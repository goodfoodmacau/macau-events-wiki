#!/usr/bin/env python3
"""
Galaxy Entertainment Crawler
Source: galaxymacau.com (ticketing page is goldmine)
"""

import re
import json
from typing import List, Optional
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawledEvent
from urllib.parse import urljoin


class GalaxyCrawler(BaseCrawler):
    name = "galaxymacau.com"
    base_url = "https://www.galaxymacau.com"
    rate_limit = 3.0
    priority = "high"
    frequency = "daily"
    languages = ['en']

    async def fetch_list_urls(self) -> List[str]:
        """Fetch dated entertainment and dining offer detail URLs."""
        urls = set()
        # Hardcoded permanent family/kids attractions
        urls.add(f"{self.base_url}/landing/galaxy-kidz/")
        urls.add(f"{self.base_url}/grand-resort-deck/")
        urls.add(f"{self.base_url}/immersive-new-experience/")

        seeds = [
            f"{self.base_url}/ticketing/event-list/",
            # Permanent family/kids attractions
            f"{self.base_url}/landing/galaxy-kidz/",
            f"{self.base_url}/entertainment/",
            f"{self.base_url}/offers/entertainment/",
            f"{self.base_url}/dining/exclusive-gastronomic-events/",
            f"{self.base_url}/offers/dining/",
        ]
        for seed in seeds:
            try:
                soup = self._soup(await self.fetch_html(seed))
                for link in soup.select('a[href*="/offers/entertainment/"], a[href*="/offers/dining/"]'):
                    full_url = urljoin(self.base_url, link.get('href', '')).split('?')[0]
                    path = full_url.rstrip('/')
                    if path.endswith('/offers/entertainment') or path.endswith('/offers/dining'):
                        continue
                    urls.add(full_url)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {seed}: {e}")

        return sorted(urls)

    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        lang = self._detect_language(url)

        # Try JSON-LD first (very complete on ticketing pages)
        json_events = self._extract_json_ld(soup)
        if json_events:
            event = self._from_json_ld(json_events[0], url, lang)
            if event.start_date and not event.end_date:
                event.end_date = event.start_date
            return event if event.title and event.start_date else None

        # Check if it's a ticketing page
        if '/ticketing/event-list/' in url:
            return self._from_ticketing_page(soup, url, lang)

        event = self._from_html(soup, url, lang)
        # Permanent attractions with no date — open year-round
        if not event.start_date and event.title and any(k in url.lower() for k in ('galaxy-kidz', 'kidz', 'kids', 'family', 'grand-resort-deck', 'water-park')):
            from datetime import date
            event.start_date = date.today().isoformat()
            event.end_date = "2027-12-31"
            event.recurring = True
            event.category = 'family'
            if not event.tags:
                event.tags = []
            event.tags += ['family', 'kids', 'permanent-attraction']
        return event if event.title and event.start_date else None

    def _from_json_ld(self, data: dict, url: str, lang: str) -> CrawledEvent:
        """Parse from JSON-LD - Galaxy ticketing pages have excellent structured data"""
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

        # Venue - Galaxy Arena typically
        location = data.get('location', {})
        if isinstance(location, dict):
            event.venue_name = location.get('name', 'Galaxy Arena')
            event.venue_id = 'venue-galaxy-arena'
            event.venue_type = 'arena'
            event.venue_capacity = location.get('maximumAttendeeCapacity', 16000)
            addr = location.get('address', {})
            if isinstance(addr, dict):
                event.address = ', '.join(filter(None, [
                    addr.get('streetAddress', ''),
                    addr.get('addressLocality', ''),
                    addr.get('addressRegion', ''),
                    addr.get('addressCountry', '')
                ]))
                # Extract district from address
                event.district = self._detect_district(event.venue_name, event.address)
            else:
                event.address = str(addr)
                event.district = 'Cotai'

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
            event.organizer = organizer.get('name', 'Galaxy Entertainment Group')
            event.organizer_url = organizer.get('url', '')
        event.organizer_zh = "銀河娛樂集團"
        event.organizer_type = 'casino'

        # Ticketing - multiple offers with tiers
        offers = data.get('offers', [])
        if not isinstance(offers, list):
            offers = [offers]

        ticket_tiers = []
        for offer in offers:
            if isinstance(offer, dict):
                tier_name = offer.get('name', 'Standard')
                price = offer.get('price', '0')
                try:
                    p = float(price)
                    event.ticket_price_min = min(event.ticket_price_min or float('inf'), p)
                    event.ticket_price_max = max(event.ticket_price_max, p)
                except ValueError:
                    pass
                event.ticket_currency = offer.get('priceCurrency', 'MOP')
                event.ticket_url = offer.get('url', event.ticket_url or '')
                event.ticket_required = True
                ticket_tiers.append(f"{tier_name}: MOP {price}")

        if ticket_tiers:
            event.ticket_info = '; '.join(ticket_tiers)

        # Membership benefits
        if 'galaxy club' in event.description.lower() or 'galaxy club' in str(offers).lower():
            event.membership_required = False
            event.membership_type = 'galaxy_club'
            event.membership_details = 'Galaxy Club members enjoy 10% discount and priority booking'

        # Images - ticketing pages have multiple images including seat maps
        if 'image' in data:
            images = data['image'] if isinstance(data['image'], list) else [data['image']]
            for img in images:
                if isinstance(img, str):
                    event.images.append({'url': img, 'primary': len(event.images) == 0, 'type': 'poster'})
                elif isinstance(img, dict) and 'url' in img:
                    img_type = 'seatmap' if 'seat' in img['url'].lower() or 'map' in img['url'].lower() else 'poster'
                    event.images.append({'url': img['url'], 'primary': len(event.images) == 0, 'type': img_type})
            if event.images:
                event.featured_image = event.images[0]['url']

        # Category
        event.category = 'concert'  # Galaxy Arena primarily concerts

        # Generate IDs
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)

        # Tags
        event.tags = ['arena', 'ticketed', 'casino-promoted']
        if event.ticket_price_max > 2000:
            event.tags.append('vip-available')
        if event.membership_type:
            event.tags.append('membership-discount')

        return event

    def _from_ticketing_page(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        """Parse Galaxy ticketing detail page"""
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Galaxy Entertainment Group"
        event.organizer_zh = "銀河娛樂集團"
        event.organizer_type = 'casino'
        event.organizer_url = "https://www.galaxyentertainment.com"
        event.category = 'concert'
        event.venue_name = "Galaxy Arena"
        event.venue_id = 'venue-galaxy-arena'
        event.venue_type = 'arena'
        event.venue_capacity = 16000
        event.address = "Galaxy Macau, Avenida da Nobreza de Carvalho, Cotai, Macao"
        event.address_zh = "澳門路氹城嘉樂路銀河澳門"
        event.district = 'Cotai'
        event.coordinates = {'lat': 22.1406, 'lng': 113.5651}

        # Title
        for sel in ['h1.event-title', 'h1', '.event-detail h1', '.ticketing-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break

        # Dates from page
        for meta in soup.find_all('meta', property=re.compile(r'og:|event:')):
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

        # Time
        time_el = soup.select_one('.event-time, .show-time, [itemprop="startDate"]')
        if time_el:
            text = time_el.get_text(strip=True)
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            if time_match:
                event.start_time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

        # Price tiers - look for price elements
        price_elements = soup.select('.price-tier, .ticket-price, .price, [data-price]')
        prices = []
        for el in price_elements:
            text = el.get_text(strip=True)
            price = self._parse_price(text)
            if price:
                prices.append(price)

        # Also check for JSON data in script tags
        for script in soup.find_all('script'):
            if script.string and 'price' in script.string.lower():
                json_prices = re.findall(r'["\']price["\']\s*:\s*["\']?([\d,]+)', script.string)
                for p in json_prices:
                    try:
                        prices.append(float(p.replace(',', '')))
                    except ValueError:
                        pass

        if prices:
            event.ticket_price_min = min(prices)
            event.ticket_price_max = max(prices)
            event.ticket_currency = 'MOP'
            event.ticket_required = True
            event.ticket_info = f"Price tiers: MOP {min(prices):,.0f} - {max(prices):,.0f}"

        # Ticket URL
        buy_btn = soup.select_one('a[href*="buy"], a[href*="ticket"], .btn-buy, .buy-ticket')
        if buy_btn:
            event.ticket_url = urljoin(self.base_url, buy_btn.get('href', ''))

        # Description
        for sel in ['.event-description', '.description', '.event-detail .content', '.detail-content']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break

        # Images - look for poster and seat map
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                img_type = 'seatmap' if 'seat' in img_url.lower() or 'map' in img_url.lower() else 'poster'
                event.images.append({'url': img_url, 'primary': len(event.images) == 0, 'type': img_type})

        for img in soup.select('.event-image img, .seat-map img, .gallery img, [itemprop="image"]'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(self.base_url, src)
                if not any(i['url'] == full_url for i in event.images):
                    img_type = 'seatmap' if 'seat' in src.lower() or 'map' in src.lower() else 'poster'
                    event.images.append({'url': full_url, 'primary': len(event.images) == 0, 'type': img_type})

        if event.images:
            event.featured_image = event.images[0]['url']

        # Membership
        if 'galaxy club' in soup.get_text().lower():
            event.membership_type = 'galaxy_club'
            event.membership_details = 'Galaxy Club members enjoy 10% discount and priority booking'

        # Generate IDs
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)

        # Tags
        event.tags = ['arena', 'ticketed', 'casino-promoted', 'galaxy-arena']
        if event.ticket_price_max > 2000:
            event.tags.append('vip-available')
        if event.membership_type:
            event.tags.append('membership-discount')

        return event

    def _from_html(self, soup: BeautifulSoup, url: str, lang: str) -> CrawledEvent:
        """Parse non-ticketing entertainment pages"""
        event = CrawledEvent()
        event.source = self.name
        event.source_url = url
        event.source_language = lang
        event.organizer = "Galaxy Entertainment Group"
        event.organizer_zh = "銀河娛樂集團"
        event.organizer_type = 'casino'

        # Title
        for sel in ['h1', '.page-title', '.event-title']:
            el = soup.select_one(sel)
            if el:
                event.title = el.get_text(strip=True)
                break

        # Determine category from URL
        if 'diamond' in url.lower() or 'crystal' in url.lower():
            event.category = 'show'
            event.venue_name = 'Galaxy Macau Lobby'
            event.ticket_required = False
            event.ticket_type = 'free'
            event.tags = ['free', 'lobby-show', 'daily']
        elif 'dining' in url.lower() or 'gastronomic' in url.lower():
            event.category = 'dining'
            event.tags = ['dining', 'chef-collab']
        else:
            event.category = 'entertainment'

        # Description
        for sel in ['.description', '.content', '.event-description']:
            el = soup.select_one(sel)
            if el:
                event.description = el.get_text(strip=True)[:5000]
                break

        # Dining offer pages often publish the date in visible copy rather than JSON-LD.
        page_text = soup.get_text(' ', strip=True)
        event.start_date, event.end_date = self._extract_visible_date_range(page_text)

        # Images
        for meta in soup.find_all('meta', property='og:image'):
            img_url = meta.get('content', '')
            if img_url:
                event.images.append({'url': img_url, 'primary': len(event.images) == 0})

        if event.images:
            event.featured_image = event.images[0]['url']

        # Generate IDs
        source_id = url.split('/')[-1]
        event.id = self._make_id(event.title, event.start_date)
        event.guid = self._make_guid(source_id)

        return event