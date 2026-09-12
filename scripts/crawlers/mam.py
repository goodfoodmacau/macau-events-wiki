#!/usr/bin/env python3
"""
Macao Museum of Art (MAM) Crawler
Source: mam.gov.mo
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class MAMCrawler(BaseCrawler):
    name = "mam.gov.mo"
    base_url = "https://www.mam.gov.mo"
    rate_limit = 3.0
    priority = "high"
    frequency = "daily"
    languages = ['en', 'zh-cn']
    
    # MAM has different sections
    SECTION_URLS = {
        'en': {
            'current': '/en/exhibitions/',
            'upcoming': '/en/exhibitions/preview',
            'past': '/en/exhibitions/review',
            'offsite': '/en/list/27/',
            'programs': '/en/eventList/56',
            'friends': '/en/eventList/32',
        },
        'zh-cn': {
            'current': '/cn/exhibitions/',
            'upcoming': '/cn/exhibitions/preview',
            'past': '/cn/exhibitions/review',
            'offsite': '/cn/list/27/',
            'programs': '/cn/eventList/56',
            'friends': '/cn/eventList/32',
        }
    }
    
    async def fetch_list_urls(self) -> List[str]:
        """Fetch event detail URLs from exhibition pages"""
        urls = set()
        
        for lang in self.languages:
            sections = self.SECTION_URLS.get(lang, self.SECTION_URLS['en'])
            
            for section_name, section_path in sections.items():
                section_url = f"{self.base_url}{section_path}"
                try:
                    html = await self.fetch_html(section_url)
                    soup = self._soup(html)
                    
                    # Exhibition detail links are /en/exhibition/{id} (not /exhibitions/)
                    for link in soup.select('a[href*="/exhibition/"]'):
                        href = link.get('href', '')
                        if href and not href.endswith('/exhibitions/') and not href.endswith('/preview') and not href.endswith('/review'):
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                            
                    # Also check for event list pages
                    for link in soup.select('a[href*="/eventList/"]'):
                        href = link.get('href', '')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                            
                    # Check for detail links in list pages
                    for link in soup.select('a[href*="/list/"]'):
                        href = link.get('href', '')
                        if href and '/detail/' in href:
                            full_url = urljoin(self.base_url, href)
                            urls.add(full_url)
                            
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {lang} {section_name}: {e}")
        
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
            event.venue_name = location.get('name', 'Macao Museum of Art')
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
            event.organizer = organizer.get('name', 'Macao Museum of Art')
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
        
        # Category
        if '/eventList/' in url or 'program' in url.lower():
            event.category = 'workshop'
        else:
            event.category = 'exhibition'
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Macao Museum of Art"
        event.organizer_zh = "澳門藝術博物館"
        event.organizer_type = 'cultural_institution'
        event.organizer_url = "https://www.mam.gov.mo"
        event.venue_name = "Macao Museum of Art"
        event.address = "Avenida Xian Xing Hai, NAPE, Macau"
        event.address_zh = "澳門新口岸冼星海大馬路"
        event.district = "Macau Peninsula"
        event.coordinates = {'lat': 22.1888601, 'lng': 113.5545978}
        
        # Title
        for sel in ['h1', '.page-title', '.exhibition-title', '.event-title', '.detail-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Category from URL
        if '/eventList/' in url:
            event.category = 'workshop'
            event.tags = ['public-program', 'museum-event']
        elif '/list/' in url and '/detail/' in url:
            event.category = 'workshop'
            event.tags = ['special-event']
        else:
            event.category = 'exhibition'
            event.tags = ['museum-exhibition']
        
        # Check for Friends events
        if 'friends' in url.lower() or '藝博館之友' in soup.get_text():
            event.tags.append('members-only')
            event.membership_required = True
            event.membership_type = 'museum_friends'
            event.membership_details = 'Friends of MAM members only'
        
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
        
        # Page content dates
        page_text = soup.get_text()
        date_values = self._extract_dates_from_text(page_text)
        if date_values and not event.start_date:
            event.start_date = date_values[0]
            event.end_date = date_values[-1]

        # Time
        time_el = soup.select_one('.event-time, .time, [itemprop="startDate"], .activity-time')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Description
        for sel in ['.description', '.exhibition-description', '.event-description', '.synopsis', '.content', '.detail-content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        
        # Curator
        curator_match = re.search(r'[Cc]urator[:\s]+([^\n]+)', page_text)
        if curator_match:
            event.curators.append(curator_match.group(1).strip())
        
        # Artists
        artist_match = re.search(r'[Aa]rtist[:\s]+([^\n]+)', page_text)
        if artist_match:
            event.artists.append(artist_match.group(1).strip())
        
        # Ticketing - MAM events often free but some require registration
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="register"], .btn-ticket, .register-btn')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Check if free
        if 'free' in page_text.lower() or '免費' in page_text:
            event.ticket_type = 'free'
            event.ticket_price_min = 0
            event.ticket_price_max = 0
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('.exhibition-image img, .event-image img, .gallery img, [itemprop="image"]'):
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
        
        event.tags = ['cultural-institution', 'museum', 'government-venue']
        if event.membership_type:
            event.tags.append('membership-required')
        
        return event