#!/usr/bin/env python3
"""
Auto-generate searchable keywords for wiki event files.
Run: python3 scripts/add_keywords.py

Reads each event .md file, derives keywords from category, tags, title,
organizer_type, venue, and existing intel fields, then writes a `keywords:`
block to the frontmatter if one isn't already present (or is empty).
"""

import re
import sys
from pathlib import Path
import yaml

WIKI_ROOT = Path(__file__).parent.parent
EVENTS_DIR = WIKI_ROOT / "events"

# ── Keyword rules ──────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "dining":        ["food", "dining", "restaurant", "culinary", "eat", "cuisine"],
    "entertainment": ["show", "performance", "entertainment", "live"],
    "art":           ["art", "exhibition", "gallery", "visual", "museum"],
    "music":         ["music", "concert", "live music", "band", "orchestra"],
    "festival":      ["festival", "celebration", "event", "cultural"],
    "sports":        ["sport", "competition", "race", "game", "athletic"],
    "nightlife":     ["nightlife", "bar", "club", "drinks", "party"],
    "theater":       ["theater", "theatre", "play", "stage", "drama", "dance"],
    "family":        ["family", "kids", "children", "all ages"],
    "film":          ["film", "movie", "cinema", "screening"],
    "education":     ["workshop", "talk", "lecture", "seminar", "class"],
    "heritage":      ["heritage", "history", "traditional", "cultural", "historic"],
    "wellness":      ["wellness", "health", "fitness", "yoga", "meditation"],
    "shopping":      ["shopping", "market", "retail", "fair"],
    "charity":       ["charity", "fundraiser", "nonprofit", "community"],
    "expo":          ["expo", "conference", "convention", "trade show", "mice"],
}

ORGANIZER_KEYWORDS = {
    "casino":        ["casino", "integrated resort", "gaming", "hotel"],
    "government":    ["government", "official", "free entry", "public"],
    "museum":        ["museum", "gallery", "exhibition", "art"],
    "venue":         ["venue", "bar", "club", "live venue"],
    "promoter":      ["promoter", "entertainment"],
}

TITLE_PATTERNS = [
    (r'\bconcert\b',       ["concert", "live music"]),
    (r'\bexhibition\b',    ["exhibition", "art", "gallery"]),
    (r'\bfestival\b',      ["festival", "celebration"]),
    (r'\bgala\b',          ["gala", "formal", "dinner"]),
    (r'\braces?\b',        ["race", "sport", "competition"]),
    (r'\bfireworks\b',     ["fireworks", "outdoor", "celebration"]),
    (r'\bparade\b',        ["parade", "outdoor", "celebration"]),
    (r'\bworkshop\b',      ["workshop", "hands-on", "class"]),
    (r'\bbrunch\b',        ["brunch", "dining", "weekend"]),
    (r'\bbuffet\b',        ["buffet", "dining", "food"]),
    (r'\btasting\b',       ["tasting", "food", "wine", "culinary"]),
    (r'\bnight\b',         ["nightlife", "evening"]),
    (r'\bfree\b',          ["free", "free entry", "no charge"]),
    (r'\bvip\b',           ["vip", "exclusive", "premium"]),
    (r'\bmooncake\b',      ["mooncake", "mid-autumn", "chinese", "traditional"]),
    (r'\bdim sum\b',       ["dim sum", "cantonese", "dining"]),
    (r'\bcrab\b',          ["seafood", "dining", "seasonal"]),
    (r'\bkaiser?\b',       ["japanese", "kaiseki", "fine dining"]),
    (r'\btempur[ae]\b',    ["japanese", "dining", "omakase"]),
    (r'\bsymphony\b',      ["classical music", "concert", "orchestra"]),
    (r'\bopera\b',         ["opera", "classical music", "performance"]),
    (r'\bdance\b',         ["dance", "performance", "show"]),
    (r'\bfilm\b',          ["film", "cinema", "screening"]),
    (r'\bmarathon\b',      ["marathon", "running", "sport", "outdoor"]),
    (r'\bgrand prix\b',    ["grand prix", "motor racing", "sport"]),
    (r'\bdragon boat\b',   ["dragon boat", "sport", "traditional", "water"]),
    (r'\bhaunted\b',       ["halloween", "seasonal", "family"]),
    (r'\bchristmas\b',     ["christmas", "seasonal", "holiday"]),
    (r'\bluna[r ]?\bnew year\b', ["chinese new year", "lunar new year", "traditional"]),
]

def derive_keywords(data: dict, title: str) -> list[str]:
    kws = set()

    # From category
    cat = (data.get("category") or "").lower()
    for c, words in CATEGORY_KEYWORDS.items():
        if c in cat:
            kws.update(words)

    # From organizer_type
    ot = (data.get("organizer_type") or "").lower()
    for o, words in ORGANIZER_KEYWORDS.items():
        if o in ot:
            kws.update(words)

    # From existing tags (cleaned up)
    for tag in (data.get("tags") or []):
        clean = tag.replace("-", " ").replace("_", " ")
        kws.add(clean)

    # From title patterns
    tl = title.lower()
    for pattern, words in TITLE_PATTERNS:
        if re.search(pattern, tl):
            kws.update(words)

    # Price signal
    price = str(data.get("price") or data.get("ticket_price") or "").lower()
    ticket_required = data.get("ticket_required")
    if "free" in price or ticket_required is False:
        kws.add("free")
        kws.add("free entry")
    elif price and price != "null":
        kws.add("ticketed")
        kws.add("paid entry")

    # Age / dress signals
    age = str(data.get("age_restriction") or "").lower()
    if "all" in age or age == "":
        kws.add("all ages")
    elif "18" in age or "adult" in age:
        kws.add("adults only")

    # Family-friendly from existing tags
    if any("family" in t for t in (data.get("tags") or [])):
        kws.update(["family", "kids", "children"])

    # Outdoor / indoor from tags
    if any("outdoor" in t for t in (data.get("tags") or [])):
        kws.add("outdoor")
    if any("indoor" in t for t in (data.get("tags") or [])):
        kws.add("indoor")

    # Remove very generic ones if list is large enough
    result = sorted(kws)
    return result


def process_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return False

    # Split frontmatter
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return False
    fm_raw, body = parts[1], parts[2]

    data = yaml.safe_load(fm_raw) or {}

    # Skip if already has non-empty keywords
    existing = data.get("keywords") or []
    if existing:
        return False

    title = data.get("title") or path.stem
    keywords = derive_keywords(data, title)
    if not keywords:
        return False

    # Insert keywords after tags line, or before last field
    fm_lines = fm_raw.splitlines()
    kw_yaml = "keywords:\n" + "\n".join(f'  - "{k}"' for k in keywords)

    # Find insertion point: after tags block
    insert_after = None
    in_tags = False
    for i, line in enumerate(fm_lines):
        if line.strip().startswith("tags:"):
            in_tags = True
            insert_after = i
        elif in_tags:
            if line.startswith("  ") or line.startswith("- "):
                insert_after = i
            else:
                in_tags = False

    if insert_after is not None:
        fm_lines.insert(insert_after + 1, kw_yaml)
    else:
        fm_lines.append(kw_yaml)

    new_fm = "\n".join(fm_lines)
    path.write_text(f"---{new_fm}\n---{body}", encoding="utf-8")
    return True


def main():
    files = list(EVENTS_DIR.rglob("*.md"))
    updated = 0
    skipped = 0
    for f in files:
        try:
            if process_file(f):
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR {f.name}: {e}", file=sys.stderr)

    print(f"Keywords added to {updated} files, {skipped} already had keywords or were skipped.")
    print("Run publication_pipeline.py to rebuild events.json.")


if __name__ == "__main__":
    main()
