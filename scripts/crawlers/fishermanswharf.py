#!/usr/bin/env python3
"""Macau Fisherman's Wharf official dated events/promotions crawler."""

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler, CrawledEvent


class FishermansWharfCrawler(BaseCrawler):
    """Crawl only scheduled events and explicitly dated hospitality offers."""

    name = "fishermanswharf.com.mo"
    base_url = "https://www.fishermanswharf.com.mo"
    rate_limit = 3.0
    priority = "low"
    frequency = "weekly"
    languages = ["en"]

    EVENT_TERMS = (
        "event", "expo", "exhibition", "carnival", "festival", "concert",
        "show", "performance", "workshop", "market",
    )
    HOSPITALITY_TERMS = (
        "buffet", "brunch", "feast", "tasting", "wine", "cocktail",
        "bar", "chef", "tea gathering", "dinner", "lunch",
    )
    EXCLUDED_TERMS = (
        "hotel package", "getaway", "voucher", "parking", "wedding",
        "banquet package", "moon cake", "mooncake", "health club",
        "pet", "birthday treat", "set menu", "specialties", "delights",
    )

    async def fetch_list_urls(self) -> List[str]:
        urls = set()
        seeds = (
            f"{self.base_url}/whats-on/",
            f"{self.base_url}/promotions/",
        )
        for seed in seeds:
            try:
                soup = self._soup(await self.fetch_html(seed))
                for link in soup.select("a[href]"):
                    label = link.get_text(" ", strip=True).lower()
                    href = urljoin(seed, link.get("href", "")).split("?", 1)[0]
                    parsed = urlparse(href)
                    if parsed.hostname not in {"fishermanswharf.com.mo", "www.fishermanswharf.com.mo"}:
                        continue
                    if href.rstrip("/") == seed.rstrip("/") or href.count("/") != 4:
                        continue
                    if any(term in label for term in self.EXCLUDED_TERMS):
                        continue
                    terms = self.EVENT_TERMS if "whats-on" in seed else self.HOSPITALITY_TERMS
                    if any(term in label for term in terms):
                        urls.add(href)
            except Exception as exc:
                self.logger.warning(f"Failed to fetch {seed}: {exc}")
        return sorted(urls)

    def _explicit_range(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Parse only source-stated ranges; never turn 'from now' into a date."""
        text = re.sub(r"\s+", " ", text)
        month_names = (
            "January|February|March|April|May|June|July|August|September|October|November|December|"
            "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
        )
        months = {name.lower(): index for index, names in enumerate((
            ("january", "jan"), ("february", "feb"), ("march", "mar"),
            ("april", "apr"), ("may",), ("june", "jun"), ("july", "jul"),
            ("august", "aug"), ("september", "sep"), ("october", "oct"),
            ("november", "nov"), ("december", "dec"),
        ), 1) for name in names}

        def iso(year: str, month: str, day: str) -> Optional[str]:
            try:
                return datetime(int(year), months[month.lower()], int(day)).strftime("%Y-%m-%d")
            except (KeyError, TypeError, ValueError):
                return None

        patterns = (
            # September 4-6, 2026 / September 5 – 6, 2026
            (rf"\b({month_names})\s+(\d{{1,2}})\s*(?:-|–|—|to|until)\s*(\d{{1,2}}),?\s+(20\d{{2}})\b", "same"),
            # 29 Mar until 30 Sep 2026
            (rf"\b(\d{{1,2}})\s+({month_names})\s*(?:-|–|—|to|until)\s*(\d{{1,2}})\s+({month_names})\s+(20\d{{2}})\b", "cross"),
            # Mar 29 until Sep 30, 2026
            (rf"\b({month_names})\s+(\d{{1,2}})\s*(?:-|–|—|to|until)\s*({month_names})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b", "cross_mdy"),
        )
        for pattern, kind in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            values = match.groups()
            if kind == "same":
                month, d1, d2, year = values
                return iso(year, month, d1), iso(year, month, d2)
            if kind == "cross":
                d1, m1, d2, m2, year = values
                return iso(year, m1, d1), iso(year, m2, d2)
            m1, d1, m2, d2, year = values
            return iso(year, m1, d1), iso(year, m2, d2)
        return None, None

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        text = soup.get_text(" ", strip=True)
        lower = text.lower()
        title_node = soup.select_one("h1")
        title = title_node.get_text(" ", strip=True) if title_node else ""
        if not title:
            meta = soup.select_one('meta[property="og:title"]')
            title = meta.get("content", "").split(" - Macau Fisherman", 1)[0].strip() if meta else ""
        title_lower = title.lower()

        if any(term in title_lower for term in self.EXCLUDED_TERMS):
            return None
        is_hospitality = any(term in title_lower for term in self.HOSPITALITY_TERMS)
        is_public_event = any(term in title_lower for term in self.EVENT_TERMS)
        if not (is_hospitality or is_public_event):
            return None

        start, end = self._explicit_range(text)
        if not start:
            return None

        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = "en"
        event.title = title
        event.start_date = start
        event.end_date = end or start
        event.organizer = "Macau Fisherman's Wharf"
        event.organizer_type = "venue"
        event.organizer_url = self.base_url
        event.district = "Macau Peninsula"
        event.address = "Avenida da Amizade e Avenida Dr. Sun Yat-Sen, Macau"
        event.venue_name = "Macau Fisherman's Wharf"
        event.venue_type = "waterfront"
        event.category = "dining" if is_hospitality else "exhibition"
        event.tags = ["official-venue", "dated-offer" if is_hospitality else "scheduled-event"]

        venue_patterns = (
            ("vic’s restaurant", "Vic's Restaurant", "restaurant"),
            ("vic's restaurant", "Vic's Restaurant", "restaurant"),
            ("praha restaurante", "Praha Restaurante", "restaurant"),
            ("praha bar", "Praha Bar", "bar"),
            ("terra mar", "Terra Mar", "restaurant"),
            ("jade orchid", "Jade Orchid", "restaurant"),
            ("the grand palace", "The Grand Palace", "restaurant"),
            ("convention and exhibition centre", "Convention and Exhibition Centre, Macau Fisherman's Wharf", "convention_center"),
        )
        for needle, venue, venue_type in venue_patterns:
            if needle in lower:
                event.venue_name = venue
                event.venue_type = venue_type
                break

        if "every sunday" in lower:
            event.recurring = True
            event.recurrence_rule = "FREQ=WEEKLY;BYDAY=SU;UNTIL=" + event.end_date.replace("-", "")
            event.tags.append("weekly")
        if "bar" in title_lower or "cocktail" in title_lower:
            event.category = "nightlife"
        elif "expo" in title_lower or "exhibition" in title_lower:
            event.category = "exhibition"
        elif "carnival" in title_lower or "festival" in title_lower or "market" in title_lower:
            event.category = "festival"

        time_match = re.search(r"(?:Opening Hours|Supply Hours|Time)\s*:\s*(\d{1,2}):(\d{2})\s*(?:-|–|—|to)\s*(\d{1,2}):(\d{2})", text, re.IGNORECASE)
        if time_match:
            event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
            event.end_time = f"{int(time_match.group(3)):02d}:{time_match.group(4)}"

        description_node = soup.select_one('meta[property="og:description"]')
        event.description = (description_node.get("content", "") if description_node else text)[:5000]
        image_node = soup.select_one('meta[property="og:image"]')
        if image_node and image_node.get("content"):
            event.featured_image = urljoin(url, image_node["content"])
            event.images = [{"url": event.featured_image, "primary": True}]

        prices = [float(value.replace(",", "")) for value in re.findall(r"MOP\s*([\d,]+)", text, re.IGNORECASE)]
        if prices:
            event.ticket_price_min = min(prices)
            event.ticket_price_max = max(prices)
            event.ticket_currency = "MOP"
            event.ticket_info = f"Source-listed prices: MOP {min(prices):,.0f}–{max(prices):,.0f}"

        source_id = urlparse(url).path.strip("/")
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        return event
