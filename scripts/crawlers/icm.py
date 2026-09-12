#!/usr/bin/env python3
"""
ICM (Cultural Affairs Bureau - 文化局) Crawler
Source: icm.gov.mo
"""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class ICMCrawler(BaseCrawler):
    name = "icm.gov.mo"
    base_url = "https://www.icm.gov.mo"
    rate_limit = 2.0
    priority = "high"
    frequency = "daily"
    languages = ['en', 'zh']
    
    # Category IDs from ICM site
    CATEGORY_URLS = {
        'en': {
            'performances': '/en/events/1,2,21,23,24,25,47',
            'exhibitions': '/en/events/3,4,14',
            'lectures': '/en/events/5,8,16,18,22,28,29,49',
            'arts_festival': '/en/events/13',
            'music_festival': '/en/events/12',
            'parade': '/en/events/76',
            'heritage_day': '/en/events/77',
            'fringe_festival': '/en/events/80',
        },
        'zh': {
            'performances': '/zh/events/1,2,21,23,24,25,47',
            'exhibitions': '/zh/events/3,4,14',
            'lectures': '/zh/events/5,8,16,18,22,28,29,49',
            'arts_festival': '/zh/events/13',
            'music_festival': '/zh/events/12',
            'parade': '/zh/events/76',
            'heritage_day': '/zh/events/77',
            'fringe_festival': '/zh/events/80',
        }
    }
    
    async def fetch_list_urls(self) -> List[str]:
        """Fetch event detail URLs from calendar and category pages"""
        urls = set()
        
        for lang in self.languages:
            # Calendar page - ICM uses FullCalendar with date cells linking to daily views
            # The daily view pages have event details in the right panel
            cal_url = f"{self.base_url}/{lang}/events/calendar"
            try:
                html = await self.fetch_html(cal_url)
                soup = self._soup(html)
                
                # Get all date cell links from the calendar
                for link in soup.select('a.dateSquer.canClick[href*="/events/calendar/"]'):
                    href = link.get('href', '')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        urls.add(full_url)
                        
                # Also check the right panel for today's events (has direct detail links)
                for link in soup.select('a[href*="/events/detail/"]'):
                    href = link.get('href', '')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        urls.add(full_url)
                        
            except Exception as e:
                self.logger.warning(f"Failed to fetch {lang} calendar: {e}")
            
            # Category pages (performances, exhibitions, lectures, festivals)
            for cat_name, cat_path in self.CATEGORY_URLS.get(lang, {}).items():
                cat_url = f"{self.base_url}{cat_path}"
                try:
                    html = await self.fetch_html(cat_url)
                    soup = self._soup(html)
                    
                    for link in soup.select('a[href*="/events/detail/"]'):
                        href = link.get('href', '')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {lang} {cat_name}: {e}")
        
        return list(urls)
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        # Try JSON-LD first
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
        
        # Performer
        performer = data.get('performer', {})
        if isinstance(performer, dict):
            event.headliners.append(performer.get('name', ''))
        elif isinstance(performer, list):
            for p in performer:
                if isinstance(p, dict):
                    event.headliners.append(p.get('name', ''))
        
        # Organizer
        organizer = data.get('organizer', {})
        if isinstance(organizer, dict):
            event.organizer = organizer.get('name', 'Cultural Affairs Bureau')
            event.organizer_url = organizer.get('url', '')
        event.organizer_zh = "澳門特別行政區政府文化局"
        event.organizer_type = 'cultural_institution'
        
        # Ticketing
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
        
        # Category from URL
        event.category = self._detect_category(url)
        
        # Generate IDs
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Cultural Affairs Bureau"
        event.organizer_zh = "澳門特別行政區政府文化局"
        event.organizer_type = 'cultural_institution'
        event.organizer_url = "https://www.icm.gov.mo"
        event.category = self._detect_category(url)
        
        # Title
        for sel in ['h1.event-title', 'h1.page-title', 'h1', '.event-detail h1', '.detail-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Dates - look in meta tags and structured elements
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
        
        # Time from page
        time_el = soup.select_one('[itemprop="startDate"], [itemprop="endDate"], .event-time, .time')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Venue
        venue_selectors = ['[itemprop="location"]', '.venue', '.event-venue', '.location', '.event-place']
        for sel in venue_selectors:
            el = soup.select_one(sel)
            if el:
                event.venue_name = el.get_text(strip=True)
                break
        
        # Address
        addr_el = soup.select_one('[itemprop="address"], .address, .event-address')
        if addr_el:
            event.address = addr_el.get_text(strip=True)
        
        # Description
        for sel in ['.event-description', '.description', '.synopsis', '.event-content', '[itemprop="description"]', 'article .content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        
        # Ticketing
        ticket_link = soup.select_one('a[href*="macaoticket"], a[href*="ticket"], .btn-ticket, .buy-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Price from text
        price_text = soup.get_text()
        prices = re.findall(r'MOP\s*([\d,]+)', price_text)
        if prices:
            price_vals = [float(p.replace(',', '')) for p in prices]
            event.ticket_price_min = min(price_vals)
            event.ticket_price_max = max(price_vals)
            event.ticket_currency = 'MOP'
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('article img, .event-image img, .detail-image img, [itemprop="image"]'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(self.base_url, src)
                if not any(i['url'] == full_url for i in event.images):
                    event.images.append({'url': full_url, 'primary': len(event.images) == 0})
        
        if event.images:
            event.featured_image = event.images[0]['url']
        
        # Generate IDs
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        # District
        event.district = self._detect_district(event.venue_name, event.address)
        
        return event
    
    def _detect_category(self, url: str) -> str:
        url_lower = url.lower()
        if any(x in url_lower for x in ['arts', 'festival', '藝術節']):
            return 'festival'
        elif any(x in url_lower for x in ['music', '音樂節', 'concert']):
            return 'concert'
        elif any(x in url_lower for x in ['parade', '巡遊', '幻彩']):
            return 'parade'
        elif any(x in url_lower for x in ['exhibition', '展覽', 'exhibitions']):
            return 'exhibition'
        elif any(x in url_lower for x in ['lecture', '講座', 'talk', '演講']):
            return 'talk'
        elif any(x in url_lower for x in ['fringe', '藝穗']):
            return 'festival'
        elif any(x in url_lower for x in ['heritage', '遺產']):
            return 'cultural'
        # Default based on category IDs in URL
        if any(x in url for x in ['1,2,21,23,24,25,47']):
            return 'theater'
        elif any(x in url for x in ['3,4,14']):
            return 'exhibition'
        elif any(x in url for x in ['5,8,16,18,22,28,29,49']):
            return 'talk'
        return 'cultural'
    
    def _detect_district(self, venue: str, address: str) -> str:
        text = (venue + ' ' + address).lower()
        if any(kw in text for kw in ['cotai', '路氹', 'galaxy', 'venetian', 'parisian', 'wynn palace', 'city of dreams', 'studio city']):
            return 'Cotai'
        elif any(kw in text for kw in ['taipa', '氹仔', 'cultural centre', '文化中心', 'jw marriott', 'ritz', 'banyan']):
            return 'Taipa'
        elif any(kw in text for kw in ['coloane', '路環']):
            return 'Coloane'
        elif any(kw in text for kw in ['peninsula', '半島', 'central', 'senado', 'rua de', 'avenida', 'nam van', 'tap seac', 'macao cultural centre', '藝術博物館', 'museum of art', '公共圖書館', 'library']):
            return 'Macau Peninsula'
        return 'Multiple'