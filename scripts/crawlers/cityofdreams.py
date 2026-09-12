#!/usr/bin/env python3
"""
City of Dreams / Studio City Crawler (Melco Resorts)
Source: cityofdreamsmacau.com, studiocitymacau.com
"""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class CityOfDreamsCrawler(BaseCrawler):
    name = "cityofdreamsmacau.com"
    base_url = "https://www.cityofdreamsmacau.com"
    rate_limit = 3.0
    priority = "medium"
    frequency = "daily"
    languages = ['en']
    
    # Also crawl Studio City
    studio_city_url = "https://www.studiocity-macau.com"
    
    async def fetch_list_urls(self) -> List[str]:
        urls = set()
        # Permanent family/kids attractions — always included
        urls.add(f"{self.base_url}/en/attractions/kids-city")
        # Permanent entertainment attractions at COD
        for attraction in ['house-of-dancing-water', 'para-club', 'art-of-the-city']:
            urls.add(f"{self.base_url}/en/entertainment/{attraction}")
        dining_terms = ('chef', 'dining', 'dinner', 'feast', 'whisky', 'wine', 'french-flair', 'all-you-can-eat')
        for base in [self.base_url, self.studio_city_url]:
            for section in ('events', 'offers', 'entertainment'):
                seed = f"{base}/en/{section}"
                try:
                    soup = self._soup(await self.fetch_html(seed))
                    for link in soup.select(f'a[href*="/en/{section}/"]'):
                        full_url = urljoin(base, link.get('href', '')).split('?')[0]
                        slug = full_url.rstrip('/').split('/')[-1].lower()
                        if section in ('events', 'entertainment') or any(term in slug for term in dining_terms):
                            urls.add(full_url)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {seed}: {e}")
        return sorted(urls)
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        json_events = self._extract_json_ld(soup)
        is_studio_city = 'studiocity' in url
        event = self._from_json_ld(json_events[0], url, lang) if json_events else self._from_html(soup, url, lang, is_studio_city)
        if event.start_date and not event.end_date:
            event.end_date = event.start_date
        # Permanent attractions (no date scraped) — open year-round
        if not event.start_date and event.title and any(k in url.lower() for k in ('kids-city', 'attractions', 'house-of-dancing')):
            from datetime import date
            event.start_date = date.today().isoformat()
            event.end_date = "2027-12-31"
            event.recurring = True
        return event if event.title and event.start_date else None

    def _melco_page_text(self, soup: BeautifulSoup) -> str:
        """Include metadata because Melco keeps event dates in descriptions."""
        parts = [soup.get_text(' ', strip=True)]
        for meta in soup.select('meta[name="description"], meta[property="og:description"]'):
            parts.append(meta.get('content', ''))
        return ' '.join(parts)

    def _extract_melco_dates(self, soup: BeautifulSoup, title: str):
        text = self._melco_page_text(soup)
        start, end = self._extract_visible_date_range(text)
        if start:
            return start, end
        year_match = re.search(r'\b(20\d{2})\b', title or '')
        label_match = re.search(
            r'(?:concert|event|show)\s+date(?:\s+and\s+time)?\s*:',
            text, re.IGNORECASE
        )
        if not year_match or not label_match:
            return None, None
        segment = text[label_match.end():label_match.end() + 300]
        tokens = re.findall(
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})',
            segment, re.IGNORECASE
        )
        dates = [self._extract_visible_date_range(f"{month} {day}, {year_match.group(1)}")[0] for month, day in tokens]
        dates = [date for date in dates if date]
        return (dates[0], dates[-1]) if dates else (None, None)
    
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
        
        organizer = data.get('organizer', {})
        if isinstance(organizer, dict):
            event.organizer = organizer.get('name', 'Melco Resorts')
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
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str, is_studio_city: bool) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Melco Resorts"
        event.organizer_type = 'casino'
        
        if is_studio_city:
            event.organizer = "Studio City"
            event.district = "Cotai"
        else:
            event.district = "Cotai"
        
        # Title
        for sel in ['h1', '.page-title', '.event-title', '.show-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        if not event.title:
            meta_title = soup.select_one('meta[property="og:title"]')
            event.title = (meta_title.get('content', '') if meta_title else '').strip()
        if not event.title and soup.title:
            event.title = soup.title.get_text(' ', strip=True)
        
        # Category
        if 'house-of-dancing-water' in url.lower() or 'dancing water' in soup.get_text().lower():
            event.category = 'theater'
            event.venue_name = "Dancing Water Theater"
            event.tags = ['permanent-show', 'water-show', 'daily']
        elif 'shows' in url.lower():
            event.category = 'theater'
        elif 'kids-city' in url.lower() or 'kids' in url.lower() or 'family' in url.lower() or 'children' in url.lower():
            event.category = 'family'
            event.venue_name = event.venue_name or "Kids City"
            event.tags = ['family', 'kids', 'indoor-playground', 'permanent-attraction']
        elif 'nightlife' in url.lower() or 'club' in url.lower():
            event.category = 'nightlife'
            event.venue_name = event.venue_name or "Club Cubic"
        elif 'concert' in url.lower():
            event.category = 'concert'
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
            event.start_date, event.end_date = self._extract_melco_dates(soup, event.title)
        
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
        
        # Ticketing
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-ticket, .buy-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Melco Club
        if 'melco club' in soup.get_text().lower():
            event.membership_type = 'melco_club'
            event.membership_details = 'Melco Club members enjoy exclusive benefits'
        
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
        
        event.tags = ['casino-promoted', 'melco-resorts']
        if is_studio_city:
            event.tags.append('studio-city')
        else:
            event.tags.append('city-of-dreams')
        if event.membership_type:
            event.tags.append('membership-discount')
        
        return event