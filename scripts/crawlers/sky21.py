#!/usr/bin/env python3
"""
Sky 21 Bar & Restaurant Crawler
Source: skyconceptmacau.com (actual domain — sky21.com.mo redirects here)
Events page: /en/entertainment/upcoming-event/  — JS-rendered, Playwright required.
"""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class Sky21Crawler(BaseCrawler):
    name = "sky21.com.mo"
    base_url = "https://skyconceptmacau.com"
    rate_limit = 3.0
    priority = "medium"
    frequency = "weekly"
    languages = ["en"]

    # Known event list pages — stored in url_map, checked first
    SEED_URLS = [
        "https://skyconceptmacau.com/en/entertainment/upcoming-event/",
        "https://skyconceptmacau.com/en/sky21/",
    ]

    async def fetch_list_urls(self) -> List[str]:
        urls: set[str] = set()
        for seed in self.SEED_URLS:
            try:
                # JS-rendered — Playwright required
                html = await self.fetch_html_js(seed, wait_until="networkidle", timeout=30000)
                soup = self._soup(html)
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if any(k in href for k in ("/upcoming-event/", "/event/", "/events/", "/entertainment/")):
                        full = urljoin(self.base_url, href.split("?")[0].split("#")[0])
                        if full != seed and full.startswith(self.base_url):
                            urls.add(full)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")
        # Always include the listing page itself — events may be inline
        urls.update(self.SEED_URLS)
        return sorted(urls)

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)

        # Try JSON-LD first
        json_events = self._extract_json_ld(soup)
        if json_events:
            event = self._from_json_ld(json_events[0], url)
            return event if event.title and event.start_date else None

        return self._from_html(soup, url)

    def _from_json_ld(self, data: dict, url: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = "en"
        event.organizer = "SKY 21 Bar & Restaurant"
        event.organizer_type = "venue"
        event.venue_name = "SKY 21"
        event.venue_type = "rooftop bar"
        event.district = "Macau Peninsula"
        event.address = "21/F, AIA Tower, 251A-301 Avenida Comercial de Macau, Macao"
        event.coordinates = {"lat": 22.1983, "lng": 113.5439}

        event.title = data.get("name", "")
        event.description = data.get("description", "")

        if "startDate" in data:
            event.start_date = data["startDate"][:10]
            if "T" in data["startDate"]:
                event.start_time = data["startDate"][11:16]
        if "endDate" in data:
            event.end_date = data["endDate"][:10]

        img = data.get("image")
        if img:
            if isinstance(img, list):
                img = img[0]
            if isinstance(img, dict):
                img = img.get("url", "")
            if isinstance(img, str) and img:
                event.featured_image = img
                event.images = [{"url": img, "primary": True}]

        event.category = self._guess_category(event.title, event.description)
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.rstrip("/").split("/")[-1])
        event.tags = ["nightlife", "rooftop-bar", "sky21", "cotai"]
        return event

    def _from_html(self, soup: BeautifulSoup, url: str) -> Optional[CrawledEvent]:
        """Parse event cards from the listing page or a detail page."""
        # Try to find individual event cards first (listing page)
        cards = soup.select(".event-card, .event-item, .upcoming-event, article.event, .wp-block-post")
        if cards:
            # Return the first parseable card (fetch_all will call parse_event per URL)
            # If we're on the listing page, return None — individual URLs are what matter
            if "/upcoming-event/" in url or "/events/" in url:
                return None

        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = "en"
        event.organizer = "SKY 21 Bar & Restaurant"
        event.organizer_type = "venue"
        event.venue_name = "SKY 21"
        event.venue_type = "rooftop bar"
        event.district = "Macau Peninsula"
        event.address = "21/F, AIA Tower, 251A-301 Avenida Comercial de Macau, Macao"
        event.coordinates = {"lat": 22.1983, "lng": 113.5439}

        # Title
        for sel in ["h1", "h2.event-title", ".event-name", ".wp-post-title"]:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 3:
                event.title = el.get_text(strip=True)
                break

        if not event.title:
            return None

        # Date from visible text
        page_text = soup.get_text(" ", strip=True)
        event.start_date, event.end_date = self._extract_visible_date_range(page_text)
        if not event.start_date:
            event.start_date = self._parse_date(page_text)

        # Description
        for sel in [".event-description", ".content", ".entry-content", ".wp-block-group"]:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(" ", strip=True)[:3000]
                break

        # Image
        for meta in soup.find_all("meta", property="og:image"):
            src = meta.get("content", "")
            if src:
                event.featured_image = src
                event.images = [{"url": src, "primary": True}]
                break

        if not event.featured_image:
            img = self._extract_best_image(soup, url, event.title)
            if img:
                event.featured_image = img
                event.images = [{"url": img, "primary": True}]

        event.category = self._guess_category(event.title, event.description)
        event.ticket_type = "free"  # Most Sky 21 events are free entry
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.rstrip("/").split("/")[-1] or "sky21-main")
        event.tags = ["nightlife", "rooftop-bar", "sky21"]
        return event if event.title and event.start_date else None

    def _guess_category(self, title: str, description: str = "") -> str:
        combined = f"{title} {description}".lower()
        if any(k in combined for k in ["dj", "dance", "party", "club", "nightlife"]):
            return "nightlife"
        if any(k in combined for k in ["live music", "band", "concert", "jazz", "acoustic"]):
            return "music"
        if any(k in combined for k in ["brunch", "dinner", "food", "dining", "cocktail", "wine"]):
            return "dining"
        return "nightlife"
