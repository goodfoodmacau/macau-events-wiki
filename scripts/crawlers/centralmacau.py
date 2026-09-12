"""
Central Macau Crawler
Domain: centralmacau.com
Tier 3 — weekly crawl
Central Macau is a lifestyle/events guide for Macau.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from .base import BaseCrawler, CrawledEvent


class CentralMacauCrawler(BaseCrawler):
    name = "centralmacau.com"
    base_url = "https://www.centralmacau.com"
    rate_limit = 2.0
    frequency = "weekly"

    SEED_URLS = [
        "https://www.centralmacau.com/events",
        "https://www.centralmacau.com/whats-on",
        "https://www.centralmacau.com/things-to-do",
        "https://www.centralmacau.com/",
    ]

    async def fetch_list_urls(self) -> List[str]:
        found: list[str] = []
        seen: set[str] = set()

        for seed in self.SEED_URLS:
            try:
                html = await self.fetch_html_smart(seed)
                urls = self._extract_event_links(html, seed)
                for u in urls:
                    if u not in seen:
                        seen.add(u)
                        found.append(u)
                if found:
                    break
            except Exception as e:
                self.logger.warning("Central Macau seed %s failed: %s", seed, e)

        if not found:
            self.logger.info("Central Macau: no event URLs found on this run.")
        return found

    def _extract_event_links(self, html: str, base: str) -> List[str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []

        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()
            full = urljoin(base, href)
            if (
                "centralmacau.com" in full
                and any(
                    seg in full
                    for seg in ["/event", "/whats-on/", "/things-to-do/", "/article", "/post/"]
                )
                and full not in links
            ):
                links.append(full)

        return links[:40]

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        event = self._parse_jsonld(url, soup)
        if event:
            return event

        title = self._extract_title(soup)
        if not title:
            return None

        event = CrawledEvent(
            guid=self._make_guid(url),
            url=url,
            source=self.name,
            title=title,
            description=self._extract_description(soup),
            start_date=self._extract_date(soup),
            venue_name=self._extract_venue(soup),
            categories=self._guess_category(title, self._extract_description(soup)),
            tags=["macau", "things to do", "central macau"],
            language="en",
            ticket_url=self._extract_ticket_url(soup, url),
            ticket_price=self._extract_price(soup),
            images=self._score_and_rank_images(
                self._extract_images(soup, url), url
            ),
            raw_source_url=url,
        )
        return event

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
                    if isinstance(addr, dict):
                        venue_address = addr.get("streetAddress", "")
                    elif isinstance(addr, str):
                        venue_address = addr

                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                ticket_url = offers.get("url", url)
                price = str(offers.get("price", "")).strip()
                currency = offers.get("priceCurrency", "MOP")
                ticket_price = f"{currency} {price}".strip() if price else None

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
                    ticket_url=ticket_url,
                    ticket_price=ticket_price,
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
                if t and "central macau" not in t.lower():
                    return t
        return ""

    def _extract_description(self, soup) -> str:
        for sel in [".entry-content p", ".post-content p", "article p", "main p"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)[:1000]
        return ""

    def _extract_venue(self, soup) -> str:
        for sel in [".venue", ".location", ".event-venue", ".address"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)[:200]
        return ""

    def _extract_date(self, soup) -> Optional[str]:
        # Try meta tags first
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "") or meta.get("name", "")
            if "date" in prop.lower() or "event" in prop.lower():
                content = meta.get("content", "")
                if content:
                    parsed = self._parse_date_str(content)
                    if parsed:
                        return parsed

        text = soup.get_text(" ")
        patterns = [
            r"\b(\d{1,2}[\s/\-]\w+[\s/\-]\d{4})\b",
            r"\b(\w+day,?\s+\d{1,2}\s+\w+\s+\d{4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return self._parse_date_str(m.group(1))
        return None

    def _extract_ticket_url(self, soup, base_url: str) -> str:
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if any(k in text for k in ["ticket", "book", "reserve", "buy now", "get tickets"]):
                return urljoin(base_url, a["href"])
        return base_url

    def _extract_price(self, soup) -> Optional[str]:
        text = soup.get_text(" ")
        m = re.search(r"(?:MOP|HKD|free|Free)\s*\$?\s*(\d[\d,]*(?:\.\d{2})?)?", text)
        if m:
            if "free" in m.group(0).lower():
                return "Free"
            if m.group(1):
                return f"MOP {m.group(1)}"
        return None

    def _extract_images(self, soup, base_url: str) -> List[str]:
        imgs = []
        # Open graph image first
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            imgs.append(og["content"])
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"])
            if any(skip in src.lower() for skip in ["logo", "icon", "avatar", "pixel", "banner-ad"]):
                continue
            if src not in imgs:
                imgs.append(src)
        return imgs[:10]

    def _guess_category(self, title: str, desc: str) -> List[str]:
        text = f"{title} {desc}".lower()
        cats = []
        if any(w in text for w in ["music", "concert", "band", "dj", "live"]):
            cats.append("music")
        if any(w in text for w in ["art", "exhibit", "gallery", "museum"]):
            cats.append("arts")
        if any(w in text for w in ["food", "dining", "restaurant", "culinary", "taste"]):
            cats.append("dining")
        if any(w in text for w in ["nightclub", "bar", "club", "lounge", "party"]):
            cats.append("nightlife")
        if any(w in text for w in ["sport", "run", "race", "marathon", "golf"]):
            cats.append("sports")
        if any(w in text for w in ["family", "kid", "child", "children"]):
            cats.append("family")
        return cats or ["events"]
