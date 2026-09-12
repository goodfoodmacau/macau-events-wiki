#!/usr/bin/env python3
"""
The Londoner Macao Crawler
Source: londonermacao.com

Anti-bot hardening:
  - Randomised User-Agent from a pool of real browser UAs
  - Randomised viewport dimensions
  - Cookie-consent banner dismissed before scraping
  - Randomised delay between page loads
"""

import random
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin

# ---------------------------------------------------------------------------
# User-Agent pool — realistic desktop browser strings
# ---------------------------------------------------------------------------
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Realistic viewport sizes
_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800},
    {"width": 2560, "height": 1440},
]

# CSS selectors for cookie-consent accept buttons (tried in order)
_CONSENT_SELECTORS = [
    "#onetrust-accept-btn-handler",
    ".onetrust-accept-btn-handler",
    "[data-testid='cookie-accept']",
    "button[aria-label*='Accept']",
    "button[aria-label*='accept']",
    ".cookie-accept",
    ".accept-cookies",
    "#accept-cookies",
    "button:contains('Accept All')",
    "button:contains('Accept Cookies')",
    "button:contains('I Accept')",
]


class LondonerCrawler(BaseCrawler):
    name = "londonermacao.com"
    base_url = "https://www.londonermacao.com"
    rate_limit = 3.0
    priority = "medium"
    frequency = "daily"
    languages = ['en']

    def _random_ua(self) -> str:
        return random.choice(_USER_AGENTS)

    def _random_viewport(self) -> dict:
        return random.choice(_VIEWPORTS)

    async def _fetch_with_consent(self, url: str) -> str:
        """
        Fetch a page via Playwright with:
         - randomised UA + viewport
         - cookie-consent banner dismissal
         - extra wait for network idle
        Falls back to fetch_html_smart if Playwright fails.
        """
        try:
            from playwright.async_api import async_playwright
            global _pw_browser, _pw_instance
            from crawlers.base import _pw_browser, _pw_instance

            if _pw_browser is None:
                raise RuntimeError("Playwright browser not available — will use smart fetch")

            ua = self._random_ua()
            viewport = self._random_viewport()

            context = await _pw_browser.new_context(
                user_agent=ua,
                viewport=viewport,
                locale="en-US",
                timezone_id="Asia/Macau",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Try to dismiss cookie/consent overlays
            for sel in _CONSENT_SELECTORS:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=800):
                        await btn.click()
                        break
                except Exception:
                    continue

            # Wait for network to settle after possible consent interaction
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            html = await page.content()
            await context.close()
            return html
        except Exception as e:
            self.logger.debug(f"Playwright consent fetch failed for {url}: {e}, using smart fetch")
            return await self.fetch_html_smart(url)

    async def fetch_list_urls(self) -> List[str]:
        import asyncio
        urls = set()
        seeds = [
            f"{self.base_url}/macau-events-shows.html",
            f"{self.base_url}/offers.html",
        ]
        shows_pattern = re.compile(r'/macau-events-shows/[^?\s#]+\.html')

        for seed in seeds:
            try:
                html = await self._fetch_with_consent(seed)
                soup = self._soup(html)
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if shows_pattern.search(href):
                        full = urljoin(self.base_url, href.split('?')[0])
                        urls.add(full)
                # Also look in script tags for dynamically built links
                for script in soup.find_all('script'):
                    text = script.string or ''
                    for m in shows_pattern.finditer(text):
                        full = urljoin(self.base_url, m.group(0))
                        urls.add(full)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")
            # Jitter between seed requests to avoid triggering rate-limits
            await asyncio.sleep(random.uniform(1.5, 3.5))

        return sorted(urls)

    async def fetch_all(self):
        """
        Override fetch_all to use _fetch_with_consent (UA rotation + cookie dismissal)
        for each event detail page, instead of the base class's fetch_html_smart.
        """
        import asyncio
        from ai_enrichment import enrich_event
        from datetime import datetime

        events = []
        urls = await self.fetch_list_urls()
        self.events_found = len(urls)
        self.logger.info(f"Found {len(urls)} event URLs to process")

        for url in urls:
            try:
                html = await self._fetch_with_consent(url)
                event = await self.parse_event(url, html)
                if event:
                    event = await enrich_event(event, html, self.session)
                    await self.verify_event(event, html)
                    event.last_crawled = datetime.utcnow().isoformat() + 'Z'
                    event.crawl_hash = event.compute_hash()
                    event.status = event.compute_status()
                    event.data_quality = event.compute_data_quality()
                    events.append(event)
                    self.events_parsed += 1
                # Randomised jitter between event pages
                await asyncio.sleep(random.uniform(2.0, 5.0))
            except Exception as e:
                self.errors.append(f"{url}: {e}")
                self.logger.warning(f"Failed to parse {url}: {e}")

        self.logger.info(f"Successfully parsed {self.events_parsed}/{self.events_found} events")
        return events

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
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

    def _from_json_ld(self, data: dict, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "The Londoner Macao"
        event.organizer_type = 'casino'

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

        location = data.get('location', {})
        if isinstance(location, dict):
            event.venue_name = location.get('name', 'The Londoner Macao')
            event.venue_type = 'casino'
            addr = location.get('address', {})
            if isinstance(addr, dict):
                event.address = ', '.join(filter(None, [
                    addr.get('streetAddress', ''),
                    addr.get('addressLocality', ''),
                    addr.get('addressRegion', ''),
                    addr.get('addressCountry', ''),
                ]))
            else:
                event.address = str(addr)
        else:
            event.venue_name = "The Londoner Macao"
            event.address = "Estrada do Istmo, Cotai, Macao"

        event.district = "Cotai"

        offers = data.get('offers', [])
        if not isinstance(offers, list):
            offers = [offers]
        for offer in offers:
            if isinstance(offer, dict):
                price = offer.get('price', '0')
                try:
                    p = float(price)
                    event.ticket_price_min = min(event.ticket_price_min or float('inf'), p)
                    event.ticket_price_max = max(event.ticket_price_max, p)
                except (ValueError, TypeError):
                    pass
                event.ticket_currency = offer.get('priceCurrency', 'MOP')
                event.ticket_url = offer.get('url', url)
                event.ticket_required = True

        if 'image' in data:
            images = data['image'] if isinstance(data['image'], list) else [data['image']]
            for img in images:
                if isinstance(img, str):
                    event.images.append({'url': img, 'primary': len(event.images) == 0})
                elif isinstance(img, dict) and 'url' in img:
                    event.images.append({'url': img['url'], 'primary': len(event.images) == 0})
            if event.images:
                event.featured_image = event.images[0]['url']

        if 'paiza' in url.lower():
            event.venue_name = "The Paiza Grand"
            event.membership_type = 'paiza'
        else:
            event.venue_name = "The Londoner Grand"

        event.category = 'theater' if 'show' in url.lower() or 'theater' in url.lower() else 'entertainment'
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.split('/')[-1].replace('.html', ''))

        return event

    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "The Londoner Macao"
        event.organizer_type = 'casino'
        event.district = "Cotai"
        event.address = "Estrada do Istmo, Cotai, Macao"

        if 'paiza' in url.lower():
            event.venue_name = "The Paiza Grand"
            event.membership_type = 'paiza'
        else:
            event.venue_name = "The Londoner Grand"

        # Title
        for sel in ['h1', '.event-title', '.offer-title', '.page-title', '.hero-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break

        # Category
        if 'show' in url.lower() or 'theatre' in url.lower() or 'theater' in url.lower():
            event.category = 'theater'
        elif 'concert' in url.lower() or 'music' in url.lower():
            event.category = 'concert'
        elif 'dine' in url.lower() or 'dining' in url.lower() or 'restaurant' in url.lower():
            event.category = 'dining'
        else:
            event.category = 'entertainment'

        # Dates from meta
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

        # Time
        time_el = soup.select_one('.event-time, .show-time, .time, [itemprop="startDate"]')
        if time_el:
            text = time_el.get_text(strip=True)
            m = re.search(r'(\d{1,2}):(\d{2})', text)
            if m:
                event.start_time = f"{int(m.group(1)):02d}:{m.group(2)}"

        # Description
        for sel in ['.event-description', '.offer-description', '.description', '.content', '.body-copy']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(' ', strip=True)[:5000]
                break

        # Ticket link
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-book, .btn-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        else:
            event.ticket_url = url

        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})

        for img in soup.select('.event-image img, .offer-image img, .hero img, [itemprop="image"]'):
            src = img.get('src') or img.get('data-src', '')
            if src:
                full = urljoin(self.base_url, src)
                if not any(i['url'] == full for i in event.images):
                    event.images.append({'url': full, 'primary': len(event.images) == 0})

        if event.images:
            event.featured_image = event.images[0]['url']

        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(url.split('/')[-1].replace('.html', ''))
        event.tags = ['casino-promoted', 'londoner-macao']
        if event.membership_type:
            event.tags.append('paiza-member')

        return event
