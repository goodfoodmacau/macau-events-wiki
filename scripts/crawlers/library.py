#!/usr/bin/env python3
"""
Macao Public Library Crawler
Source: library.gov.mo
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class LibraryCrawler(BaseCrawler):
    name = "library.gov.mo"
    base_url = "https://www.library.gov.mo"
    rate_limit = 3.0
    priority = "medium"
    frequency = "weekly"
    languages = ['en', 'zh-hant']
    
    VENUES = {
        'Central-library': {'name': 'Macao Central Library', 'address': 'Tap Seac Square, Macao', 'district': 'Macau Peninsula'},
        'Senado-library': {'name': 'Senado Library', 'address': 'Senado Square, Macao', 'district': 'Macau Peninsula'},
        'HoTung': {'name': 'Sir Robert Ho Tung Library', 'address': 'Rua de Sao Francisco, Macao', 'district': 'Macau Peninsula'},
        'MongHa': {'name': 'Mong Ha Library', 'address': 'Mong Ha, Macao', 'district': 'Macau Peninsula'},
        'Ilha-Verde': {'name': 'Ilha Verde Library', 'address': 'Ilha Verde, Macao', 'district': 'Macau Peninsula'},
        'Bairro': {'name': 'Bairro Library', 'address': 'Bairro, Macao', 'district': 'Macau Peninsula'},
    }
    
    async def fetch_list_urls(self) -> List[str]:
        urls = set()
        
        for lang in self.languages:
            # Main promotion events page
            events_url = f"{self.base_url}/{lang}/promotion-events"
            try:
                html = await self.fetch_html(events_url)
                soup = self._soup(html)
                
                # Venue links
                for link in soup.select('a[href*="/venues/"]'):
                    href = link.get('href', '')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        urls.add(full_url)
                
                # Event detail links
                for link in soup.select('a[href*="/detail/"]'):
                    href = link.get('href', '')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        urls.add(full_url)
                        
            except Exception as e:
                self.logger.warning(f"Failed to fetch {lang} events: {e}")
            
            # Individual venue pages
            for venue_key in self.VENUES:
                venue_url = f"{self.base_url}/{lang}/promotion-events/venues/{venue_key}"
                try:
                    html = await self.fetch_html(venue_url)
                    soup = self._soup(html)
                    
                    for link in soup.select('a[href*="/detail/"]'):
                        href = link.get('href', '')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                except Exception:
                    pass
        
        return list(urls)
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        json_events = self._extract_json_ld(soup)
        if json_events:
            return self._from_json_ld(json_events[0], url, lang)
        
        return self._from_html(soup, url, lang)
    
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
            event.venue_name = location.get('name', 'Macao Public Library')
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
            event.organizer = organizer.get('name', 'Macao Public Library')
        event.organizer_type = 'cultural_institution'
        
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
        
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        event.category = 'workshop'
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Macao Public Library"
        event.organizer_zh = "澳門公共圖書館"
        event.organizer_type = 'cultural_institution'
        event.organizer_url = "https://www.library.gov.mo"
        event.category = 'workshop'
        event.ticket_type = 'free'
        event.ticket_price_min = 0
        event.ticket_price_max = 0
        event.ticket_required = False
        
        # Detect venue from URL
        venue_key = None
        for key in self.VENUES:
            if key.lower() in url.lower():
                venue_key = key
                break
        
        if venue_key and venue_key in self.VENUES:
            venue = self.VENUES[venue_key]
            event.venue_name = venue['name']
            event.address = venue['address']
            event.district = venue['district']
        else:
            event.venue_name = "Macao Public Library"
            event.address = "Macao"
            event.district = "Macau Peninsula"
        
        # Title
        for sel in ['h1', '.page-title', '.event-title', '.activity-title', '.detail-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
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
        
        page_text = soup.get_text()
        date_matches = re.findall(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', page_text)
        if date_matches and not event.start_date:
            day, month, year = date_matches[0]
            event.start_date = f"{year}-{int(month):02d}-{int(day):02d}"
            event.end_date = event.start_date
        
        # Time
        time_el = soup.select_one('.event-time, .time, [itemprop="startDate"], .activity-time')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Description
        for sel in ['.description', '.event-description', '.activity-description', '.content', '.detail-content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        
        # Target audience / age restriction
        if 'children' in page_text.lower() or '兒童' in page_text or '親子' in page_text:
            event.tags.append('children')
            event.age_restriction = 'all-ages'
        elif 'youth' in page_text.lower() or '青少年' in page_text:
            event.tags.append('youth')
            event.age_restriction = '12+'
        elif 'senior' in page_text.lower() or '長者' in page_text:
            event.tags.append('senior')
            event.age_restriction = 'all-ages'
        
        # Tags
        event.tags = ['public-library', 'government-venue', 'free', 'community']
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('.event-image img, .activity-image img, [itemprop="image"]'):
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
        
        return event