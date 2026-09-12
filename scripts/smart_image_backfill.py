#!/usr/bin/env python3
"""
Smart image backfill — finds the best matching image from each event's source URL.

Improvement over enrich_images.py:
- Scores candidates by relevance to event title (filename keywords, alt text, proximity to heading)
- Prefers og:image / twitter:image / JSON-LD (authoritative hero images)
- Looks for images near the event heading in the DOM
- Filters out icons, logos, navigation images, social buttons
- Picks largest / highest-resolution candidate when score is tied
- Runs on ALL events missing an image (checks published/events.json)
"""

import json
from typing import Optional, List
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = ROOT / "events"
PUBLISHED = ROOT / "published" / "events.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Tokens that indicate non-event images
BAD_TOKENS = (
    "logo", "icon", "favicon", "facebook", "youtube", "twitter",
    "instagram", "/frame/", "sprite", "arrow", "close", "menu",
    "footer", "header-bg", "nav-", "social", "share-", "button",
    "qr-", "/ads/", "banner-bg", "background-", "border-", "divider",
)

IMG_EXT = re.compile(r"\.(jpg|jpeg|png|webp|gif)(\?|$|#|&)", re.I)


def title_keywords(title: str) -> List[str]:
    """Return meaningful words from the event title for image relevance scoring."""
    stopwords = {"in", "the", "a", "an", "of", "and", "at", "for", "with", "to", "from", "is", "on"}
    words = re.findall(r"[a-zA-Z]{4,}", title)
    return [w.lower() for w in words if w.lower() not in stopwords]


def score_image(url: str, alt: str, classes: str, keywords: List[str]) -> int:
    """Higher score = better image."""
    score = 0
    low = url.lower()

    # Penalise bad tokens
    if any(t in low for t in BAD_TOKENS):
        return -999

    # Must look like an image
    if not IMG_EXT.search(low) and "/image" not in low and "/photo" not in low and "/media" not in low:
        score -= 10

    # Title keyword in URL path or alt text
    combined = (low + " " + alt.lower() + " " + classes.lower())
    for kw in keywords:
        if kw in combined:
            score += 12

    # Hero/feature class names
    for good_class in ("hero", "feature", "banner", "event", "cover", "main", "poster", "key-visual", "thumbnail"):
        if good_class in classes.lower():
            score += 8

    # High-resolution hints in URL
    for dim in ("1920", "1280", "1200", "1080", "800", "1600"):
        if dim in url:
            score += 4

    # Shallow URL path (likely a top-level event asset, not a sidebar thumb)
    depth = url.count("/") - 2  # subtract protocol slashes
    if depth < 5:
        score += 3

    # Penalise small-looking thumbnails
    for small_cls in ("thumb", "small", "avatar", "icon", "nav", "sidebar"):
        if small_cls in classes.lower():
            score -= 6

    return score


def extract_best_image(url: str, title: str) -> tuple:
    """
    Fetch the page at `url` and return (best_image_url, debug_note).
    Tries multiple extraction strategies, scores all candidates, returns best.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return None, f"fetch_error: {e}"

    soup = BeautifulSoup(html, "html.parser")
    keywords = title_keywords(title)
    candidates: list = []  # (score, url, source)

    # ── 1. OG / Twitter meta (authoritative hero images, always score highest) ────
    for sel, bonus in [
        ('meta[property="og:image"]', 200),
        ('meta[property="og:image:secure_url"]', 200),
        ('meta[name="twitter:image"]', 190),
        ('meta[name="twitter:image:src"]', 190),
    ]:
        for tag in soup.select(sel):
            src = tag.get("content", "").strip()
            if src and not any(t in src.lower() for t in BAD_TOKENS):
                abs_url = urljoin(url, src)
                s = bonus + score_image(abs_url, "", "", keywords)
                candidates.append((s, abs_url, "og/meta"))

    # ── 2. JSON-LD image ──────────────────────────────────────────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                # Also look inside @graph
                graph = node.get("@graph", []) if isinstance(node, dict) else []
                for item in ([node] + graph):
                    img = item.get("image") if isinstance(item, dict) else None
                    if not img:
                        continue
                    if isinstance(img, dict):
                        img = img.get("url") or img.get("@id", "")
                    if isinstance(img, list):
                        img = img[0]
                        if isinstance(img, dict):
                            img = img.get("url", "")
                    if isinstance(img, str) and img:
                        abs_url = urljoin(url, img)
                        if not any(t in abs_url.lower() for t in BAD_TOKENS):
                            s = 180 + score_image(abs_url, "", "", keywords)
                            candidates.append((s, abs_url, "json-ld"))
        except Exception:
            pass

    # ── 3. <img> tags near headings and within event/article containers ───────────
    # First try: find the event heading, walk siblings for images
    heading = None
    for h in soup.find_all(["h1", "h2"]):
        h_text = h.get_text(strip=True)
        if any(kw in h_text.lower() for kw in keywords) or len(h_text) > 10:
            heading = h
            break

    nearby_imgs: list = []
    if heading:
        # Look forward in DOM for imgs within next 5 siblings
        for sib in list(heading.next_siblings)[:10]:
            nearby_imgs += (sib.find_all("img") if hasattr(sib, "find_all") else [])
        # Also parent container
        parent = heading.parent
        if parent:
            nearby_imgs += parent.find_all("img")

    for img in (nearby_imgs or soup.find_all("img")):
        src = (
            img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            or img.get("data-original") or img.get("data-image") or ""
        )
        if not src:
            continue
        abs_url = urljoin(url, src)
        alt = img.get("alt", "")
        classes = " ".join(img.get("class", []))
        s = score_image(abs_url, alt, classes, keywords)
        if s > -100:  # skip only clearly bad ones
            bonus = 20 if img in nearby_imgs else 0
            candidates.append((s + bonus, abs_url, "img"))

    if not candidates:
        return None, "no_candidates"

    candidates.sort(key=lambda x: -x[0])
    best_score, best_url, best_src = candidates[0]

    if best_score < -50:
        return None, f"all_low_score (best={best_score})"

    return best_url, f"score={best_score} src={best_src} (from {len(candidates)} candidates)"


def read_event_md(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    try:
        fm = yaml.safe_load(parts[1]) or {}
        fm["_raw"] = raw
        fm["_path"] = path
        return fm
    except Exception:
        return {}


def write_image_to_md(path: Path, image_url: str) -> bool:
    """Write featured_image into the event markdown frontmatter."""
    raw = path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return False
    fm_text = parts[1]
    # Remove any existing (empty) featured_image line
    fm_text = re.sub(r'^featured_image:.*\n', '', fm_text, flags=re.M)
    fm_text = re.sub(r'^image:.*\n', '', fm_text, flags=re.M)
    # Insert after source_url line, or at end of frontmatter
    marker = re.search(r'^source_url:.*$', fm_text, re.M)
    insert_after = marker.end() if marker else len(fm_text.rstrip())
    clean_url = image_url.strip().replace('"', '')
    fm_text = fm_text[:insert_after] + f'\nfeatured_image: "{clean_url}"' + fm_text[insert_after:]
    path.write_text("---".join([parts[0], fm_text, parts[2]]), encoding="utf-8")
    return True


def process_event(slug: str, title: str, source_url: str) -> tuple[str, Optional[str], str]:
    """Process one event: returns (slug, image_url_or_None, note)."""
    if not source_url:
        return slug, None, "no_source_url"
    img, note = extract_best_image(source_url, title)
    return slug, img, note


def main():
    # Load published events to find those missing images
    with open(PUBLISHED) as f:
        published = json.load(f)

    missing = [
        e for e in published
        if not (e.get("image") or e.get("featured_image"))
    ]
    print(f"Events missing images: {len(missing)} of {len(published)}")

    # Build slug → path mapping for wiki markdown files
    slug_to_path: dict = {}
    for md in EVENTS_DIR.rglob("*.md"):
        if md.name == "index.md":
            continue
        slug_to_path[md.stem] = md

    results: list[tuple[str, Optional[str], str]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(
                process_event,
                e.get("slug", ""),
                e.get("title", ""),
                e.get("sourceUrl") or e.get("source_url") or "",
            ): e
            for e in missing
        }
        for future in as_completed(futures):
            try:
                slug, img, note = future.result()
                results.append((slug, img, note))
                status = f"✓ {img[:80]}" if img else f"✗ {note}"
                print(f"  {slug[:55]:55s} {status}")
            except Exception as exc:
                e = futures[future]
                print(f"  ERROR {e.get('slug', '?')}: {exc}")

    # Write results back to wiki markdown files
    updated = 0
    not_found_in_wiki = []
    for slug, img, note in results:
        if not img:
            continue
        path = slug_to_path.get(slug)
        if not path:
            not_found_in_wiki.append(slug)
            continue
        if write_image_to_md(path, img):
            print(f"WRITTEN: {path.relative_to(ROOT)}")
            updated += 1

    print(f"\n── Summary ──")
    print(f"Images found:  {sum(1 for _, img, _ in results if img)}")
    print(f"Written to MD: {updated}")
    print(f"Not in wiki:   {len(not_found_in_wiki)}")
    if not_found_in_wiki:
        for s in not_found_in_wiki:
            print(f"  missing md: {s}")


if __name__ == "__main__":
    main()
