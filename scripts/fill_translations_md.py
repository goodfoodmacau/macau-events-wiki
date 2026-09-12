#!/usr/bin/env python3
"""
Fill missing translations in all event .md files using OpenAI,
then write updated frontmatter back to disk.

Usage:
  python3 scripts/fill_translations_md.py [--dry-run] [--limit N]
"""
from __future__ import annotations
import argparse, asyncio, json, os, re, sys
from pathlib import Path
import aiohttp
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from translations import (
    REQUIRED_LANGUAGES, LANGUAGE_NAMES, REQUIRED_FIELDS,
    ensure_source_block, has_complete_translations,
    missing_translation_languages, practical_source_text,
    translation_block_complete,
)

OPENAI_BASE = "https://api.openai.com"
MODEL       = os.getenv("MACAU_AI_MODEL", "gpt-4o-mini")
API_KEY     = os.getenv("OPENAI_API_KEY", "")


def load_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    data = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ""
    return data, body


def dump_md(path: Path, data: dict, body: str) -> None:
    front = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    path.write_text(f"---\n{front}---{body}", encoding="utf-8")


async def translate_event(session: aiohttp.ClientSession, event: dict) -> bool:
    ensure_source_block(event)
    missing = missing_translation_languages(event)
    if not missing:
        return True

    title = str(event.get("title") or "").strip()
    description = str(event.get("description") or "").strip()
    practical = practical_source_text(event)

    if not title:
        return False

    # If no description, ask AI to generate a brief one from title+practical
    desc_instruction = (
        description if description
        else f"[No description available. Write a 1-sentence description based on the event title and practical info: title='{title}', info='{practical[:200]}']"
    )

    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": (
                "Translate Macau event information faithfully into the requested languages. "
                "Return a JSON object where each key is a language code. "
                "Preserve proper names, dates, prices, URLs. "
                "If the description instruction is in brackets, write a real 1-sentence description "
                "based on the title and practical info — do not include the brackets in the output."
            )},
            {"role": "user", "content": json.dumps({
                "source_language": event.get("source_language", "en"),
                "source": {
                    "title": title,
                    "description": desc_instruction,
                    "practical_info": practical,
                },
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
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    try:
        async with session.post(
            f"{OPENAI_BASE}/v1/chat/completions",
            json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            resp.raise_for_status()
            body_json = await resp.json()
            result = json.loads(body_json["choices"][0]["message"]["content"])
    except Exception as exc:
        print(f"    API ERROR: {exc}")
        return False

    translations = event.get("translations") or {}
    for lang in missing:
        block = result.get(lang)
        if not isinstance(block, dict):
            continue
        normalized = {
            "language_name": LANGUAGE_NAMES.get(lang, lang),
            "title":          str(block.get("title") or "").strip(),
            "description":    str(block.get("description") or "").strip(),
            "practical_info": str(block.get("practical_info") or "").strip(),
            "translation_status": "machine",
        }
        if translation_block_complete(normalized):
            translations[lang] = normalized
        else:
            print(f"    incomplete block for {lang}: {normalized}")
    event["translations"] = translations
    return has_complete_translations(event)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: OPENAI_API_KEY not set"); return 1

    wiki_root = Path(__file__).parent.parent
    md_files = sorted((wiki_root / "events").rglob("*.md"))
    md_files = [f for f in md_files if f.name != "index.md"]
    print(f"Found {len(md_files)} event files")

    need_translation = []
    for path in md_files:
        data, body = load_md(path)
        if not has_complete_translations(data):
            need_translation.append((path, data, body))

    print(f"Need translation: {len(need_translation)}")
    if args.limit:
        need_translation = need_translation[:args.limit]
        print(f"Processing first {args.limit}")

    if args.dry_run:
        print("DRY RUN")
        for path, data, _ in need_translation[:5]:
            print(f"  {path.name}: missing {missing_translation_languages(data)}")
        return 0

    done = errors = 0
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i, (path, data, body) in enumerate(need_translation, 1):
            missing = missing_translation_languages(data)
            print(f"[{i}/{len(need_translation)}] {path.name[:60]} — filling {missing}...", flush=True)
            ok = await translate_event(session, data)
            if ok:
                dump_md(path, data, body)
                done += 1
                print(f"    ✓")
            else:
                errors += 1
                print(f"    ✗ incomplete")
            await asyncio.sleep(0.1)

    print(f"\nDone: {done} translated, {errors} failed")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
