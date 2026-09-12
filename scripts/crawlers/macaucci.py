#!/usr/bin/env python3
"""
Macao Cultural Centre (CCM) Crawler
Source: macaucci.gov.mo
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class CCMCrawler(BaseCrawler):
    name = "macaucci.gov.mo"
    base_url = "https://www.macaucci.gov.mo"
    rate_limit = 3.0
    priority = "high"
    frequency = "daily"
    languages = ['en', 'zh']
    
    async def fetch_list_urls(self) -> List[str]:
        """Fetch event detail URLs from list pages for each category"""
        urls = set()
        
        # CCM uses /en/list/{category} pages for event listings
        CATEGORY_LISTS = {
            'en': ['14', '15', '16', '17', '18', '19', '19', '20', '1,2,21,23,24,25,47'],
            'zh': ['14', '15', '16', '17', '18', '19', '19', '20', '1,2,21,23,24,25,47'],
        }
        
        for lang in self.languages:
            for cat_id in CATEGORY_LISTS.get(lang, []):
                list_url = f"{self.base_url}/{lang}/list/{cat_id}"
                try:
                    html = await self.fetch_html(list_url)
                    soup = self._soup(html)
                    
                    # Find all detail links
                    for link in soup.select('a[href*="/detail/"]'):
                        href = link.get('href', '')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {lang} list/{cat_id}: {e}")
        
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
            parsed_start = self._parse_date(data['startDate'])
            if parsed_start:
                event.start_date = parsed_start
            if 'T' in data['startDate']:
                event.start_time = data['startDate'][11:16]
        if 'endDate' in data:
            parsed_end = self._parse_date(data['endDate'])
            if parsed_end:
                event.end_date = parsed_end
            if 'T' in data['endDate']:
                event.end_time = data['endDate'][11:16]
        
        location = data.get('location', {})
        if isinstance(location, dict):
            event.venue_name = location.get('name', 'Macao Cultural Centre')
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
            event.organizer = organizer.get('name', 'Macao Cultural Centre')
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
        
        # Category detection
        if any(kw in event.title.lower() for kw in ['concert', 'music', 'orchestra', 'symphony', 'piano', 'violin']):
            event.category = 'concert'
        elif any(kw in event.title.lower() for kw in ['dance', 'ballet', '舞蹈']):
            event.category = 'dance'
        elif any(kw in event.title.lower() for kw in ['opera', '歌劇']):
            event.category = 'opera'
        elif any(kw in event.title.lower() for kw in ['theater', 'theatre', 'drama', 'musical', '戲劇', '音樂劇']):
            event.category = 'theater'
        else:
            event.category = 'theater'
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Macao Cultural Centre"
        event.organizer_zh = "澳門文化中心"
        event.organizer_type = 'cultural_institution'
        event.organizer_url = "https://www.macaucci.gov.mo"
        event.venue_name = "Macao Cultural Centre"
        event.address = "Xian Xing Hai Avenue, Macao"
        event.address_zh = "澳門宋玉生廣場"
        event.district = "Macau Peninsula"
        event.coordinates = {'lat': 22.1917, 'lng': 113.5521}
        
        # Title
        for sel in ['h1', '.page-title', '.event-title', '.program-title', '.detail-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Category from venue/title
        title_lower = event.title.lower()
        if any(kw in title_lower for kw in ['concert', 'music', 'orchestra', 'symphony', 'piano', 'violin', '音樂', '演奏']):
            event.category = 'concert'
        elif any(kw in title_lower for kw in ['dance', 'ballet', '舞蹈']):
            event.category = 'dance'
        elif any(kw in title_lower for kw in ['opera', '歌劇']):
            event.category = 'opera'
        elif any(kw in title_lower for kw in ['theater', 'theatre', 'drama', 'musical', '戲劇', '音樂劇']):
            event.category = 'theater'
        else:
            event.category = 'theater'
        
        # Dates - look in meta and structured elements
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
        
        # Also check for date in page content
        page_text = soup.get_text()
        date_values = self._extract_dates_from_text(page_text)
        if date_values and not event.start_date:
            event.start_date = date_values[0]
            event.end_date = date_values[-1]

        # Time
        time_el = soup.select_one('.event-time, .show-time, .time, [itemprop="startDate"], .performance-time')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Venue detail (which auditorium)
        for sel in ['.venue', '.auditorium', '.location', '.event-venue', '[itemprop="location"]']:
            el = soup.select_one(sel)
            if el:
                venue_text = el.get_text(strip=True)
                if 'grand' in venue_text.lower() or '大劇院' in venue_text:
                    event.venue_name = "Macao Cultural Centre - Grand Auditorium"
                elif 'small' in venue_text.lower() or '小劇院' in venue_text:
                    event.venue_name = "Macao Cultural Centre - Small Auditorium"
                break
        
        # Description
        for sel in ['.description', '.event-description', '.synopsis', '.program-description', '.content', '.detail-content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        
        # Ticketing - CCM uses macauticket.com
        ticket_link = soup.select_one('a[href*="macaoticket"], a[href*="ticket"], .btn-ticket, .buy-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Price
        prices = re.findall(r'MOP\s*([\d,]+)', page_text)
        if prices:
            price_vals = [float(p.replace(',', '')) for p in prices]
            event.ticket_price_min = min(price_vals)
            event.ticket_price_max = max(price_vals)
            event.ticket_currency = 'MOP'
            event.ticket_required = True
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('.event-image img, .program-image img, [itemprop="image"]'):
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
        
        event.tags = ['cultural-institution', 'government-venue']
        
        return event