#!/usr/bin/env python3
"""
Wynn Macau Crawler
Source: wynnresortsmacau.com
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class WynnCrawler(BaseCrawler):
    name = "wynnresortsmacau.com"
    base_url = "https://www.wynnresortsmacau.com"
    rate_limit = 3.0
    priority = "medium"
    frequency = "daily"
    languages = ['en']
    
    # Disable SSL verification for this domain (known cert issues)
    ssl_verify = False
    
    async def fetch_list_urls(self) -> List[str]:
        urls = set()
        dining_terms = ('chef', 'dining', 'sake', 'wine', 'culinary', 'gourmet', 'brunch', 'dinner', 'buns-bubbles')
        seeds = [
            f"{self.base_url}/en/wynn-palace/offers",
            f"{self.base_url}/en/wynn-macau/offers",
        ]
        for seed in seeds:
            try:
                soup = self._soup(await self.fetch_html(seed))
                for link in soup.select('a[href*="/offers/"]'):
                    full_url = urljoin(seed, link.get('href', '')).split('?')[0]
                    slug = full_url.rstrip('/').split('/')[-1].lower()
                    if any(term in slug for term in dining_terms):
                        urls.add(full_url)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")
        return sorted(urls)
    
    async def fetch_html(self, url: str) -> str:
        """Override to disable SSL verification"""
        async with await self._rate_limited_request('GET', url, ssl=not self.ssl_verify) as resp:
            resp.raise_for_status()
            return await resp.text()
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        json_events = self._extract_json_ld(soup)
        event = self._from_json_ld(json_events[0], url, lang) if json_events else self._from_html(soup, url, lang)
        if event.start_date and not event.end_date:
            event.end_date = event.start_date
        return event if event.title and event.start_date else None
    
    def _from_json_ld(self, data: dict, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        
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
            event.venue_name = location.get('name', 'Wynn Theater')
            event.venue_type = 'theater'
            addr = location.get('address', {})
            if isinstance(addr, dict):
                event.address = ', '.join(filter(None, [
                    addr.get('streetAddress', ''),
                    addr.get('addressLocality', ''),
                    addr.get('addressRegion', ''),
                    addr.get('addressCountry', '')
                ]))
            else:
                event.address = str(addr)
        
        organizer = data.get('organizer', {})
        if isinstance(organizer, dict):
            event.organizer = organizer.get('name', 'Wynn Macau')
        event.organizer_type = 'casino'
        
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
                except ValueError:
                    pass
                event.ticket_currency = offer.get('priceCurrency', 'MOP')
                event.ticket_url = offer.get('url', '')
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
        
        event.category = 'theater' if 'theater' in url.lower() else 'entertainment'
        
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Wynn Macau"
        event.organizer_type = 'casino'

        
        # Determine property and venue
        if 'palace' in url.lower() or 'wynn palace' in soup.get_text().lower():
            event.organizer = "Wynn Palace"
            event.venue_name = "Mizumi" if 'mizumi' in url.lower() else "Wynn Palace"
            event.district = "Cotai"
            event.address = "Avenida da Nave Desportiva, Cotai, Macao"
        else:
            event.venue_name = "Wynn Macau"
            event.district = "Macau Peninsula"
            event.address = "Rua Cidade de Sintra, NAPE, Macao"
        
        # Title
        for sel in ['h1', '.page-title', '.event-title', '.show-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Category
        if 'theater' in url.lower() or 'theatre' in url.lower():
            event.category = 'theater'
        elif 'concert' in url.lower() or 'music' in url.lower():
            event.category = 'concert'
        elif 'dining' in url.lower():
            event.category = 'dining'
        else:
            event.category = 'entertainment'
        
        # Dates
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
        time_el = soup.select_one('.show-time, .event-time, .time, [itemprop="startDate"]')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Description
        for sel in ['.description', '.event-description', '.show-description', '.content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        if not event.description:
            content = soup.select_one('.about-content')
            if content:
                event.description = content.get_text(' ', strip=True)[:5000]
        
        # Ticketing
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-ticket, .buy-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True

        if 'wynn rewards' in soup.get_text(' ', strip=True).lower():
            event.membership_type = 'wynn_rewards'
            event.membership_details = 'Wynn Rewards benefits are described on the source page'
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('.event-image img, .show-image img, [itemprop="image"]'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(self.base_url, src)
                if not any(i['url'] == full_url for i in event.images):
                    event.images.append({'url': full_url, 'primary': len(event.images) == 0})
        
        if event.images:
            event.featured_image = event.images[0]['url']
        
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        event.tags = ['casino-promoted', 'wynn-resorts']
        if event.membership_type:
            event.tags.append('membership-discount')
        
        return event