#!/usr/bin/env python3
"""Event intelligence enrichment.

Uses an OpenAI-compatible chat endpoint when MACAU_AI_BASE_URL is configured.
The local fallback is deliberately conservative: it summarizes only fields
already extracted from the source and never invents dates, prices or claims.

Anti-hallucination layer
------------------------
When the AI returns factual fields (performers, price, organizer, etc.) it must
also return a matching *_source field containing the exact source text span that
supports the claim.  Before the field is accepted into the event, we verify that
the quoted span appears verbatim in the raw HTML text.  Fields whose source quote
is missing or cannot be found in the page text are dropped (set to null) so that
the crawler never publishes invented facts.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Fields that require a source quote when returned by the AI.
# If the AI returns "performers": ["X"] it must also return
# "performers_source": "exact text from the page that names X".
# ---------------------------------------------------------------------------
CITATION_REQUIRED_FIELDS = [
    "performers",
    "ticket_price",
    "organizer",
    "sponsor",
    "dress_code",
    "age_restriction",
    "capacity",
    "lineup",
]

# Generic default values the AI invents without real source support.
# Rejected even if the AI fabricates a citation for them.
GENERIC_DEFAULT_BLOCKLIST = {
    'dress_code':      {'casual', 'smart casual', 'no dress code', 'not stated', 'n/a', 'none'},
    'age_restriction': {'all-ages', 'all ages', 'none', 'n/a', 'not stated', 'open to all'},
}



def _text(value: Any) -> str:
    return str(value or "").strip()


def _source_text(html: str, event: Any) -> str:
    if html:
        soup = BeautifulSoup(html, "lxml")
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        text = " ".join(soup.get_text(" ").split())
        if text:
            return text[:12000]
    return " ".join(filter(None, [
        _text(getattr(event, "title", "")),
        _text(getattr(event, "description", "")),
        _text(getattr(event, "venue_name", "")),
        _text(getattr(event, "ticket_info", "")),
    ]))[:12000]


def _verify_citations(result: dict, page_text: str) -> tuple[dict, list[str]]:
    """
    For every field in CITATION_REQUIRED_FIELDS, check that:
      1. A matching *_source key exists in result.
      2. The quoted text appears verbatim (case-insensitive) in page_text.

    Fields that fail verification are set to None and flagged.
    Returns (cleaned_result, list_of_dropped_fields).
    """
    dropped: list[str] = []
    page_lower = page_text.lower()

    for field in CITATION_REQUIRED_FIELDS:
        value = result.get(field)
        if value is None:
            continue  # field not present — nothing to verify
        source_key = f"{field}_source"
        quote: str = str(result.get(source_key) or "").strip()

        if not quote:
            # AI returned the field but no source quote
            result[field] = None
            result[source_key] = None
            dropped.append(f"{field}:missing_source_quote")
            continue

        # The quote must appear somewhere in the page text
        if quote.lower() not in page_lower:
            result[field] = None
            result[source_key] = f"UNVERIFIED:{quote[:120]}"
            dropped.append(f"{field}:quote_not_found_in_page")
            continue

        # Block generic default values even when a citation exists —
        # the AI fabricates citations for these boilerplate phrases.
        if field in GENERIC_DEFAULT_BLOCKLIST:
            val_str = str(value).strip().lower()
            if val_str in GENERIC_DEFAULT_BLOCKLIST[field]:
                result[field] = None
                result[source_key] = None
                dropped.append(f"{field}:generic_default_blocked:{val_str}")

    return result, dropped


def _fallback(event: Any) -> dict[str, Any]:
    title = _text(getattr(event, "title", ""))
    description = _text(getattr(event, "description", ""))
    category = _text(getattr(event, "category", "")) or "event"
    article = "an" if category[:1].lower() in "aeiou" else "a"
    venue = _text(getattr(event, "venue_name", "")) or "venue to be confirmed"
    date = _text(getattr(event, "start_date", ""))
    end = _text(getattr(event, "end_date", ""))
    summary = description[:500] if description else f"{article.title()} {category} event at {venue}."
    best_for = []
    lower = f"{title} {description} {category}".lower()
    if any(x in lower for x in ["family", "children", "kids"]): best_for.append("families")
    if any(x in lower for x in ["concert", "music", "dj", "nightlife", "party"]): best_for.append("music and nightlife audiences")
    if any(x in lower for x in ["exhibition", "museum", "gallery", "art"]): best_for.append("art and culture visitors")
    if not best_for: best_for.append("visitors interested in this type of event")
    practical = []
    if date: practical.append(f"Scheduled from {date}" + (f" to {end}" if end and end != date else ""))
    if getattr(event, "start_time", None): practical.append(f"Starts at {event.start_time} local time")
    if getattr(event, "ticket_info", None): practical.append(_text(event.ticket_info))
    elif getattr(event, "ticket_url", None): practical.append("Ticketing information is available from the official source")
    return {
        "intel_summary": summary,
        "event_type_explained": f"This is {article} {category} event presented at {venue}.",
        "best_for": best_for,
        "experience_level": "general audience",
        "intel_highlights": [summary[:180]],
        "practical_intelligence": practical,
        "considerations": ["Check the official source for final schedule, availability and access requirements."],
        "ai_confidence": "low",
        "ai_enrichment_status": "fallback",
        "ai_enrichment_model": "local-conservative-fallback",
        "hallucination_check": "skipped:fallback_mode",
    }


def _valid(result: Any) -> bool:
    if not isinstance(result, dict): return False
    required = ["intel_summary", "event_type_explained", "best_for", "intel_highlights", "practical_intelligence", "considerations"]
    return all(isinstance(result.get(k), (str, list)) and result.get(k) for k in required)


async def enrich_event(event: Any, html: str, session: Any) -> Any:
    fallback = _fallback(event)
    base_url = os.getenv("MACAU_AI_BASE_URL", "").rstrip("/")
    if not base_url:
        for key, value in fallback.items(): setattr(event, key, value)
        event.ai_enriched_at = datetime.now(timezone.utc).isoformat()
        return event

    # Build the page text now so we can cross-check AI claims against it
    page_text = _source_text(html, event)

    payload = {
        "model": os.getenv("MACAU_AI_MODEL", "gpt-4o-mini"),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Macau event intelligence editor. Read the supplied source text. "
                    "Return valid JSON only. Never invent facts; use empty arrays or "
                    "'not stated in source' when unknown.\n\n"
                    "ANTI-HALLUCINATION RULES:\n"
                    "1. Never set dress_code to 'casual' or 'smart casual' unless those exact words appear in the source.\n"
                    "2. Never set age_restriction to 'all-ages' or 'all ages' unless explicitly stated in the source.\n"
                    "3. Never set considerations to generic advice like 'Check the official source' — only state specific verifiable uncertainties from the page.\n"
                    "4. If a field is not explicitly stated in the source, set it to null — do not guess or use generic defaults.\n\n"
                    "CITATION REQUIREMENT: For every factual field you fill in "
                    "(performers, ticket_price, organizer, sponsor, dress_code, age_restriction, "
                    "capacity, lineup), you MUST also include a matching *_source field containing "
                    "the EXACT verbatim text span from the source that supports the claim. "
                    "If you cannot find an exact supporting quote in the source text, set the "
                    "field to null and omit the *_source field entirely. "
                    "Fields without a verifiable source quote will be discarded by the pipeline."
                )
            },
            {
                "role": "user",
                "content": json.dumps({
                    "task": "Explain what this event is and produce useful visitor intelligence.",
                    "required_fields": {
                        "intel_summary": "2-4 factual sentences",
                        "event_type_explained": "plain-language explanation",
                        "best_for": "array of audience descriptions",
                        "experience_level": "casual, enthusiast, specialist, or general audience",
                        "intel_highlights": "array of 2-6 factual highlights",
                        "practical_intelligence": "array covering time, venue, tickets, access and logistics only when stated",
                        "considerations": "array of uncertainties or things to verify",
                        "ai_confidence": "high, medium or low",
                        "performers": "array of performer names IF stated in source (+ performers_source)",
                        "ticket_price": "price string IF stated in source (+ ticket_price_source)",
                        "organizer": "organizer name IF stated in source (+ organizer_source)",
                    },
                    "citation_instruction": (
                        "For performers, ticket_price, organizer, sponsor, dress_code, "
                        "age_restriction, capacity, lineup — add a *_source field with the "
                        "exact verbatim quote from the source text. Example: "
                        "\"performers\": [\"Sarah Brightman\"], "
                        "\"performers_source\": \"International soprano Sarah Brightman will headline\""
                    ),
                    "structured_event": {k: getattr(event, k, None) for k in [
                        "title", "description", "category", "start_date", "end_date",
                        "start_time", "venue_name", "address", "organizer",
                        "ticket_info", "ticket_url", "source_url"
                    ]},
                    "source_text": page_text,
                }, ensure_ascii=False)
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    if os.getenv("MACAU_AI_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['MACAU_AI_API_KEY']}"
    try:
        async with session.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers, timeout=90) as response:
            response.raise_for_status()
            body = await response.json()
            content = body["choices"][0]["message"]["content"]
            result = json.loads(content)
            if not _valid(result):
                raise ValueError("AI response missing required intelligence fields")

            # ---------------------------------------------------------------
            # Anti-hallucination: verify citations before accepting factual fields
            # ---------------------------------------------------------------
            result, dropped_fields = _verify_citations(result, page_text)
            if dropped_fields:
                result["hallucination_check"] = f"dropped:{','.join(dropped_fields)}"
            else:
                result["hallucination_check"] = "passed"

            result["ai_enrichment_status"] = "ai"
            result["ai_enrichment_model"] = payload["model"]
            result["ai_enriched_at"] = datetime.now(timezone.utc).isoformat()
            for key, value in result.items():
                setattr(event, key, value)
            return event
    except Exception:
        for key, value in fallback.items():
            setattr(event, key, value)
        event.ai_enrichment_status = "fallback_after_error"
        event.ai_enriched_at = datetime.now(timezone.utc).isoformat()
        return event
