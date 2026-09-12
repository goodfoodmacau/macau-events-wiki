"""
Macau News Agency Crawler
Domain: macaunews.mo (or macaunews.com.mo)
Tier 3 — weekly crawl
Macau News is an English-language news outlet that covers events and happenings in Macau.
Events are found in the Lifestyle / Events sections of the site.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from .base import BaseCrawler, CrawledEvent


class MacauNewsCrawler(BaseCrawler):
    name = "macaunews.mo"
    base_url = "https://www.macaunews.mo"
    rate_limit = 2.0
    frequency = "weekly"

    SEED_URLS = [
        "https://www.macaunews.mo/category/lifestyle/events/",
        "https://www.macaunews.mo/category/events/",
        "https://www.macaunews.mo/lifestyle/",
        "https://www.macaunews.mo/",
        # fallback domain
        "https://macaunews.com.mo/category/lifestyle/events/",
    ]

    async def fetch_list_urls(self) -> List[str]:
        found: list[str] = []
        seen: set[str] = set()

        for seed in self.SEED_URLS:
            try:
                html = await self.fetch_html_smart(seed)
                urls = self._extract_article_links(html, seed)
                for u in urls:
                    if u not in seen:
                        seen.add(u)
                        found.append(u)
                if found:
                    # Also crawl page 2 of successful seed to get more events
                    try:
                        html2 = await self.fetch_html_smart(seed.rstrip("/") + "/page/2/")
                        for u in self._extract_article_links(html2, seed):
                            if u not in seen:
                                seen.add(u)
                                found.append(u)
                    except Exception:
                        pass
                    break
            except Exception as e:
                self.logger.warning("Macau News seed %s failed: %s", seed, e)

        if not found:
            self.logger.info("Macau News: no article/event URLs found on this run.")
        return found[:50]

    def _extract_article_links(self, html: str, base: str) -> List[str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        allowed = {"macaunews.mo", "macaunews.com.mo"}

        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()
            full = urljoin(base, href)
            # Macau News uses WordPress-style /{year}/{month}/{day}/{slug}/ URLs
            if (
                any(d in full for d in allowed)
                and re.search(r"/\d{4}/\d{2}/\d{2}/", full)
                and full not in links
            ):
                links.append(full)

        return links[:50]

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        """
        Macau News articles often describe events but are news articles, not
        structured event listings. We extract what we can and mark the
        publication_status as 'review' so editors can verify.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Only process articles that are clearly about events
        title = self._extract_title(soup)
        if not title:
            return None
        if not self._is_event_article(title, soup):
            return None

        event = self._parse_jsonld(url, soup)
        if event:
            event.data_quality = event.data_quality or {}
            event.data_quality["source_type"] = "news_article"
            return event

        description = self._extract_description(soup)
        start_date = self._extract_date(soup)
        venue_name = self._extract_venue(soup)

        event = CrawledEvent(
            guid=self._make_guid(url),
            url=url,
            source=self.name,
            title=title,
            description=description,
            start_date=start_date,
            venue_name=venue_name,
            categories=self._guess_category(title, description),
            tags=["macau", "news", "event"],
            language="en",
            ticket_url=self._extract_ticket_url(soup, url),
            ticket_price=self._extract_price(soup),
            images=self._score_and_rank_images(
                self._extract_images(soup, url), url
            ),
            raw_source_url=url,
            # Mark for editorial review since this is a news article, not a venue page
            publication_status="review",
        )
        return event

    def _is_event_article(self, title: str, soup) -> bool:
        """Return True if this article is about a specific upcoming event."""
        text = f"{title} {soup.get_text(' ')[:500]}".lower()
        # Must mention upcoming event signals
        event_signals = [
            "upcoming", "this weekend", "tonight", "this week",
            "exhibition", "concert", "performance", "festival",
            "show", "event", "opening", "launch", "ceremony",
        ]
        return any(sig in text for sig in event_signals)

    def _parse_jsonld(self, url: str, soup) -> Optional[CrawledEvent]:
        import json

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = next((d for d in data if d.get("@type") == "Event"), None)
                if not data or data.get("@type") != "Event":
                    continue
                name = data.get("name", "").strip()
                if not name:
                    continue

                start = data.get("startDate", "")
                end = data.get("endDate", "")
                image = data.get("image", "")
                if isinstance(image, list):
                    image = image[0] if image else ""
                elif isinstance(image, dict):
                    image = image.get("url", "")

                loc = data.get("location", {})
                venue_name = ""
                venue_address = ""
                if isinstance(loc, dict):
                    venue_name = loc.get("name", "")
                    addr = loc.get("address", {})
                    venue_address = (
                        addr.get("streetAddress", "") if isinstance(addr, dict) else str(addr)
                    )

                return CrawledEvent(
                    guid=self._make_guid(url),
                    url=url,
                    source=self.name,
                    title=name,
                    description=data.get("description", ""),
                    start_date=self._parse_date_str(start),
                    end_date=self._parse_date_str(end) if end else None,
                    venue_name=venue_name,
                    venue_address=venue_address,
                    categories=self._guess_category(name, data.get("description", "")),
                    tags=["macau"],
                    language="en",
                    ticket_url=data.get("offers", {}).get("url", url)
                    if isinstance(data.get("offers"), dict)
                    else url,
                    images=[image] if image else [],
                    raw_source_url=url,
                )
            except Exception:
                continue
        return None

    def _extract_title(self, soup) -> str:
        for sel in ["h1.entry-title", "h1.post-title", "h1", "title"]:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if t and "macau news" not in t.lower()[:20]:
                    return t.split("|")[0].split("–")[0].strip()
        return ""

    def _extract_description(self, soup) -> str:
        # WordPress article — get intro paragraph(s)
        paras = []
        for el in soup.select(".entry-content p, .post-content p, article p"):
            t = el.get_text(" ", strip=True)
            if len(t) > 50:
                paras.append(t)
            if len(" ".join(paras)) > 800:
                break
        return " ".join(paras)[:1200]

    def _extract_venue(self, soup) -> str:
        # News articles sometimes name the venue inline
        text = soup.get_text(" ")
        patterns = [
            r"(?:held|taking place|at|venue[:\s]+)\s+([A-Z][a-zA-Z\s&']{3,50}(?:Macau|Macao)?)",
            r"(?:location[:\s]+)([A-Z][a-zA-Z\s&']{3,50})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 3:
                    return candidate
        return ""

    def _extract_date(self, soup) -> Optional[str]:
        # WordPress publish date (article date ≠ event date, but better than nothing)
        meta = soup.find("meta", property="article:published_time")
        if meta and meta.get("content"):
            return self._parse_date_str(meta["content"])

        time_el = soup.select_one("time[datetime]")
        if time_el:
            return self._parse_date_str(time_el["datetime"])

        # Full-text date extraction
        text = soup.get_text(" ")
        patterns = [
            r"\b(\d{1,2}[\s/\-]\w+[\s/\-]\d{4})\b",
            r"\b(\w+day,?\s+\d{1,2}\s+\w+\s+\d{4})\b",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return self._parse_date_str(m.group(1))
        return None

    def _extract_ticket_url(self, soup, base_url: str) -> str:
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            href: str = a["href"]
            if any(k in text for k in ["ticket", "book", "reserve", "rsvp"]):
                return urljoin(base_url, href)
            # External ticketing links
            if any(d in href for d in ["eventbrite", "ticketmaster", "klook", "ticketek"]):
                return href
        return base_url

    def _extract_price(self, soup) -> Optional[str]:
        text = soup.get_text(" ")
        if re.search(r"\bfree\b", text, re.IGNORECASE):
            return "Free"
        m = re.search(r"(?:MOP|HKD)\s*\$?\s*(\d[\d,]*)", text)
        if m:
            return f"MOP {m.group(1)}"
        return None

    def _extract_images(self, soup, base_url: str) -> List[str]:
        imgs = []
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            imgs.append(og["content"])
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"])
            if any(skip in src.lower() for skip in ["logo", "icon", "avatar", "pixel", "ad-"]):
                continue
            if src not in imgs:
                imgs.append(src)
        return imgs[:10]

    def _guess_category(self, title: str, desc: str) -> List[str]:
        text = f"{title} {desc}".lower()
        cats = []
        if any(w in text for w in ["music", "concert", "band", "dj", "live music"]):
            cats.append("music")
        if any(w in text for w in ["art", "exhibit", "gallery", "museum", "installation"]):
            cats.append("arts")
        if any(w in text for w in ["food", "dining", "restaurant", "culinary", "taste", "brunch"]):
            cats.append("dining")
        if any(w in text for w in ["nightclub", "bar", "club", "lounge", "party"]):
            cats.append("nightlife")
        if any(w in text for w in ["sport", "run", "race", "marathon", "golf", "tennis"]):
            cats.append("sports")
        if any(w in text for w in ["family", "kid", "child", "children", "puppet", "magic"]):
            cats.append("family")
        if any(w in text for w in ["festival", "carnival", "parade", "firework"]):
            cats.append("festival")
        return cats or ["events"]
