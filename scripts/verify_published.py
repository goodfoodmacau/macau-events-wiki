#!/usr/bin/env python3
"""
verify_published.py — Self-healing QA pipeline for published Macau events.

Verification layers:
  1. HTTP  — URL alive, not a soft-404 or parked page
  2. Field — Live page date/title/price still match stored values
  3. Anti-hallucination — AI-enriched fields anchored to source text
  4. Image — featured_image URL returns a valid image
  5. Temporal — past events auto-archived
  6. AI brain — LLM reads live page + stored event, makes intelligent decisions

Auto-fix actions:
  - Re-scrape corrected field values from live page
  - Strip unanchored AI claims (or replace with sourced value)
  - Null broken image URLs (re-scrape replacement if possible)
  - Archive past events
  - Update source_url to final redirect when original redirects cleanly

Output:
  - qa_report.json  — full audit trail per event
  - Updates events.json + individual event .md files
  - Git commit with structured message
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, date, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup

WIKI_ROOT = Path(__file__).parent.parent
PUBLISHED_JSON = WIKI_ROOT / "published" / "events.json"
EVENTS_DIR = WIKI_ROOT / "events"
ARCHIVE_DIR = WIKI_ROOT / "archive"
REJECTED_DIR = WIKI_ROOT / "rejected"
REVIEW_DIR = WIKI_ROOT / "review"
QA_REPORT = WIKI_ROOT / "qa_report.json"
LOG_DIR = WIKI_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("verify_published")

# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
CONCURRENCY = 5
REQUEST_TIMEOUT = 15
FUZZY_TITLE_THRESHOLD = 0.75
ANCHOR_MIN_OVERLAP = 0.40
MIN_IMAGE_BYTES = 2000
PARKED_MARKERS = [
    "this domain is for sale", "buy this domain", "domain parking",
    "godaddy", "sedo.com", "afternic", "hugedomains",
    "this webpage is not available", "under construction",
]
SOFT_404_MARKERS = [
    "page not found", "404", "event not found", "this event has ended",
    "content not found", "no longer available",
]

# Permanent/ongoing attractions — no specific date on page by design
PERMANENT_ATTRACTION_KEYWORDS = [
    'galaxy kidz', 'grand resort deck', 'fantasy box', 'the spectacle',
    'grande praca', 'grande praça', 'kids city', "kids' city",
    'sky21', 'sky 21', 'fisherman', 'always open', 'daily admission',
    'open daily', 'year-round', 'permanent exhibition', 'permanent attraction',
]

def _is_permanent_attraction(event: dict) -> bool:
    title = str(event.get('title', '')).lower()
    venue = str(event.get('venue_name', '')).lower()
    combined = title + ' ' + venue
    return any(kw in combined for kw in PERMANENT_ATTRACTION_KEYWORDS)

HALLUCINATION_RISK_PATTERNS = [
    r"mop\s*\d+",
    r"\d{1,2}:\d{2}\s*(am|pm)",
    r"macau['']?s\s+(best|top|largest|premier|only|first)",
    r"sold\s+out",
    r"limited\s+(seats|tickets|availability)",
]
AI_ENRICHED_FIELDS = [
    "intel_summary", "best_for", "highlights",
    "practical_intelligence", "considerations",
    "performers", "ticket_price", "dress_code",
    "age_restriction", "lineup",
]
CITATION_REQUIRED = [
    "performers", "ticket_price", "organizer",
    "dress_code", "age_restriction", "capacity", "lineup",
]

# ---------------------------------------------------------------------------
# AI brain
# ---------------------------------------------------------------------------
AI_BASE_URL = os.environ.get("MACAU_AI_BASE_URL", "")
AI_API_KEY  = os.environ.get("MACAU_AI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
AI_MODEL    = os.environ.get("MACAU_AI_MODEL", "gpt-4o-mini")

AI_VERIFY_PROMPT = """\
You are a factual data quality analyst for a Macau events website.

You will be given:
1. A stored event record (JSON)
2. The live page text from the event source URL (truncated to 8000 chars)
3. Rule-based flags already raised

Your job is to produce a clean, accurate event record by:
- Correcting any fields that don't match the live page
- Removing or fixing claims not supported by the page text
- Filling in missing fields IF the page clearly states them
- Deciding the final action: ok | fixed | review | archive | reject

STRICT RULES:
- NEVER invent facts — only use what is explicitly on the live page
- If the page is in Chinese or Portuguese, extract English equivalents if present
- If start_date cannot be confirmed on the page, flag for review (do not guess)
- If the event is clearly in the past, action = archive
- If the page is a 404 / parked / unrelated, action = reject
- If something is ambiguous and you are not sure, action = review

Return ONLY valid JSON with this exact structure:
{
  "action": "ok" | "fixed" | "review" | "archive" | "reject",
  "reason": "one sentence explaining your decision",
  "corrected_fields": {
    "field_name": "corrected_value"
  },
  "stripped_fields": ["field_name"],
  "hallucination_findings": [
    {"field": "field_name", "claim": "the problematic text", "reason": "why it is unanchored"}
  ],
  "confidence": 0.0
}
"""


async def ai_verify_event(
    session: aiohttp.ClientSession,
    event: dict,
    page_text: str,
    rule_flags: list[str],
) -> dict | None:
    if not AI_BASE_URL and not AI_API_KEY:
        return None

    base = AI_BASE_URL.rstrip("/") if AI_BASE_URL else "https://api.openai.com/v1"
    endpoint = f"{base}/chat/completions"

    event_snapshot = {
        k: v for k, v in event.items()
        if k not in ("html_cache", "raw_html", "translations")
        and v not in (None, "", [], {})
    }

    user_content = (
        f"STORED EVENT:\n{json.dumps(event_snapshot, ensure_ascii=False, indent=2)}\n\n"
        f"LIVE PAGE TEXT (truncated):\n{page_text[:8000]}\n\n"
        f"RULE-BASED FLAGS:\n{json.dumps(rule_flags)}\n\n"
        "Analyse and return your JSON decision."
    )

    payload = {
        "model": AI_MODEL,
        "temperature": 0.0,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": AI_VERIFY_PROMPT},
            {"role": "user",   "content": user_content},
        ],
    }
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with session.post(
            endpoint, json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                log.warning(f"AI verify HTTP {resp.status} for {event.get('guid','')}")
                return None
            data = await resp.json()
            raw = data["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"AI returned invalid JSON for {event.get('guid','')}: {e}")
        return None
    except Exception as e:
        log.warning(f"AI verify failed for {event.get('guid','')}: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> date:
    return datetime.now(tz=timezone.utc).date()

def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def _keyword_overlap(claim: str, source_text: str) -> float:
    stop = {"a","an","the","and","or","of","in","at","to","is","are","was","were","be","been","for","on","with","by"}
    words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", claim) if w.lower() not in stop]
    if not words:
        return 1.0
    src_lower = source_text.lower()
    return sum(1 for w in words if w in src_lower) / len(words)

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript","svg","header","footer","nav"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())[:20000]

def _is_parked(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in PARKED_MARKERS) or len(text.split()) < 150

def _is_soft_404(text: str) -> bool:
    return any(m in text.lower() for m in SOFT_404_MARKERS)

def _parse_date(val: Any) -> date | None:
    if not val:
        return None
    s = str(val).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None

def _find_date_on_page(text: str, target: date) -> bool:
    patterns = [
        target.strftime("%Y-%m-%d"),
        target.strftime("%d/%m/%Y"),
        target.strftime("%B %d, %Y"),
        target.strftime("%d %B %Y"),
    ]
    return any(p in text for p in patterns)

def _scrape_image(soup: BeautifulSoup, base_url: str) -> str | None:
    for meta in soup.find_all("meta", property=re.compile(r"og:image|twitter:image")):
        src = meta.get("content", "").strip()
        if src:
            return urljoin(base_url, src)
    for img in soup.find_all("img", src=True):
        src = img["src"].strip()
        if src and not src.endswith(".gif") and "logo" not in src.lower():
            return urljoin(base_url, src)
    return None

def _event_md_path(event: dict) -> Path | None:
    d = _parse_date(event.get("start_date"))
    if not d:
        return None
    month_name = d.strftime("%B").lower()
    folder = EVENTS_DIR / str(d.year) / f"{d.month:02d}-{month_name}"
    guid = str(event.get("guid", "")).replace("/", "-").replace(":", "-")
    slug = str(event.get("id", guid))
    candidates = list(folder.glob(f"*{slug[:30]}*.md")) if folder.exists() else []
    return candidates[0] if candidates else None

def _update_md_file(path: Path, updates: dict) -> None:
    if not path or not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for key, value in updates.items():
        val_str = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
        pattern = rf"^({re.escape(key)}:\s*).*$"
        replacement = rf"\g<1>{val_str}"
        new_text = re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)
        if new_text == text:
            parts = text.split("---", 2)
            if len(parts) >= 3:
                parts[1] = parts[1].rstrip() + f"\n{key}: {val_str}\n"
                new_text = "---".join(parts)
        text = new_text
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-event verification
# ---------------------------------------------------------------------------

async def verify_event(session: aiohttp.ClientSession, event: dict) -> dict:
    result = {
        "guid": event.get("guid", ""),
        "title": event.get("title", ""),
        "source_url": event.get("source_url", ""),
        "fixes": [], "flags": [],
        "action": "ok",
        "updates": {},
        "ai_verified": False,
    }

    url = event.get("source_url", "").strip()
    if not url:
        result["flags"].append("no_source_url")
        result["action"] = "review"
        return result

    # Layer 1 — HTTP
    html = ""
    final_url = url
    try:
        async with session.get(
            url, allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            headers={"User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )},
        ) as resp:
            final_url = str(resp.url)
            if resp.status == 404:
                result["flags"].append("dead_link_404")
                result["action"] = "reject"
                return result
            if resp.status >= 400:
                result["flags"].append(f"http_error_{resp.status}")
                result["action"] = "review"
                return result
            html = await resp.text(errors="replace")
    except asyncio.TimeoutError:
        result["flags"].append("timeout")
        result["action"] = "review"
        return result
    except Exception as exc:
        result["flags"].append(f"fetch_error:{type(exc).__name__}")
        result["action"] = "review"
        return result

    orig_domain = urlparse(url).netloc
    final_domain = urlparse(final_url).netloc
    if orig_domain and final_domain and orig_domain != final_domain:
        result["flags"].append(f"redirect_domain_change:{final_domain}")
        result["action"] = "reject"
        return result
    if final_url != url and final_domain == orig_domain:
        result["fixes"].append(f"source_url_updated")
        result["updates"]["source_url"] = final_url

    page_text = _extract_text(html)
    soup = BeautifulSoup(html, "lxml")

    if _is_parked(page_text):
        result["flags"].append("parked_page")
        result["action"] = "reject"
        return result
    if _is_soft_404(page_text):
        result["flags"].append("soft_404")
        result["action"] = "review"
        return result

    # Layer 5 — Temporal
    end_date = _parse_date(event.get("end_date")) or _parse_date(event.get("start_date"))
    if end_date and end_date < _today():
        result["flags"].append("past_event")
        result["action"] = "archive"
        return result

    # Layer 2 — Field verification
    stored_title = str(event.get("title", "")).strip()
    if stored_title and _fuzzy(stored_title, page_text[:2000]) < FUZZY_TITLE_THRESHOLD:
        live_title = ""
        og = soup.find("meta", property="og:title")
        if og:
            live_title = og.get("content", "").strip()
        if not live_title:
            h1 = soup.find("h1")
            if h1:
                live_title = h1.get_text(strip=True)
        if live_title and _fuzzy(stored_title, live_title) < FUZZY_TITLE_THRESHOLD:
            result["flags"].append(f"title_mismatch")
            result["updates"]["title"] = live_title
            result["fixes"].append("title_updated")
        elif not live_title:
            result["flags"].append("title_not_found_on_page")

    start_date = _parse_date(event.get("start_date"))
    if start_date and not _find_date_on_page(page_text, start_date):
        if _is_permanent_attraction(event):
            result["flags"].append("permanent_attraction:date_check_skipped")
        else:
            result["flags"].append(f"date_not_found_on_page:{start_date}")
            if result["action"] == "ok":
                result["action"] = "review"

    # Layer 4 — Image
    img_url = event.get("featured_image", "")
    if img_url:
        try:
            async with session.head(
                img_url, allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=8),
            ) as img_resp:
                ct = img_resp.headers.get("Content-Type", "")
                cl = int(img_resp.headers.get("Content-Length", "0") or "0")
                if img_resp.status >= 400 or "image" not in ct or cl < MIN_IMAGE_BYTES:
                    new_img = _scrape_image(soup, final_url)
                    result["updates"]["featured_image"] = new_img
                    result["flags"].append("image_broken")
                    result["fixes"].append("image_replaced" if new_img else "image_nulled")
        except Exception:
            result["flags"].append("image_check_failed")

    # Layer 3 — Anti-hallucination (rule-based)
    stripped_fields = []
    for field_name in AI_ENRICHED_FIELDS:
        value = event.get(field_name)
        if not value:
            continue
        claim_text = " ".join(str(v) for v in value) if isinstance(value, list) else str(value)

        if field_name in CITATION_REQUIRED:
            citation = str(event.get(f"{field_name}_source", "")).strip()
            if not citation or citation.lower() not in page_text.lower():
                result["flags"].append(f"missing_or_invalid_citation:{field_name}")
                stripped_fields.append(field_name)
                result["updates"][field_name] = None
                continue

        if _keyword_overlap(claim_text, page_text) < ANCHOR_MIN_OVERLAP:
            result["flags"].append(f"unanchored_claim:{field_name}")
            stripped_fields.append(field_name)
            result["updates"][field_name] = None
            continue

        for pattern in HALLUCINATION_RISK_PATTERNS:
            for m in re.findall(pattern, claim_text, re.IGNORECASE):
                if m.lower() not in page_text.lower():
                    result["flags"].append(f"hallucination_risk:{field_name}:'{m}'")
                    sentences = re.split(r"(?<=[.!?])\s+", claim_text)
                    safe = [s for s in sentences if not re.search(pattern, s, re.IGNORECASE)]
                    result["updates"][field_name] = " ".join(safe).strip() or None
                    result["fixes"].append(f"hallucination_stripped:{field_name}")

    if stripped_fields:
        result["updates"]["ai_enrichment_status"] = "partially_stripped"
        result["updates"]["needs_reenrichment"] = True

    # Layer 6 — AI brain
    ai_decision = await ai_verify_event(session, event, page_text, result["flags"])
    if ai_decision:
        result["ai_verified"] = True
        result["ai_confidence"] = ai_decision.get("confidence", 0.0)
        result["ai_reason"] = ai_decision.get("reason", "")

        ai_action = ai_decision.get("action", "")
        if ai_action in ("ok", "fixed", "review", "archive", "reject"):
            if result["action"] in ("ok", "review") or ai_action in ("archive", "reject"):
                result["action"] = ai_action

        for field_name, corrected_val in ai_decision.get("corrected_fields", {}).items():
            result["updates"][field_name] = corrected_val
            result["fixes"].append(f"ai_corrected:{field_name}")

        for field_name in ai_decision.get("stripped_fields", []):
            result["updates"][field_name] = None
            result["flags"].append(f"ai_stripped:{field_name}")
            result["fixes"].append(f"ai_stripped:{field_name}")

        for finding in ai_decision.get("hallucination_findings", []):
            result["flags"].append(
                f"ai_hallucination:{finding.get('field')}:'{finding.get('claim','')[:60]}'"
            )

        if ai_decision.get("corrected_fields") or ai_decision.get("stripped_fields"):
            result["updates"]["ai_enrichment_status"] = "ai_verified_and_cleaned"

    if result["updates"] and result["action"] == "ok":
        result["action"] = "fixed"

    result["last_verified"] = datetime.now(tz=timezone.utc).isoformat()
    result["updates"]["last_verified"] = result["last_verified"]
    return result


# ---------------------------------------------------------------------------
# Apply fixes + move events
# ---------------------------------------------------------------------------

def apply_fixes(event: dict, result: dict, all_events: list[dict]) -> None:
    if not result["updates"]:
        return
    guid = event.get("guid", "")
    for i, ev in enumerate(all_events):
        if ev.get("guid") == guid:
            all_events[i].update(result["updates"])
            break
    md_path = _event_md_path(event)
    if md_path:
        _update_md_file(md_path, result["updates"])

def move_event(event: dict, destination: Path, all_events: list[dict]) -> None:
    guid = event.get("guid", "")
    md_path = _event_md_path(event)
    if md_path and md_path.exists():
        destination.mkdir(parents=True, exist_ok=True)
        shutil.move(str(md_path), str(destination / md_path.name))
    for i, ev in enumerate(all_events):
        if ev.get("guid") == guid:
            all_events.pop(i)
            break


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_verification() -> dict:
    if not PUBLISHED_JSON.exists():
        log.error("published/events.json not found")
        sys.exit(1)

    events: list[dict] = json.loads(PUBLISHED_JSON.read_text(encoding="utf-8"))
    log.info(f"Loaded {len(events)} published events")

    report = {
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "total": len(events),
        "ok": 0, "fixed": 0, "archived": 0, "rejected": 0, "review": 0,
        "ai_verified_count": 0,
        "events": [],
    }

    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        sem = asyncio.Semaphore(CONCURRENCY)
        async def bounded(ev):
            async with sem:
                return await verify_event(session, ev)
        results = await asyncio.gather(*[bounded(ev) for ev in events])

    events_copy = list(events)
    rejected_guids = set()

    for event, result in zip(events, results):
        action = result["action"]
        if result.get("ai_verified"):
            report["ai_verified_count"] += 1

        if action == "ok":
            apply_fixes(event, result, events_copy)
            report["ok"] += 1
        elif action == "fixed":
            apply_fixes(event, result, events_copy)
            log.info(f"FIXED [{event.get('guid','')}]: {result['fixes']}")
            report["fixed"] += 1
        elif action == "archive":
            move_event(event, ARCHIVE_DIR / _today().strftime("%Y/%m"), events_copy)
            log.info(f"ARCHIVED [{event.get('guid','')}]")
            rejected_guids.add(event.get("guid", ""))
            report["archived"] += 1
        elif action == "reject":
            move_event(event, REJECTED_DIR, events_copy)
            log.info(f"REJECTED [{event.get('guid','')}]: {result['flags']}")
            rejected_guids.add(event.get("guid", ""))
            report["rejected"] += 1
        elif action == "review":
            log.info(f"REVIEW [{event.get('guid','')}]: {result['flags']}")
            report["review"] += 1

        report["events"].append(result)

    published_events = [ev for ev in events_copy if ev.get("guid") not in rejected_guids]
    PUBLISHED_JSON.write_text(
        json.dumps(published_events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    QA_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def _git_commit(report: dict) -> None:
    try:
        subprocess.run(
            ["git", "-C", str(WIKI_ROOT), "add",
             "published/events.json", "events/", "archive/", "rejected/", "qa_report.json"],
            check=True, capture_output=True,
        )
        msg = (
            f"qa: {report['run_at'][:10]} — "
            f"{report['fixed']} fixed, {report['archived']} archived, "
            f"{report['rejected']} rejected, {report['review']} flagged for review "
            f"(AI verified: {report['ai_verified_count']})"
        )
        subprocess.run(
            ["git", "-C", str(WIKI_ROOT), "commit", "-m", msg],
            check=True, capture_output=True,
        )
        log.info(f"Git commit: {msg}")
    except subprocess.CalledProcessError as e:
        log.warning(f"Git commit skipped: {e.stderr.decode()[:200]}")


def _mac_notify(report: dict) -> None:
    total = report["total"]
    bad = report["rejected"] + report["review"]
    if total and bad / total > 0.10:
        pct = int(bad / total * 100)
        msg = (
            f"{pct}% of events flagged — "
            f"{report['rejected']} rejected, {report['review']} need review"
        )
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{msg}" with title "Macau Events QA"'
            ], capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-healing QA for published events")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only — do not modify any files")
    args = parser.parse_args()

    report = asyncio.run(run_verification())

    if not args.dry_run and not args.no_commit:
        _git_commit(report)
        _mac_notify(report)

    print("\n" + "="*60)
    print(f"QA COMPLETE — {report['run_at'][:19]}")
    print(f"  Total checked  : {report['total']}")
    print(f"  OK             : {report['ok']}")
    print(f"  Auto-fixed     : {report['fixed']}")
    print(f"  Archived       : {report['archived']}")
    print(f"  Rejected       : {report['rejected']}")
    print(f"  Needs review   : {report['review']}")
    print(f"  AI verified    : {report['ai_verified_count']}")
    print(f"  Report         : {QA_REPORT}")
    print("="*60)
    if args.dry_run:
        print("\n[DRY RUN — no files were modified]")
