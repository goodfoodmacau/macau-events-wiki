#!/usr/bin/env python3
"""
MGM China Crawler
Source: mgm.mo
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class MGMCrawler(BaseCrawler):
    name = "mgm.mo"
    base_url = "https://www.mgm.mo"
    rate_limit = 3.0
    priority = "medium"
    frequency = "daily"
    languages = ['en']
    
    async def fetch_list_urls(self) -> List[str]:
        urls = set()
        # Hardcode permanent attractions (they live at /en/entertainment/<slug>, not /en/entertainment/happening/<slug>)
        for attraction in ['spectacle', 'mgm-theater', 'fantasy-box', 'the-grande-praca']:
            urls.add(f"{self.base_url}/en/entertainment/{attraction}")
        for seed in [f"{self.base_url}/en/entertainment", f"{self.base_url}/en/best-deal"]:
            try:
                soup = self._soup(await self.fetch_html(seed))
                for link in soup.select('a[href*="/en/entertainment/happening/"], a[href*="/en/art/happening/"], a[href*="/en/best-deal/"]'):
                    full_url = urljoin(self.base_url, link.get('href', '')).split('?')[0]
                    if full_url.rstrip('/') != seed.rstrip('/'):
                        urls.add(full_url)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")
        return sorted(urls)
    
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
            event.venue_name = location.get('name', 'MGM Theater')
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
            event.organizer = organizer.get('name', 'MGM China')
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
        
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "MGM China"
        event.organizer_type = 'casino'

        
        # Detect property
        page_text = soup.get_text(' ', strip=True)
        page_lower = page_text.lower()
        if 'mgm cotai' in page_lower:
            event.organizer = "MGM Cotai"
            event.district = "Cotai"
            event.address = "Avenida da Nave Desportiva, Cotai, Macao"
        else:
            event.organizer = "MGM Macau"
            event.district = "Macau Peninsula"
            event.address = "Avenida Dr. Sun Yat Sen, NAPE, Macao"

        venue_patterns = [
            ('bar patuá', 'Bar Patuá'), ('grill 58', 'Grill 58'),
            ('location: coast', 'Coast'), ('imperial court', 'Imperial Court'),
            ('chatterbox café', 'Chatterbox Café'), ('hao guo', 'Hao Guo'),
            ('five foot road', 'Five Foot Road'), ('chún', 'Chún'),
        ]
        for needle, venue in venue_patterns:
            if needle in page_lower:
                event.venue_name = venue
                break
        if 'autumn-crab-delicacies' in url.lower():
            event.venue_name = "Participating restaurants at MGM Macau and MGM Cotai"
            event.address = "MGM Macau and MGM Cotai, Macao"
        if not event.venue_name:
            event.venue_name = "MGM Cotai" if event.district == "Cotai" else "MGM Macau"
        
        # Title
        for sel in ['h1', '.page-title', '.event-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        
        # Category
        if 'theater' in url.lower() or 'theatre' in url.lower():
            event.category = 'theater'
        elif 'spectacle' in url.lower():
            event.category = 'show'
            event.venue_name = "Spectacle"
        elif 'dining' in url.lower() or 'best-deal' in url.lower() or 'bar-' in url.lower():
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
        for sel in ['.description', '.event-description', '.content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        if not event.description:
            meta = soup.select_one('meta[name="description"], meta[property="og:description"]')
            if meta:
                event.description = meta.get('content', '').strip()[:5000]
        
        # Ticketing
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})
        
        for img in soup.select('.event-image img, [itemprop="image"]'):
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
        
        event.tags = ['casino-promoted', 'mgm-china']
        if event.membership_type:
            event.tags.append('membership-discount')
        
        return event