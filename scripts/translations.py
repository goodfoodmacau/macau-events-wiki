#!/usr/bin/env python3
"""Wiki-level multilingual enrichment for Macau event records.

Translations belong to each event's YAML frontmatter. The website is a reader:
it selects one stored language block and never generates event translations.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_LANGUAGES = (
    "en", "zh-hant-yue", "zh-cn", "pt",
)
REQUIRED_FIELDS = ("title", "description", "practical_info", "translation_status")
ALLOWED_TRANSLATION_STATUSES = {"source", "machine", "human-reviewed"}
LANGUAGE_NAMES = {
    "en": "English",
    "zh-hant-yue": "Traditional Chinese (Cantonese)",
    "zh-cn": "Simplified Chinese (Mandarin)",
    "pt": "Portuguese",
    "ko": "Korean",
    "th": "Thai",
    "de": "German",
    "it": "Italian",
    "es": "Spanish",
    "sq": "Albanian",
    "vi": "Vietnamese",
    "id": "Indonesian",
}


def _get(event: Any, key: str, default: Any = "") -> Any:
    return event.get(key, default) if isinstance(event, dict) else getattr(event, key, default)


def _set(event: Any, key: str, value: Any) -> None:
    if isinstance(event, dict):
        event[key] = value
    else:
        setattr(event, key, value)


def practical_source_text(event: Any) -> str:
    facts: list[str] = []
    start = str(_get(event, "start_date") or "").strip()
    end = str(_get(event, "end_date") or "").strip()
    if start:
        facts.append(f"Scheduled for {start}" + (f" to {end}" if end and end != start else ""))
    start_time = str(_get(event, "start_time") or "").strip()
    end_time = str(_get(event, "end_time") or "").strip()
    if start_time:
        facts.append(f"Time: {start_time}" + (f"–{end_time}" if end_time else ""))
    venue = str(_get(event, "venue_name") or "").strip()
    address = str(_get(event, "address") or "").strip()
    if venue:
        facts.append(f"Venue: {venue}" + (f", {address}" if address else ""))
    if _get(event, "ticket_info"):
        facts.append(str(_get(event, "ticket_info")).strip())
    if _get(event, "ticket_url"):
        facts.append(f"Official ticket information: {_get(event, 'ticket_url')}")
    if _get(event, "accessibility"):
        facts.append(str(_get(event, "accessibility")).strip())
    if _get(event, "transport"):
        facts.append(str(_get(event, "transport")).strip())
    if _get(event, "parking"):
        facts.append(str(_get(event, "parking")).strip())
    return ". ".join(dict.fromkeys(filter(None, facts)))


def translation_block_complete(block: Any) -> bool:
    return (
        isinstance(block, dict)
        and all(str(block.get(field) or "").strip() for field in REQUIRED_FIELDS)
        and block.get("translation_status") in ALLOWED_TRANSLATION_STATUSES
    )


def missing_translation_languages(event: Any) -> list[str]:
    translations = _get(event, "translations", {}) or {}
    return [lang for lang in REQUIRED_LANGUAGES if not translation_block_complete(translations.get(lang))]


def has_complete_translations(event: Any) -> bool:
    return not missing_translation_languages(event)


def ensure_source_block(event: Any) -> dict[str, dict[str, str]]:
    translations = dict(_get(event, "translations", {}) or {})
    source_language = str(_get(event, "source_language", "en") or "en").lower()
    aliases = {"zh-hant": "zh-hant-yue", "zh-hk": "zh-hant-yue", "zh-cn": "zh-cn", "zh": "zh-cn"}
    source_language = aliases.get(source_language, source_language)
    if source_language not in REQUIRED_LANGUAGES:
        _set(event, "translations", translations)
        return translations
    current = dict(translations.get(source_language) or {})
    source_values = {
        "language_name": LANGUAGE_NAMES[source_language],
        "title": str(_get(event, "title") or "").strip(),
        "description": str(_get(event, "description") or "").strip(),
        "practical_info": practical_source_text(event),
        "translation_status": "source",
    }
    for field, value in source_values.items():
        if not str(current.get(field) or "").strip() and value:
            current[field] = value
    translations[source_language] = current
    _set(event, "translations", translations)
    return translations


def _json_from_model(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("translation response is not an object")
    return value


async def ensure_event_translations(event: Any, session: Any) -> bool:
    """Fill missing wiki translation blocks through an OpenAI-compatible API.

    Configure MACAU_AI_BASE_URL, MACAU_AI_MODEL and optionally MACAU_AI_API_KEY.
    Returns False without inventing translations if the service is unavailable.
    """
    translations = ensure_source_block(event)
    missing = missing_translation_languages(event)
    if not missing:
        return True

    base_url = os.getenv("MACAU_AI_BASE_URL", "").rstrip("/")
    if not base_url:
        return False

    source = {
        "title": str(_get(event, "title") or "").strip(),
        "description": str(_get(event, "description") or "").strip(),
        "practical_info": practical_source_text(event),
    }
    payload = {
        "model": os.getenv("MACAU_AI_MODEL", "gpt-4o-mini"),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "Translate Macau event information faithfully. Return JSON only. Preserve proper names, "
                "dates, prices, URLs and factual meaning. Do not add, infer or omit facts."
            )},
            {"role": "user", "content": json.dumps({
                "source_language": _get(event, "source_language", "en"),
                "source": source,
                "target_languages": {lang: LANGUAGE_NAMES[lang] for lang in missing},
                "output_shape": {lang: {
                    "language_name": LANGUAGE_NAMES[lang],
                    "title": "translated title",
                    "description": "translated description",
                    "practical_info": "translated practical information",
                    "translation_status": "machine",
                } for lang in missing},
            }, ensure_ascii=False)},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if os.getenv("MACAU_AI_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['MACAU_AI_API_KEY']}"
    try:
        async with session.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers, timeout=120) as response:
            response.raise_for_status()
            body = await response.json()
            result = _json_from_model(body["choices"][0]["message"]["content"])
        for language in missing:
            block = result.get(language)
            if not isinstance(block, dict):
                continue
            normalized = {
                "language_name": LANGUAGE_NAMES[language],
                "title": str(block.get("title") or "").strip(),
                "description": str(block.get("description") or "").strip(),
                "practical_info": str(block.get("practical_info") or "").strip(),
                "translation_status": "machine",
            }
            if translation_block_complete(normalized):
                translations[language] = normalized
        _set(event, "translations", translations)
        return has_complete_translations(event)
    except Exception as exc:
        logger.warning("Translation failed for %s: %s", _get(event, "id") or _get(event, "title"), exc)
        return False
