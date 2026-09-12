#!/usr/bin/env python3
"""Backfill missing translations for all published events using local Ollama."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from translations import ensure_event_translations, has_complete_translations, missing_translation_languages


async def main() -> int:
    base = Path(os.getenv("MACAU_EVENTS_WIKI_ROOT", "/Users/besa/macau-events-wiki")).resolve()
    published_path = base / "published" / "events.json"
    events = json.loads(published_path.read_text(encoding="utf-8"))

    total = len(events)
    complete_before = sum(1 for e in events if has_complete_translations(e))
    print(f"Total published: {total}")
    print(f"Complete 12-language before: {complete_before}")

    import aiohttp
    async with aiohttp.ClientSession() as session:
        for i, event in enumerate(events, 1):
            missing = missing_translation_languages(event)
            if not missing:
                print(f"[{i}/{total}] {event.get('title','')[:60]} — already complete")
                continue
            print(f"[{i}/{total}] {event.get('title','')[:60]} — filling {len(missing)} languages...")
            try:
                await ensure_event_translations(event, session)
            except Exception as e:
                print(f"  ERROR: {e}")

    complete_after = sum(1 for e in events if has_complete_translations(e))
    print(f"\nComplete 12-language after: {complete_after}/{total}")

    # Write back the enriched events
    published_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated published/events.json")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))