"""
Cuba Macao Nightclub Crawler
Domain: cubamacao.com
Tier 3 — weekly crawl
Primary: https://www.cubamacao.com/events
Fallback: static homepage (limited info), no events section
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

from .base import BaseCrawler, CrawledEvent


class CubaMacaoCrawler(BaseCrawler):
    name = "cubamacao.com"
    base_url = "https://www.cubamacao.com"
    rate_limit = 3.0
    frequency = "weekly"

    SEED_URLS = [
        "https://www.cubamacao.com/events",
        "https://www.cubamacao.com/whats-on",
        "https://www.cubamacao.com/",
    ]

    # Cuba Macao — nightclub in the Grand Lisboa Hotel basement
    VENUE_NAME = "Cuba Macao"
    VENUE_ADDRESS = "Grand Lisboa Hotel, Avenida de Lisboa, Macau"
    VENUE_COORDINATES = {"lat": 22.1937, "lng": 113.5418}

    async def fetch_list_urls(self) -> List[str]:
        """Try each seed with Playwright (JS-heavy nightclub sites)."""
        found: list[str] = []
        seen: set[str] = set()

        for seed in self.SEED_URLS:
            try:
                html = await self.fetch_html_js(
                    seed,
                    wait_until="networkidle",
                    timeout=25000,
                )
                urls = self._extract_event_links(html, seed)
                for u in urls:
                    if u not in seen:
                        seen.add(u)
                        found.append(u)
                if found:
                    break  # stop on first seed that yields results
            except Exception as e:
                self.logger.warning("Cuba Macao seed %s failed: %s", seed, e)

        if not found:
            self.logger.warning(
                "Cuba Macao: no event URLs found — site may be down or events-only on social media"
            )
        return found

    def _extract_event_links(self, html: str, base: str) -> List[str]:
        """Pull event-detail links from a listing page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []

        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()
            full = urljoin(base, href)
            # Keep internal event/show detail pages
            if (
                "cubamacao.com" in full
                and any(
                    seg in full
                    for seg in ["/event", "/show", "/night", "/party", "/whats-on/"]
                )
                and full not in links
            ):
                links.append(full)

        return links[:30]

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Try JSON-LD first
        event = self._parse_jsonld(url, soup)
        if event:
            self._apply_venue_defaults(event)
            return event

        # HTML fallback
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
            categories=["nightlife"],
            tags=["nightclub", "cuba", "latin", "dance"],
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
        """Extract event from JSON-LD schema.org markup."""
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
                image = data.get("image")
                if isinstance(image, dict):
                    image = image.get("url", "")
                elif isinstance(image, list):
                    image = image[0] if image else ""

                loc = data.get("location", {})
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                ticket_url = offers.get("url", "")
                price = str(offers.get("price", "")).strip()
                currency = offers.get("priceCurrency", "MOP")
                ticket_price = f"{currency} {price}".strip() if price else None

                event = CrawledEvent(
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
                    categories=["nightlife"],
                    tags=["nightclub", "cuba", "latin", "dance"],
                    language="en",
                    ticket_url=ticket_url or url,
                    ticket_price=ticket_price,
                    images=[image] if image else [],
                    raw_source_url=url,
                )
                return event
            except Exception:
                continue
        return None

    def _extract_title(self, soup) -> str:
        for sel in ["h1", "h2.event-title", ".event-name", "title"]:
            el = soup.select_one(sel)
            if el:
                t = el.get_text(" ", strip=True)
                if t and t.lower() not in {"cuba macao", "home", "events"}:
                    return t
        return ""

    def _extract_description(self, soup) -> str:
        for sel in [".event-description", ".description", "article p", "main p"]:
            el = soup.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)[:1000]
        return ""

    def _extract_date(self, soup) -> Optional[str]:
        # Look for date text patterns: "Friday, 20 September 2024"
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
            href: str = a["href"]
            text = a.get_text(strip=True).lower()
            if any(k in text for k in ["ticket", "book", "reserve", "buy"]):
                return urljoin(base_url, href)
        return base_url

    def _extract_price(self, soup) -> Optional[str]:
        text = soup.get_text(" ")
        m = re.search(r"(?:MOP|HKD|USD)?\s*\$?\s*(\d[\d,]*(?:\.\d{2})?)", text)
        if m:
            return f"MOP {m.group(1)}"
        return None

    def _extract_images(self, soup, base_url: str) -> List[str]:
        imgs = []
        for img in soup.find_all("img", src=True):
            src = urljoin(base_url, img["src"])
            if any(skip in src for skip in ["logo", "icon", "thumb", "avatar"]):
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
            event.categories = ["nightlife"]
