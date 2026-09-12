"""
Bob Bar Macau Crawler
Domain: bobbarmacau.com
Tier 3 — weekly crawl
Bob Bar is a cocktail bar in Macau; primarily promotes via social media.
Crawler attempts the website but degrades gracefully when no events section exists.
"""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from .base import BaseCrawler, CrawledEvent


class BobBarCrawler(BaseCrawler):
    name = "bobbarmacau.com"
    base_url = "https://www.bobbarmacau.com"
    rate_limit = 3.0
    frequency = "weekly"

    SEED_URLS = [
        "https://www.bobbarmacau.com/events",
        "https://www.bobbarmacau.com/whats-on",
        "https://www.bobbarmacau.com/happenings",
        "https://www.bobbarmacau.com/",
    ]

    VENUE_NAME = "Bob Bar"
    VENUE_ADDRESS = "Wynn Palace, Cotai, Macau"
    VENUE_COORDINATES = {"lat": 22.1486, "lng": 113.5627}

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
                self.logger.warning("Bob Bar seed %s failed: %s", seed, e)
                continue

        if not found:
            self.logger.info(
                "Bob Bar: no event URLs found — site likely has no structured events page. "
                "Consider social media monitoring as an alternative."
            )
        return found

    def _extract_event_links(self, html: str, base: str) -> List[str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()
            full = urljoin(base, href)
            if (
                "bobbarmacau.com" in full
                and any(
                    seg in full
                    for seg in ["/event", "/whats-on/", "/happening", "/night", "/special"]
                )
                and full not in links
            ):
                links.append(full)
        return links[:20]

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # JSON-LD first
        event = self._parse_jsonld(url, soup)
        if event:
            self._apply_venue_defaults(event)
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
            venue_name=self.VENUE_NAME,
            venue_address=self.VENUE_ADDRESS,
            venue_lat=self.VENUE_COORDINATES["lat"],
            venue_lng=self.VENUE_COORDINATES["lng"],
            categories=["nightlife", "dining"],
            tags=["cocktail bar", "bob bar", "wynn palace", "drinks"],
            language="en",
            ticket_url=self._extract_ticket_url(soup, url),
            ticket_price=self._extract_price(soup),
            images=self._score_and_rank_images(
                self._extract_images(soup, url), url
            ),
            raw_source_url=url,
        )
        self._apply_venue_defaults(event)
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
                desc = data.get("description", "")
                image = data.get("image", "")
                if isinstance(image, list):
                    image = image[0] if image else ""
                elif isinstance(image, dict):
                    image = image.get("url", "")

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
                    description=desc,
                    start_date=self._parse_date_str(start),
                    end_date=self._parse_date_str(end) if end else None,
                    venue_name=self.VENUE_NAME,
                    venue_address=self.VENUE_ADDRESS,
                    venue_lat=self.VENUE_COORDINATES["lat"],
                    venue_lng=self.VENUE_COORDINATES["lng"],
                    categories=["nightlife", "dining"],
                    tags=["cocktail bar", "bob bar", "wynn palace", "drinks"],
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
        for sel in ["h1.event-title", "h1", ".post-title", "title"]:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if t and t.lower() not in {"bob bar", "home", "events", "happenings"}:
                    return t
        return ""

    def _extract_description(self, soup) -> str:
        for sel in [".event-content", ".description", "article p", "main p"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)[:1000]
        return ""

    def _extract_date(self, soup) -> Optional[str]:
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
            if any(k in text for k in ["ticket", "book", "reserve", "rsvp"]):
                return urljoin(base_url, a["href"])
        return base_url

    def _extract_price(self, soup) -> Optional[str]:
        text = soup.get_text(" ")
        m = re.search(r"(?:MOP|HKD)?\s*\$?\s*(\d[\d,]*(?:\.\d{2})?)", text)
        if m:
            return f"MOP {m.group(1)}"
        return None

    def _extract_images(self, soup, base_url: str) -> List[str]:
        imgs = []
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"])
            if any(skip in src.lower() for skip in ["logo", "icon", "avatar", "pixel"]):
                continue
            imgs.append(src)
        return imgs[:10]

    def _apply_venue_defaults(self, event: CrawledEvent) -> None:
        if not event.venue_name:
            event.venue_name = self.VENUE_NAME
        if not event.venue_address:
            event.venue_address = self.VENUE_ADDRESS
        if not event.venue_lat:
            event.venue_lat = self.VENUE_COORDINATES["lat"]
        if not event.venue_lng:
            event.venue_lng = self.VENUE_COORDINATES["lng"]
        if not event.categories:
            event.categories = ["nightlife", "dining"]
