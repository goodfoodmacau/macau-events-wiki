#!/usr/bin/env python3
"""
Sands China Crawler
Source: sandsresortsmacao.com (unified lifestyle portal for 7 properties)
"""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin, parse_qs, urlparse


class SandsCrawler(BaseCrawler):
    name = "sandsresortsmacao.com"
    base_url = "https://www.sandsresortsmacao.com"
    rate_limit = 3.0
    priority = "high"
    frequency = "daily"
    languages = ['en']
    
    PROPERTY_MAP = {
        'venetian': {'name': 'The Venetian Macao', 'venue': 'The Venetian Arena', 'district': 'Cotai', 'address': 'Estrada da Baía de N. Senhora da Esperança, Cotai, Macao'},
        'parisian': {'name': 'The Parisian Macao', 'venue': 'Parisian Theatre', 'district': 'Cotai', 'address': 'Estrada do Istmo, Lote 3, Cotai Strip, Macao'},
        'four-seasons': {'name': 'Four Seasons Hotel Macao', 'venue': 'Four Seasons Ballroom', 'district': 'Cotai'},
        'conrad': {'name': 'Conrad Macao', 'venue': 'Conrad Ballroom', 'district': 'Cotai'},
        'sheraton': {'name': 'Sheraton Grand Macao', 'venue': 'Sheraton Grand Ballroom', 'district': 'Cotai'},
        'st-regis': {'name': 'The St. Regis Macao', 'venue': 'St. Regis Ballroom', 'district': 'Cotai'},
        'holiday-inn': {'name': 'Holiday Inn Macao', 'venue': 'Meeting Rooms', 'district': 'Cotai'},
    }
    
    async def fetch_list_urls(self) -> List[str]:
        """Fetch official Sands and Venetian event detail URLs."""
        urls = set()
        # Permanent family/kids attractions
        urls.add("https://www.sandsresortsmacao.com/en/activities/family-fun.html")
        urls.add("https://www.venetianmacao.com/entertainment/canal-rides.html")

        seeds = [
            "https://en.sandsresortsmacao.com/sands-lifestyle/events-ent.html",
            "https://www.venetianmacao.com/entertainment.html",
            "https://www.parisianmacao.com/entertainment.html",
            "https://www.venetianmacao.com/promotions.html",
            "https://www.venetianmacao.com/restaurants.html",
            "https://www.parisianmacao.com/offers.html",
            "https://www.parisianmacao.com/restaurants.html",
        ]
        for seed in seeds:
            try:
                soup = self._soup(await self.fetch_html(seed))
                for link in soup.select('a[href*="/sands-lifestyle/events-ent/"], a[href*="/entertainment/"], a[href*="/offers/"]'):
                    full_url = urljoin(seed, link.get('href', '')).split('?')[0]
                    slug = full_url.rstrip('/').split('/')[-1].lower()
                    is_dated_hospitality = any(term in slug for term in (
                        'chef-series', 'mooncake', 'brunch', 'dinner', 'tasting', 'wine', 'cocktail'
                    ))
                    if (full_url.endswith('.html') and
                            not full_url.endswith('/entertainment.html') and
                            'sands-golf-day.html' not in full_url and
                            ('/offers/' not in full_url or is_dated_hospitality)):
                        urls.add(full_url)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")
        return sorted(urls)

    async def fetch_html(self, url: str) -> str:
        """Decode legacy Sands pages without dropping otherwise valid events."""
        async with await self._rate_limited_request('GET', url) as resp:
            resp.raise_for_status()
            return await resp.text(errors='replace')
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)
        
        # Try JSON-LD
        json_events = self._extract_json_ld(soup)
        if json_events:
            event = self._from_json_ld(json_events[0], url, lang)
        else:
            property_key = self._detect_property(url)
            event = self._from_html(soup, url, lang, property_key)
        
        if event.start_date and not event.end_date:
            event.end_date = event.start_date
        # Permanent attractions with no date — open year-round
        if not event.start_date and event.title and any(k in url.lower() for k in ('family-fun', 'canal-ride', 'kids', 'family', 'activities')):
            from datetime import date
            event.start_date = date.today().isoformat()
            event.end_date = "2027-12-31"
            event.recurring = True
            event.category = 'family'
            if isinstance(event.tags, list):
                event.tags += ['family', 'kids', 'permanent-attraction']
            else:
                event.tags = ['family', 'kids', 'permanent-attraction']
        return event if event.title and event.start_date else None
    
    def _detect_property(self, url: str) -> Optional[str]:
        url_lower = url.lower()
        for key in self.PROPERTY_MAP:
            if key in url_lower:
                return key
        # Check for property in page content
        return None
    
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
            event.organizer = organizer.get('name', 'Sands China Limited')
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
        
        # Detect property
        prop_key = self._detect_property(url)
        if prop_key and prop_key in self.PROPERTY_MAP:
            prop = self.PROPERTY_MAP[prop_key]
            event.organizer = prop['name']
            event.district = prop['district']
            event.address = prop.get('address', event.address)
            if not event.venue_name:
                event.venue_name = prop['venue']
        
        event.category = self._detect_category(url, event.title)
        
        source_id = url.split('/')[-1].split('?')[0]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        # Sands Rewards
        if 'sands rewards' in event.description.lower() or 'sands rewards' in html.lower():
            event.membership_type = 'sands_rewards'
            event.membership_details = 'Sands Rewards members enjoy exclusive benefits and priority booking'
        
        return event
    
    def _from_html(self, soup: BeautifulSoup, url: str, lang: str, property_key: Optional[str]) -> CrawledEvent:
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Sands China Limited"
        event.organizer_type = 'casino'
        
        # Property-specific info
        if property_key and property_key in self.PROPERTY_MAP:
            prop = self.PROPERTY_MAP[property_key]
            event.organizer = prop['name']
            event.district = prop['district']
            event.venue_name = prop['venue']
            event.address = prop.get('address', '')
        else:
            event.district = 'Cotai'
        
        # Title
        for sel in ['h1', '.event-title', '.page-title', '.event-detail h1']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break
        if not event.title:
            meta_title = soup.select_one('meta[property="og:title"]')
            event.title = (meta_title.get('content', '') if meta_title else '').strip()
        if not event.title and soup.title:
            event.title = soup.title.get_text(' ', strip=True).split(' | ')[0].strip()

        page_text = soup.get_text(' ', strip=True)
        if property_key == 'venetian' and 'The Venetian Arena' in page_text:
            event.venue_name = 'The Venetian Arena'
        
        # Category
        event.category = self._detect_category(url, event.title)
        
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
            event.start_date, event.end_date = self._extract_visible_date_range(page_text)
        if 'chef-series-2026' in url:
            # This official series page lists six individually dated weekends.
            # Treat the page as one culinary series spanning its first through
            # final scheduled service rather than guessing dates from prose.
            ranges = re.findall(
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
                r'(\d{1,2})(?:\s*(?:-|–|—)\s*(\d{1,2}))?,?\s+(20\d{2})',
                page_text, re.IGNORECASE
            )
            parsed = []
            for month, first, last, year in ranges:
                start = self._parse_date(f'{month} {first}, {year}')
                end = self._parse_date(f'{month} {last or first}, {year}')
                if start and end:
                    parsed.extend((start, end))
            if parsed:
                event.start_date, event.end_date = min(parsed), max(parsed)
            event.venue_name = 'Le Cristal Parisian'
            event.venue_type = 'restaurant'
            event.category = 'dining'
        elif 'mooncake-2026' in url:
            # The source states a common redemption period and names all three
            # participating resort locations explicitly.
            event.venue_name = 'The Londoner Macao, The Venetian Macao and The Parisian Macao'
            event.address = 'Cotai Strip, Macao'
            event.district = 'Cotai'
            event.venue_type = 'hotel'
            event.category = 'dining'
            event.organizer = 'Sands China Limited'
        
        # Time
        time_el = soup.select_one('.event-time, .show-time, [itemprop="startDate"], .time')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
        
        # Venue (if not set from property)
        if not event.venue_name:
            for sel in ['.venue', '.event-venue', '[itemprop="location"]', '.location']:
                el = soup.select_one(sel)
                if el:
                    event.venue_name = el.get_text(strip=True)
                    break
        
        # Description
        for sel in ['.event-description', '.description', '.event-detail .content', '.detail-content', 'article']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break
        if not event.description:
            meta = soup.select_one('meta[name="description"], meta[property="og:description"]')
            if meta:
                event.description = meta.get('content', '').strip()[:5000]
        
        # Ticketing
        ticket_link = soup.select_one('a[href*="ticket"], a[href*="macaoticket"], .btn-ticket, .buy-ticket')
        if ticket_link:
            event.ticket_url = urljoin(self.base_url, ticket_link.get('href', ''))
            event.ticket_required = True
        
        # Price
        price_text = soup.get_text()
        prices = re.findall(r'MOP\s*([\d,]+)', price_text)
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
        
        for img in soup.select('.event-image img, .gallery img, [itemprop="image"]'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(self.base_url, src)
                if not any(i['url'] == full_url for i in event.images):
                    event.images.append({'url': full_url, 'primary': len(event.images) == 0})
        
        if event.images:
            event.featured_image = event.images[0]['url']
        
        # Sands Rewards
        page_text = soup.get_text().lower()
        if 'sands rewards' in page_text:
            event.membership_type = 'sands_rewards'
            event.membership_details = 'Sands Rewards members enjoy exclusive benefits and priority booking'
        
        # Generate IDs
        source_id = url.split('/')[-1].split('?')[0]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)
        
        # Tags
        event.tags = ['casino-promoted', 'sands-resorts']
        if property_key:
            event.tags.append(property_key.replace('-', '-'))
        if event.membership_type:
            event.tags.append('membership-discount')
        
        return event
    
    def _detect_category(self, url: str, title: str) -> str:
        text = (url + ' ' + title).lower()
        if any(kw in text for kw in ['car show', 'mice', 'convention', 'exhibition', 'trade show', 'expo', 'business']):
            return 'business'
        elif any(kw in text for kw in ['concert', 'music', 'live', 'world tour']):
            return 'concert'
        elif any(kw in text for kw in ['theater', 'theatre', 'musical', 'broadway', 'cirque']):
            return 'theater'
        elif any(kw in text for kw in ['dining', 'chef', 'wine', 'dinner', 'tasting', 'gastronomic']):
            return 'dining'
        elif any(kw in text for kw in ['festival', 'celebration', 'cny', 'chinese new year', 'christmas']):
            return 'festival'
        return 'entertainment'