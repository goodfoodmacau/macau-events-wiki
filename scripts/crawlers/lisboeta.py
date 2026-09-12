#!/usr/bin/env python3
"""
Lisboeta Macau Crawler
Source: lisboetamacau.com

Uses the WordPress REST API for both URL discovery and data extraction,
since all page content is JavaScript-rendered and not available via plain HTTP.

Anti-bot hardening:
  - Rotated Accept-Language + User-Agent headers on API calls
  - Jitter between endpoint fetches
  - Retry with exponential back-off on 429 / 5xx responses
"""

import asyncio
import json
import random
import re
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class LisboetaCrawler(BaseCrawler):
    name = "lisboetamacau.com"
    base_url = "https://www.lisboetamacau.com"
    rate_limit = 2.0
    priority = "medium"
    frequency = "daily"
    languages = ['en']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_cache: Dict[str, dict] = {}

    def _api_headers(self) -> dict:
        """Rotate UA + set realistic browser headers for WP REST API calls."""
        return {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.9,zh;q=0.8"]),
            "Referer": self.base_url + "/",
        }

    async def _fetch_api_with_retry(self, endpoint: str, retries: int = 3) -> list:
        """Fetch a WP REST API endpoint with exponential back-off on rate-limit errors."""
        for attempt in range(retries):
            try:
                async with self.session.get(
                    endpoint,
                    headers=self._api_headers(),
                    timeout=30,
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 429 or resp.status >= 500:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(
                            f"Lisboeta API {resp.status} on {endpoint}; retrying in {wait:.1f}s"
                        )
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    return data if isinstance(data, list) else []
            except asyncio.TimeoutError:
                self.logger.warning(f"Lisboeta API timeout on {endpoint} (attempt {attempt+1})")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                self.logger.warning(f"Lisboeta API error on {endpoint}: {e}")
                break
        return []

    async def fetch_list_urls(self) -> List[str]:
        self._api_cache = {}
        urls = set()
        api_endpoints = [
            f"{self.base_url}/wp-json/wp/v2/promotions?per_page=100&lang=en",
            f"{self.base_url}/wp-json/wp/v2/entertainment?per_page=100&lang=en",
            f"{self.base_url}/wp-json/wp/v2/art-exhibitions?per_page=100&lang=en",
            f"{self.base_url}/wp-json/wp/v2/dining?per_page=100&lang=en",
        ]
        for endpoint in api_endpoints:
            try:
                items = await self._fetch_api_with_retry(endpoint)
                for item in items:
                    link = item.get("link", "").rstrip("/")
                    if link and "lisboetamacau.com" in link:
                        urls.add(link)
                        self._api_cache[link] = item
            except Exception as e:
                self.logger.warning(f"Failed to fetch API {endpoint}: {e}")
            # Jitter between endpoints to avoid triggering Cloudflare rate-limits
            await asyncio.sleep(random.uniform(1.0, 2.5))
        return sorted(urls)

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        url_key = url.rstrip("/")
        if url_key in self._api_cache:
            event = self._from_api(self._api_cache[url_key], url)
        else:
            soup = self._soup(html)
            lang = self._detect_language(url)
            json_events = self._extract_json_ld(soup)
            if json_events:
                event = self._from_json_ld(json_events[0], url, lang)
            else:
                event = self._from_html(soup, url, lang)

        if event.start_date and not event.end_date:
            event.end_date = event.start_date

        return event if event.title and event.start_date else None

    def _from_api(self, data: dict, url: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = 'en'
        event.organizer = "Lisboeta Macau"
        event.organizer_type = 'casino'
        event.venue_name = "Lisboeta Macau"
        event.district = "Cotai"
        event.address = "Avenida de Lisboa, Cotai, Macao"

        title_obj = data.get('title', {})
        raw_title = title_obj.get('rendered', '') if isinstance(title_obj, dict) else str(title_obj)
        event.title = BeautifulSoup(raw_title, 'html.parser').get_text(strip=True)

        content_obj = data.get('content', {})
        excerpt_obj = data.get('excerpt', {})
        content_html = content_obj.get('rendered', '') if isinstance(content_obj, dict) else ''
        excerpt_html = excerpt_obj.get('rendered', '') if isinstance(excerpt_obj, dict) else ''
        if content_html:
            event.description = BeautifulSoup(content_html, 'html.parser').get_text(' ', strip=True)[:5000]
        elif excerpt_html:
            event.description = BeautifulSoup(excerpt_html, 'html.parser').get_text(' ', strip=True)[:2000]

        acf = data.get('acf', {}) or {}
        start_raw = acf.get('start_date') or acf.get('event_start_date') or acf.get('date_from') or ''
        end_raw = acf.get('end_date') or acf.get('event_end_date') or acf.get('date_to') or ''
        if start_raw:
            event.start_date = self._parse_date(str(start_raw))
        if end_raw:
            event.end_date = self._parse_date(str(end_raw))

        if not event.start_date and event.description:
            sd, ed = self._extract_visible_date_range(event.description)
            event.start_date = sd
            event.end_date = ed or sd

        if not event.start_date:
            modified = data.get('date', '') or data.get('modified', '')
            if modified:
                parsed = self._parse_date(modified[:10])
                if parsed:
                    event.start_date = parsed

        embedded = data.get('_embedded', {})
        featured = embedded.get('wp:featuredmedia', [])
        for media in featured:
            if isinstance(media, dict):
                src = media.get('source_url', '') or media.get('guid', {}).get('rendered', '')
                if src:
                    event.images.append({'url': src, 'primary': len(event.images) == 0})

        for key in ('banner', 'image', 'thumbnail', 'cover'):
            img = acf.get(key)
            if isinstance(img, dict):
                src = img.get('url') or img.get('sizes', {}).get('large', '')
                if src:
                    event.images.append({'url': src, 'primary': len(event.images) == 0})
            elif isinstance(img, str) and img.startswith('http'):
                event.images.append({'url': img, 'primary': len(event.images) == 0})

        if event.images:
            event.featured_image = event.images[0]['url']

        event.category = self._guess_category(url)
        event.ticket_url = url
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.rstrip('/').split('/')[-1])
        event.tags = ['casino-promoted', 'lisboeta-macau']
        return event

    def _guess_category(self, url: str) -> str:
        u = url.lower()
        if 'show' in u or 'theatre' in u or 'theater' in u or 'concert' in u or 'music' in u:
            return 'concert'
        if 'dine' in u or 'dining' in u or 'restaurant' in u or 'brunch' in u or 'tea' in u:
            return 'dining'
        if 'enjoy' in u or 'entertainment' in u or 'spa' in u or 'pool' in u or 'golf' in u:
            return 'entertainment'
        return 'promotion'

    def _from_json_ld(self, data: dict, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Lisboeta Macau"
        event.organizer_type = 'casino'
        event.venue_name = "Lisboeta Macau"
        event.district = "Cotai"
        event.address = "Avenida de Lisboa, Cotai, Macao"
        event.title = data.get('name', '')
        event.description = data.get('description', '')
        if 'startDate' in data:
            event.start_date = data['startDate'][:10]
            if 'T' in data['startDate']:
                event.start_time = data['startDate'][11:16]
        if 'endDate' in data:
            event.end_date = data['endDate'][:10]
            if 'T' in data['endDate']:
                event.end_time = data['endDate'][11:16]
        if 'image' in data:
            images = data['image'] if isinstance(data['image'], list) else [data['image']]
            for img in images:
                if isinstance(img, str):
                    event.images.append({'url': img, 'primary': len(event.images) == 0})
                elif isinstance(img, dict) and 'url' in img:
                    event.images.append({'url': img['url'], 'primary': len(event.images) == 0})
            if event.images:
                event.featured_image = event.images[0]['url']
        event.category = self._guess_category(url)
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.rstrip('/').split('/')[-1])
        return event

    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Lisboeta Macau"
        event.organizer_type = 'casino'
        event.venue_name = "Lisboeta Macau"
        event.district = "Cotai"
        event.address = "Avenida de Lisboa, Cotai, Macao"
        for sel in ['h1', '.promotion-title', '.event-title', '.page-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        event.category = self._guess_category(url)
        for meta in soup.find_all('meta', property=re.compile(r'og:|article:|event:')):
            prop = meta.get('property', '')
            content = meta.get('content', '')
            if 'start' in prop or 'date' in prop:
                parsed = self._parse_date(content)
                if parsed and not event.start_date:
                    event.start_date = parsed
            if 'end' in prop:
                parsed = self._parse_date(content)
                if parsed and not event.end_date:
                    event.end_date = parsed
        if not event.start_date:
            event.start_date, event.end_date = self._extract_visible_date_range(soup.get_text(' ', strip=True))
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        if event.images:
            event.featured_image = event.images[0]['url']
        event.ticket_url = url
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.rstrip('/').split('/')[-1])
        event.tags = ['casino-promoted', 'lisboeta-macau']
        return event
