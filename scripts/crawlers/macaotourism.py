#!/usr/bin/env python3
"""
MGTO (Macao Government Tourism Office) Crawler
Source: macaotourism.gov.mo
"""

import re
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent


class MGTOCrawler(BaseCrawler):
    name = "macaotourism.gov.mo"
    base_url = "https://www.macaotourism.gov.mo"
    rate_limit = 2.0
    priority = "high"
    frequency = "daily"
    languages = ['en', 'zh-hant', 'pt', 'th', 'id']
    
    async def fetch_list_urls(self) -> List[str]:
        """Fetch event detail URLs from calendar pages for all languages"""
        urls = []
        
        for lang in self.languages:
            cal_url = f"{self.base_url}/{lang}/events/calendar"
            try:
                html = await self.fetch_html(cal_url)
                soup = self._soup(html)
                
                # Find all event detail links - m-calendar__item ARE the <a> tags
                for link in soup.select('a.m-calendar__item[href*="/events/calendar/"]'):
                    href = link.get('href', '')
                    if href and not href.endswith('/calendar') and not href.endswith('/events/calendar'):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)
                                
            except Exception as e:
                self.logger.warning(f"Failed to fetch {lang} calendar: {e}")
        
        return urls
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        # Try JSON-LD first
        json_events = self._extract_json_ld(soup)
        if json_events:
            return self._from_json_ld(json_events[0], url, lang)
        
        # Fallback to HTML parsing
        return self._from_html(soup, url, lang)
    
    def _from_json_ld(self, data: dict, url: str, lang: str) -> CrawledEvent:
        """Parse from JSON-LD structured data"""
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        
        # Basic info
        event.title = data.get('name', '')
        event.description = data.get('description', '')
        
        # Dates
        if 'startDate' in data:
            event.start_date = data['startDate'][:10]
            if 'T' in data['startDate']:
                event.start_time = data['startDate'][11:16]
        if 'endDate' in data:
            event.end_date = data['endDate'][:10]
            if 'T' in data['endDate']:
                event.end_time = data['endDate'][11:16]
        
        # Venue
        location = data.get('location', {})
        if isinstance(location, dict):
            event.venue_name = location.get('name', '')
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
        
        # Organizer
        organizer = data.get('organizer', {})
        if isinstance(organizer, dict):
            event.organizer = organizer.get('name', '')
            event.organizer_url = organizer.get('url', '')
        event.organizer_type = 'government'
        
        # Ticketing
        offers = data.get('offers', [])
        if not isinstance(offers, list):
            offers = [offers]
        for offer in offers:
            if isinstance(offer, dict):
                price = offer.get('price', '0')
                event.ticket_price_min = min(event.ticket_price_min or float('inf'), float(price))
                event.ticket_price_max = max(event.ticket_price_max, float(price))
                event.ticket_currency = offer.get('priceCurrency', 'MOP')
                event.ticket_url = offer.get('url', '')
                event.ticket_required = float(price) > 0
        
        # Images
        if 'image' in data:
            images = data['image'] if isinstance(data['image'], list) else [data['image']]
            for img in images:
                if isinstance(img, str):
                    event.images.append({'url': img, 'primary': len(event.images) == 0})
                elif isinstance(img, dict) and 'url' in img:
                    event.images.append({'url': img['url'], 'primary': len(event.images) == 0})
            if event.images:
                event.featured_image = event.images[0]['url']
        
        # Generate IDs
        source_id = url.split('/')[-1] or 'unknown'
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        event.category = 'festival'  # MGTO primarily festivals
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        """Parse from HTML when JSON-LD not available"""
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Macao Government Tourism Office"
        event.organizer_zh = "澳門特別行政區政府旅遊局"
        event.organizer_type = 'government'
        event.organizer_url = "https://www.macaotourism.gov.mo"
        event.category = 'festival'
        
        # Title
        title_selectors = ['h1.event-title', 'h1.page-title', 'h1', '.event-detail h1', 'article h1']
        for sel in title_selectors:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Extract dates from page text
        page_text = soup.get_text()
        date_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', page_text)
        if date_match:
            day, month, year = date_match.groups()
            event.start_date = f"{year}-{int(month):02d}-{int(day):02d}"
            event.end_date = event.start_date
        
        # Try to find date in meta tags
        for meta in soup.find_all('meta', property=re.compile(r'og:|article:')):
            prop = meta.get('property', '')
            if 'date' in prop or 'time' in prop:
                content = meta.get('content', '')
                parsed = self._parse_date(content)
                if parsed and not event.start_date:
                    event.start_date = parsed
                    event.end_date = parsed
        
        # Venue
        venue_selectors = ['.event-venue', '.venue', '[itemprop="location"]', '.location']
        for sel in venue_selectors:
            el = soup.select_one(sel)
            if el:
                event.venue_name = el.get_text(strip=True)
                break
        
        # Description
        desc_selectors = ['.event-description', '.description', 'article .content', '.detail-content', 'main article']
        for sel in desc_selectors:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        
        # Images - Open Graph and article images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('article img, .event-image img, .detail-image img'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(self.base_url, src)
                if not any(i['url'] == full_url for i in event.images):
                    event.images.append({'url': full_url, 'primary': len(event.images) == 0})
        
        if event.images:
            event.featured_image = event.images[0]['url']
        
        # Ticket URL
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Generate IDs
        source_id = url.split('/')[-1] or 'unknown'
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        # District detection
        event.district = self._detect_district(event.venue_name, event.address)
        
        return event
    
    def _detect_district(self, venue: str, address: str) -> str:
        text = (venue + ' ' + address).lower()
        if any(kw in text for kw in ['cotai', '路氹', 'galaxy', 'venetian', 'parisian', 'wynn palace', 'city of dreams', 'studio city', 'morpheus', 'nüwa']):
            return 'Cotai'
        elif any(kw in text for kw in ['taipa', '氹仔', 'jw marriott', 'ritz', 'banyan', 'okura', 'rakku']):
            return 'Taipa'
        elif any(kw in text for kw in ['coloane', '路環', 'hac sa', 'hengqin']):
            return 'Coloane'
        elif any(kw in text for kw in ['peninsula', '半島', 'central', 'senado', 'rua de', 'avenida', 'nam van', 'tap seac']):
            return 'Macau Peninsula'
        return 'Multiple'