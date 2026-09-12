#!/usr/bin/env python3
"""
Smart image enrichment for wiki event files.

For each event that has no featured_image, fetches its source_url and scores
candidate images by relevance to the event title.

Strategy (in priority order):
1. og:image / twitter:image meta tags
2. JSON-LD image field
3. DOM <img> tags near the title heading
4. Scored DOM <img> tags

JS fallback: if a plain HTTP fetch yields no og:image and fewer than 3 real
<img> tags (indicating JS-rendered content), Playwright headless Chromium
renders the page fully before extracting images.  Known JS-heavy domains
(Venetian, Wynn, Sands, MGM, etc.) always use Playwright directly.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "events"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Domains that gate all image content behind JavaScript.
JS_DOMAINS = (
    "venetianmacao.com",
    "sandsresortsmacao.cn",
    "sandsresorts",
    "wynnmacau.com",
    "mgm.mo",
    "melco-resorts.com",
    "studiocity-macau.com",
    "cityofdreamsmacau.com",
    "galaxymacau.com",
    "sjm.com.mo",
)

BAD_TOKENS = (
    "logo", "icon", "favicon", "facebook", "youtube", "twitter",
    "instagram", "/frame/", "sprite", "arrow", "close", "menu",
    "footer", "header-bg", "nav-", "social", "share-", "button",
    "qr-", "/ads/", "banner-bg", "background-", "border-", "divider",
)

IMG_EXT = re.compile(r"\.(jpg|jpeg|png|webp|gif)(\?|$|#|&)", re.I)


def title_keywords(title: str) -> list:
    stopwords = {"in", "the", "a", "an", "of", "and", "at", "for", "with", "to", "from", "is", "on"}
    words = re.findall(r"[a-zA-Z]{4,}", title)
    return [w.lower() for w in words if w.lower() not in stopwords]


def score_image(url: str, alt: str, classes: str, keywords: list) -> int:
    score = 0
    low = url.lower()
    if any(t in low for t in BAD_TOKENS):
        return -999
    if not IMG_EXT.search(low) and "/image" not in low and "/photo" not in low and "/media" not in low:
        score -= 10
    combined = low + " " + alt.lower() + " " + classes.lower()
    for kw in keywords:
        if kw in combined:
            score += 12
    for good_cls in ("hero", "feature", "banner", "event", "cover", "main", "poster", "key-visual", "thumbnail"):
        if good_cls in classes.lower():
            score += 8
    for dim in ("1920", "1280", "1200", "1080", "800", "1600"):
        if dim in url:
            score += 4
    depth = url.count("/") - 2
    if depth < 5:
        score += 3
    for small_cls in ("thumb-sm", "x-small", "avatar", "icon-", "nav-icon"):
        if small_cls in classes.lower():
            score -= 6
    return score


def _fetch_html_js(url: str) -> str:
    """
    Render a page with Playwright headless Chromium and return the full HTML.

    Uses a fresh browser launch per call (acceptable for batch enrichment runs
    that process a small number of JS-heavy pages).

    Uses wait_until="load" (not "networkidle") for Venetian/Sands because those
    sites keep persistent background connections that cause networkidle to time
    out after 30 s. After the load event, a gradual scroll triggers lazy-loaded
    images. Other JS domains still use "networkidle" for maximum image coverage.
    """
    from playwright.sync_api import sync_playwright

    # Domains with persistent background connections – use "load" only.
    LOAD_ONLY_DOMAINS = ("venetianmacao.com", "sandsresortsmacao.cn", "sandsresorts")
    wait_until = "load" if any(d in url for d in LOAD_ONLY_DOMAINS) else "networkidle"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        # Block heavy media to speed up load.
        context.route(
            "**/*.{mp4,avi,mov,wmv,flv,webm,mp3,wav,ogg,woff,woff2,ttf,eot,otf}",
            lambda route, _req: route.abort(),
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until=wait_until, timeout=30000)
            # Gradual scroll to trigger lazy-loaded images.
            page.evaluate("""
                () => new Promise(resolve => {
                    const dist = document.body.scrollHeight;
                    let pos = 0;
                    const step = Math.max(200, dist / 10);
                    const timer = setInterval(() => {
                        pos += step;
                        window.scrollTo(0, pos);
                        if (pos >= dist / 2) { clearInterval(timer); resolve(); }
                    }, 120);
                })
            """)
            page.wait_for_timeout(1500)
            html = page.content()
        finally:
            context.close()
            browser.close()
    return html


def _needs_js(url: str) -> bool:
    return any(d in url for d in JS_DOMAINS)


def _fetch_html_smart(url: str):
    """
    Return (html, used_js).  Uses Playwright for known JS-heavy domains and
    falls back to Playwright automatically when a plain fetch yields sparse
    content (no og:image and fewer than 3 real <img> tags).
    """
    if _needs_js(url):
        return _fetch_html_js(url), True

    try:
        resp = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content", "").startswith("http"):
            return html, False  # Good static og:image

        real_imgs = [
            img for img in soup.find_all("img")
            if img.get("src", "").startswith("http")
            and not any(t in img.get("src", "").lower() for t in BAD_TOKENS)
        ]
        if len(real_imgs) >= 3:
            return html, False  # Enough real images — probably not JS-gated

        # Sparse content; try JS rendering as fallback.
        return _fetch_html_js(url), True
    except Exception:
        return _fetch_html_js(url), True


def extract_best_image(url: str, title: str) -> str | None:
    """Fetch the event page and return the best candidate image URL, or None."""
    try:
        html, _ = _fetch_html_smart(url)
    except Exception as exc:
        print(f"    ⚠  fetch failed: {exc}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    keywords = title_keywords(title)

    # 1. og:image / twitter:image
    for prop in ("og:image", "twitter:image"):
        tag = soup.find("meta", attrs={"property": prop}) or \
              soup.find("meta", attrs={"name": prop})
        if tag:
            img_url = tag.get("content", "").strip()
            if img_url.startswith("http") and IMG_EXT.search(img_url):
                return img_url

    # 2. JSON-LD image
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            img = data.get("image") or data.get("thumbnailUrl")
            if isinstance(img, dict):
                img = img.get("url", "")
            if isinstance(img, list):
                img = img[0] if img else ""
            if img and str(img).startswith("http") and IMG_EXT.search(str(img)):
                return str(img)
        except Exception:
            pass

    # 3. Scored DOM <img> candidates
    base = url
    candidates = []
    for img in soup.find_all("img"):
        src = (img.get("src") or img.get("data-src") or
               img.get("data-lazy-src") or "")
        if not src:
            continue
        src = urljoin(base, src)
        alt = img.get("alt", "")
        classes = " ".join(img.get("class", []))
        s = score_image(src, alt, classes, keywords)
        if s > -999:
            candidates.append((s, src))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_url = candidates[0]
        if best_score >= 0:
            return best_url

    return None


def load_event(path: Path):
    """Parse an event markdown file, returning (frontmatter_dict, fm_raw, body)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, None, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, None, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None, None, text
    return fm, parts[1], parts[2]


def process_event(path: Path) -> tuple[str, bool]:
    """Process one event file. Returns (status_message, changed)."""
    fm, _, body = load_event(path)
    if fm is None:
        return f"  skip (no frontmatter): {path.name}", False

    if fm.get("featured_image"):
        return f"  ok (has image): {path.name}", False

    source_url = fm.get("source_url") or fm.get("website")
    if not source_url or not str(source_url).startswith("http"):
        return f"  skip (no url): {path.name}", False

    title = fm.get("title", path.stem)
    print(f"  → {path.name}")
    print(f"    url: {source_url}")

    img = extract_best_image(str(source_url), str(title))
    if not img:
        return f"  no image found: {path.name}", False

    print(f"    image: {img}")

    fm["featured_image"] = img
    new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_text = f"---\n{new_fm}---{body}"
    path.write_text(new_text, encoding="utf-8")
    return f"  ✓ saved: {path.name}", True


def main():
    event_files = sorted(EVENTS.rglob("evt-*.md"))

    # Collect events that need images
    needs_image = []
    for p in event_files:
        fm, _, _ = load_event(p)
        if fm is None or fm.get("featured_image"):
            continue
        url = str(fm.get("source_url") or fm.get("website") or "")
        if url.startswith("http"):
            needs_image.append(p)

    print(f"Events needing images: {len(needs_image)}")
    if not needs_image:
        return

    # JS-heavy pages must be processed serially (Playwright isn't thread-safe
    # across contexts in sync_playwright when forked via ThreadPoolExecutor).
    def event_url(p):
        fm, _, _ = load_event(p)
        return str(fm.get("source_url") or fm.get("website") or "")

    js_events = [p for p in needs_image if _needs_js(event_url(p))]
    plain_events = [p for p in needs_image if not _needs_js(event_url(p))]

    changed = 0

    if js_events:
        print(f"\nJS-heavy events ({len(js_events)}) — processing serially:")
        for p in js_events:
            msg, ok = process_event(p)
            print(msg)
            if ok:
                changed += 1

    if plain_events:
        print(f"\nPlain HTTP events ({len(plain_events)}) — processing in parallel:")
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(process_event, p): p for p in plain_events}
            for fut in as_completed(futures):
                msg, ok = fut.result()
                print(msg)
                if ok:
                    changed += 1

    print(f"\nDone. Updated {changed} events.")


if __name__ == "__main__":
    main()
