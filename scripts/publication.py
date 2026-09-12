#!/usr/bin/env python3
"""Credibility and publication policy for the local event feed.

This module deliberately reads archive Markdown without modifying it.  The
published feed is a derived, disposable view of the archive.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import Any
import json
import re
import yaml
from translations import has_complete_translations, missing_translation_languages

TRUST_LEVELS = {"official": 3, "institutional": 2, "commercial": 1, "unknown": 0}
OFFICIAL_DOMAINS = {
    "macaotourism.gov.mo", "icm.gov.mo", "mam.gov.mo", "library.gov.mo",
    "macaucci.gov.mo", "gov.mo",
}
COMMERCIAL_DOMAINS = {
    "galaxymacau.com", "mgm.mo", "grandlisboahotels.com",
    "sandsresortsmacao.com", "wynnresortsmacau.com", "wynnmacau.com", "wynnpalace.com",
    "cityofdreamsmacau.com", "studiocitymacau.com", "studiocity-macau.com", "venetianmacao.com",
    "parisianmacao.com", "broadwaymacau.com", "sjmholdings.com", "sjmresorts.com",
    "grandlisboa.com", "grandlisboapalace.com", "grandlisboahotels.com",
    "fishermanswharf.com.mo",
    "lisboetamacau.com", "londonermacao.com",
}
INSTITUTIONAL_DOMAINS = {
    "macaudailytimes.com.mo", "tdm.com.mo", "macaunews.mo", "icm.gov.mo",
    "insideasianliving.com", "timeout.com", "macaulifestyle.com",
}
DATE_FIELDS = ("start_date", "end_date", "last_crawled")


def normalize_date(value: Any) -> str | None:
    """Return an ISO date/datetime string, including for PyYAML date objects."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    # Keep valid ISO values stable; don't silently reinterpret malformed dates.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ].*)?", text):
        return text
    return text


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def classify_source(event: dict[str, Any]) -> tuple[str, str]:
    source = str(event.get("source") or "").lower().strip()
    url = str(event.get("source_url") or "")
    parsed_host = urlparse(url).hostname
    host = (parsed_host or "").lower().removeprefix("www.")
    candidate = host or source
    if candidate.endswith(".gov.mo") or candidate in OFFICIAL_DOMAINS:
        return "official", candidate or "unknown"
    if any(candidate == domain or candidate.endswith("." + domain) for domain in COMMERCIAL_DOMAINS):
        return "commercial", candidate or "unknown"
    if candidate in INSTITUTIONAL_DOMAINS:
        return "institutional", candidate
    # A merely reachable URL or arbitrary source label is not evidence of
    # credibility. It must be explicitly allowlisted or reviewed.
    return "unknown", candidate or "unknown"


def assess_event(event: dict[str, Any]) -> dict[str, Any]:
    """Score an event from explicit evidence, returning policy fields."""
    trust, source_label = classify_source(event)
    score = TRUST_LEVELS[trust] * 20
    reasons = [f"source trust: {trust} ({source_label})"]
    start = normalize_date(event.get("start_date"))
    end = normalize_date(event.get("end_date"))
    if start and re.match(r"^\d{4}-\d{2}-\d{2}", start):
        score += 20; reasons.append("has start date")
    else:
        reasons.append("missing start date")
    if end and re.match(r"^\d{4}-\d{2}-\d{2}", end):
        score += 10; reasons.append("has end date")
    else:
        reasons.append("missing end date")
    if event.get("title"):
        score += 10; reasons.append("has title")
    if event.get("venue_name") and str(event.get("venue_name")).strip().lower() not in {"tbd", "unknown"}:
        score += 10; reasons.append("has venue")
    if event.get("organizer"):
        score += 5; reasons.append("has organizer")
    if event.get("source_url", "").startswith(("http://", "https://")):
        score += 10; reasons.append("has source URL")
    else:
        reasons.append("missing source URL")
    translations_complete = has_complete_translations(event)
    if translations_complete:
        score += 5; reasons.append("has complete 12-language event translations")
    else:
        reasons.append("missing event translations: " + ", ".join(missing_translation_languages(event)))
    score = min(100, score)
    # A trusted source is not sufficient by itself: public records must also
    # be actionable for a visitor. Missing practical fields go to review.
    missing_actionable = [
        label for label, present in (
            ("end date", bool(end)),
            ("venue", bool(event.get("venue_name"))),
            ("address", bool(event.get("address"))),
            ("organizer", bool(event.get("organizer"))),
        ) if not present
    ]
    if not start or not event.get("title") or trust == "unknown":
        band, status = "low", "rejected"
    elif missing_actionable and score >= 50:
        band, status = "medium", "review"
        reasons.append("needs review: missing " + ", ".join(missing_actionable))
    elif score >= 75:
        band, status = "high", "published"
    elif score >= 50:
        band, status = "medium", "review"
    else:
        band, status = "low", "rejected"
    return {"credibility_score": score, "credibility_band": band,
            "credibility_reasons": reasons, "publication_status": status,
            "source_trust_level": trust}


def load_events(events_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    events, errors = [], []
    for path in sorted(events_dir.rglob("*.md")):
        if path.name == "index.md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                errors.append({"path": str(path), "error": "missing frontmatter"}); continue
            parts = content.split("---", 2)
            event = yaml.safe_load(parts[1]) or {}
            if not isinstance(event, dict):
                raise ValueError("frontmatter is not a mapping")
            event = json_safe(event)
            # Preserve the stable website route key from the archive filename.
            # The public feed must not require the website to reconstruct it.
            event["slug"] = path.stem
            event["_path"] = str(path.relative_to(events_dir.parent))
            event.update(assess_event(event))
            events.append(event)
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    return events, errors


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace"), encoding="utf-8")
