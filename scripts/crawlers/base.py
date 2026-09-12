#!/usr/bin/env python3
"""
Base Crawler Class
All source-specific crawlers inherit from this.
"""

import asyncio
import aiohttp
import hashlib
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional Playwright browser — lazily initialised the first time JS rendering
# is requested so that crawlers that never need it pay no startup cost.
# ---------------------------------------------------------------------------
_pw_instance = None   # playwright async context manager
_pw_browser  = None   # shared Browser object (reused across calls in one run)


@dataclass
class CrawledEvent:
    """Standardized event structure for all crawlers"""
    # Required identifiers
    id: str = ""
    guid: str = ""
    source: str = ""
    source_url: str = ""
    source_language: str = "en"
    supported_languages: List[str] = field(default_factory=lambda: [
        "en", "zh-hant-yue", "zh-cn", "pt", "ko", "th",
        "de", "it", "es", "sq", "vi", "id"
    ])
    
    # Core event info
    title: str = ""
    title_zh: Optional[str] = None
    title_pt: Optional[str] = None
    title_alternatives: List[str] = field(default_factory=list)
    translations: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Dates & Times
    start_date: str = ""
    end_date: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timezone: str = "Asia/Macau"
    recurring: bool = False
    recurrence_rule: Optional[str] = None
    recurrence_exceptions: List[str] = field(default_factory=list)
    
    # Venue
    venue_name: str = ""
    venue_name_zh: Optional[str] = None
    venue_name_pt: Optional[str] = None
    address: str = ""
    address_zh: Optional[str] = None
    address_pt: Optional[str] = None
    district: str = ""
    coordinates: Optional[Dict[str, float]] = None
    venue_type: str = ""
    venue_id: str = ""
    venue_capacity: Optional[int] = None
    
    # Organizer & Promoter
    organizer: str = ""
    organizer_zh: Optional[str] = None
    organizer_pt: Optional[str] = None
    organizer_type: str = ""
    organizer_url: Optional[str] = None
    promoter: Optional[str] = None
    promoter_zh: Optional[str] = None
    promoter_type: Optional[str] = None
    promoter_contact: Dict = field(default_factory=dict)
    
    # Categorization
    category: str = ""
    subcategory: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    age_restriction: str = "all-ages"
    dress_code: str = "casual"
    
    # Ticketing
    ticket_required: bool = False
    ticket_price_min: float = 0
    ticket_price_max: float = 0
    ticket_currency: str = "MOP"
    ticket_url: Optional[str] = None
    ticket_info: Optional[str] = None
    ticket_type: str = "free"
    membership_required: bool = False
    membership_type: Optional[str] = None
    membership_details: Optional[str] = None
    early_bird: bool = False
    early_bird_deadline: Optional[str] = None
    group_discount: bool = False
    
    # Program
    headliners: List[str] = field(default_factory=list)
    performers: List[str] = field(default_factory=list)
    djs: List[str] = field(default_factory=list)
    speakers: List[str] = field(default_factory=list)
    curators: List[str] = field(default_factory=list)
    conductors: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    chefs: List[str] = field(default_factory=list)
    artists: List[str] = field(default_factory=list)
    exhibitors: List[str] = field(default_factory=list)
    description: str = ""
    description_zh: Optional[str] = None
    description_pt: Optional[str] = None
    program_highlights: List[str] = field(default_factory=list)
    schedule_url: Optional[str] = None
    
    # Media
    images: List[Dict] = field(default_factory=list)
    featured_image: Optional[str] = None
    video_url: Optional[str] = None
    social_links: Dict = field(default_factory=dict)
    hashtag: Optional[str] = None
    
    # Practical
    accessibility: Optional[str] = None
    parking: Optional[str] = None
    transport: Optional[str] = None
    weather_policy: Optional[str] = None
    covid_policy: Optional[str] = None
    food_drink_policy: Optional[str] = None
    bag_policy: Optional[str] = None
    reentry_allowed: Optional[bool] = None
    
    # Internal
    crawl_priority: str = "high"
    crawl_frequency: str = "daily"
    data_quality: str = "partial"
    data_completeness_score: float = 0.0
    version: int = 1
    previous_versions: List[str] = field(default_factory=list)
    change_log: List[Dict] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    # Computed at runtime
    last_crawled: str = ""
    crawl_hash: str = ""
    status: str = ""
    
    def compute_hash(self) -> str:
        """Content hash for change detection"""
        key_fields = [
            self.title, self.start_date, self.end_date, self.start_time,
            self.end_time, self.venue_name, self.address, self.ticket_price_min,
            self.ticket_price_max, self.ticket_url, self.description,
            self.ticket_type, self.membership_type
        ]
        content = '|'.join(str(f) for f in key_fields if f)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def compute_status(self) -> str:
        """Compute status from dates"""
        try:
            today = datetime.now().date()
            start = datetime.strptime(self.start_date, '%Y-%m-%d').date() if self.start_date else today
            end = datetime.strptime(self.end_date, '%Y-%m-%d').date() if self.end_date else today
            
            if self.status == 'cancelled':
                return 'cancelled'
            if self.status == 'postponed':
                return 'postponed'
            if start > today:
                return 'upcoming'
            elif start <= today <= end:
                return 'ongoing'
            else:
                return 'completed'
        except ValueError:
            return 'tentative'
    
    def compute_data_quality(self) -> str:
        """Assess data completeness"""
        required = [
            self.title, self.start_date, self.end_date, self.venue_name,
            self.address, self.organizer, self.category
        ]
        optional = [
            self.description, self.ticket_url, self.featured_image,
            self.headliners, self.performers, self.tags,
            self.accessibility, self.transport, self.coordinates
        ]
        
        req_filled = sum(1 for f in required if f)
        opt_filled = sum(1 for f in optional if f)
        
        score = (req_filled / len(required)) * 0.7 + (opt_filled / len(optional)) * 0.3
        self.data_completeness_score = round(score, 2)
        
        if score >= 0.9:
            return 'complete'
        elif score >= 0.6:
            return 'partial'
        return 'minimal'
    
    def to_frontmatter(self) -> Dict:
        """Convert to dict for YAML frontmatter"""
        fm = {}
        for key, value in self.__dict__.items():
            if value not in (None, "", [], {}, 0, 0.0, False) or key in ['ticket_required', 'membership_required', 'recurring', 'early_bird', 'group_discount', 'reentry_allowed']:
                fm[key] = value
        return fm


class BaseCrawler(ABC):
    """Base class for all crawlers"""

    # Class attributes to be overridden
    name: str = ""
    base_url: str = ""
    rate_limit: float = 3.0
    priority: str = "high"
    frequency: str = "daily"
    languages: List[str] = ['en']

    # Domains that serve content via JavaScript and require Playwright rendering.
    # Subclasses can extend this list.
    JS_REQUIRED_DOMAINS: tuple = (
        'venetianmacao.com',
        'sandsresortsmacao.cn',
        'sandsresorts',
        'wynnmacau.com',
        'mgm.mo',
        'melco-resorts.com',
        'studiocity-macau.com',
        'cityofdreamsmacau.com',
        'galaxymacau.com',
        'grandlisboa.com',
        'sjm.com.mo',
    )

    # Domains where wait_until='networkidle' times out because of persistent
    # background connections. These use 'load' + scroll instead.
    LOAD_ONLY_DOMAINS: tuple = (
        'venetianmacao.com',
        'sandsresortsmacao.cn',
        'sandsresorts',
        'galaxymacau.com',
        'wynnresortsmacau.com',
        'cityofdreamsmacau.com',
        'studiocity-macau.com',
        'mgm.mo',
        'sjmresorts.com',
    'londonermacao.com',
    'lisboetamacau.com',
    )

    # Default headers
    DEFAULT_HEADERS: Dict[str, str] = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
    }

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.last_request_time = 0
        self.logger = logging.getLogger(f'crawler.{self.name}')
        self.events_found = 0
        self.events_parsed = 0
        self.errors = []
        self.headers = dict(self.DEFAULT_HEADERS)
    
    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make rate-limited HTTP request"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
        request_headers = {**self.headers, **kwargs.pop('headers', {})}
        return await self.session.request(method, url, headers=request_headers, **kwargs)
    
    async def fetch_html(self, url: str) -> str:
        """Fetch and return HTML content using plain HTTP (no JS execution)."""
        async with await self._rate_limited_request('GET', url) as resp:
            resp.raise_for_status()
            return await resp.text()

    # ------------------------------------------------------------------
    # JavaScript / Playwright rendering
    # ------------------------------------------------------------------

    def _needs_js_render(self, url: str) -> bool:
        """Return True if the URL belongs to a known JS-heavy domain."""
        return any(domain in url for domain in self.JS_REQUIRED_DOMAINS)

    async def fetch_html_js(
        self,
        url: str,
        wait_until: str = 'networkidle',
        timeout: int = 30000,
        scroll: bool = True,
    ) -> str:
        """
        Fetch a page's full rendered HTML using a headless Playwright browser.

        Uses a module-level shared Browser to avoid launching Chromium for
        every request.  Call ``BaseCrawler.close_js_browser()`` in the main
        script's ``finally`` block to release the browser when the crawl ends.

        Args:
            url:        Target URL.
            wait_until: Playwright navigation condition — ``'networkidle'``
                        (default) waits for network activity to stop, which
                        captures most lazy-loaded content.  Use
                        ``'domcontentloaded'`` for a faster but shallower fetch.
            timeout:    Navigation timeout in milliseconds (default 30 s).
            scroll:     If True, scroll halfway and wait 1.5 s to trigger
                        lazy-loaded images before capturing the page HTML.

        Returns:
            The fully rendered HTML as a string.
        """
        global _pw_instance, _pw_browser

        from playwright.async_api import async_playwright

        # Launch a shared browser once per process.
        if _pw_browser is None:
            _pw_instance = async_playwright()
            pw = await _pw_instance.__aenter__()
            _pw_browser = await pw.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                ],
            )
            self.logger.debug('Playwright Chromium browser launched (shared instance).')

        context = await _pw_browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1280, 'height': 800},
            java_script_enabled=True,
        )

        # Block bandwidth-heavy resources that add no text content.
        await context.route(
            '**/*.{mp4,avi,mov,wmv,flv,webm,mp3,wav,ogg,woff,woff2,ttf,eot,otf}',
            lambda route, _req: route.abort(),
        )

        # Auto-select wait_until for domains with persistent background connections
        if wait_until == 'networkidle' and any(d in url for d in self.LOAD_ONLY_DOMAINS):
            wait_until = 'load'

        page = await context.new_page()
        try:
            self.logger.info(f'JS-render (Playwright): {url}')
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            if scroll:
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
                await page.wait_for_timeout(1500)
            html = await page.content()
        finally:
            await context.close()

        return html

    async def fetch_html_smart(self, url: str) -> str:
        """
        Intelligent fetch: Playwright for known JS-heavy domains, plain HTTP
        otherwise — with an automatic JS fallback when the plain fetch yields
        sparse content (no og:image and fewer than 3 real <img> tags).

        This means previously-unknown JS-heavy pages are handled gracefully
        without having to add them to ``JS_REQUIRED_DOMAINS`` first.
        """
        # Known JS-heavy domain — go straight to Playwright.
        if self._needs_js_render(url):
            return await self.fetch_html_js(url)

        # Try plain HTTP first.
        try:
            html = await self.fetch_html(url)
            soup = self._soup(html)

            og = soup.find('meta', attrs={'property': 'og:image'})
            if og and og.get('content', '').startswith('http'):
                return html  # og:image present — content is fine

            real_imgs = [
                img for img in soup.find_all('img')
                if (img.get('src') or img.get('data-src') or '').startswith('http')
            ]
            if len(real_imgs) >= 3:
                return html  # Enough images — probably not JS-gated

            # Sparse — fall back to Playwright.
            self.logger.info(
                f'Plain fetch yielded sparse content ({len(real_imgs)} imgs, no og:image), '
                f'retrying with JS render: {url}'
            )
            return await self.fetch_html_js(url)

        except Exception as exc:
            self.logger.warning(f'Plain fetch failed ({exc}), retrying with JS: {url}')
            return await self.fetch_html_js(url)

    @classmethod
    async def close_js_browser(cls) -> None:
        """
        Shut down the shared Playwright browser.
        Call once at the end of a crawl run to ensure the process exits cleanly.
        """
        global _pw_instance, _pw_browser
        if _pw_browser is not None:
            try:
                await _pw_browser.close()
            except Exception:
                pass
            _pw_browser = None
        if _pw_instance is not None:
            try:
                await _pw_instance.__aexit__(None, None, None)
            except Exception:
                pass
            _pw_instance = None

    # ------------------------------------------------------------------
    # HTML / parsing helpers
    # ------------------------------------------------------------------

    def _soup(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup"""
        return BeautifulSoup(html, 'lxml')
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract Event nodes from direct, list, and @graph JSON-LD."""
        events = []

        def visit(node):
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return
            if not isinstance(node, dict):
                return
            node_type = node.get('@type')
            types = node_type if isinstance(node_type, list) else [node_type]
            if 'Event' in types:
                events.append(node)
            for key in ('@graph', 'itemListElement'):
                if key in node:
                    visit(node[key])

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                content = script.string or script.get_text()
                if not content or not content.strip():
                    continue
                visit(json.loads(content))
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
        return events
    
    def _extract_microdata(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract microdata (schema.org)"""
        events = []
        for elem in soup.find_all(itemtype=re.compile(r'Event')):
            event_data = {}
            for prop in elem.find_all(itemprop=True):
                prop_name = prop.get('itemprop')
                prop_value = prop.get('content') or prop.get('datetime') or prop.get_text(strip=True)
                if prop_name:
                    event_data[prop_name] = prop_value
            if event_data:
                events.append(event_data)
        return events
    
    def _make_id(self, title: str, date_str: str = None) -> str:
        """Generate event ID from title and date"""
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')[:50]
        return f"evt-{date_str}-{slug}"
    
    def _make_guid(self, source_id: str) -> str:
        """Generate GUID from source and source-specific ID"""
        return f"{self.name}:{source_id}"
    
    def _detect_language(self, url: str) -> str:
        """Detect language from URL path"""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            first = path_parts[0]
            if first in ['en', 'zh-hant', 'zh-cn', 'pt', 'th', 'id', 'zh']:
                return first
        return 'en'
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Parse date from various formats and return YYYY-MM-DD."""
        if not text:
            return None

        def _as_date(y: str, m: str, d: str) -> Optional[str]:
            try:
                dt = datetime(int(y), int(m), int(d))
                return dt.strftime('%Y-%m-%d')
            except Exception:
                return None

        patterns = [
            r'(\d{4})[-/\.]?(\d{1,2})[-/\.]?(\d{1,2})',
            r'(\d{1,2})[-/\.]?(\d{1,2})[-/\.]?(\d{4})',
            r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{4})年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
            r'(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            groups = match.groups()
            try:
                if len(groups) == 3:
                    if groups[0].isdigit() and len(groups[0]) == 4:
                        y, a, b = groups
                        dt = _as_date(y, a, b)
                        if dt:
                            return dt
                        dt = _as_date(y, b, a)
                        if dt:
                            return dt
                    elif not groups[0].isdigit():
                        months = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        dt = _as_date(groups[2], months[groups[0].lower()[:3]], groups[1])
                        if dt:
                            return dt
                    elif groups[1].isdigit():
                        d, m, y = groups
                        dt = _as_date(y, m, d)
                        if dt:
                            return dt
                    else:
                        months = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        dt = _as_date(groups[2], months[groups[1].lower()[:3]], groups[0])
                        if dt:
                            return dt
            except (ValueError, IndexError, TypeError):
                continue
        return None

    def _extract_dates_from_text(self, text: str) -> List[str]:
        """Extract all parseable dates from free text and return sorted YYYY-MM-DD list."""
        if not text:
            return []
        candidates = re.findall(
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}\\s*年\\s*\d{1,2}\\s*月\\d{1,2}\\s*日|\d{1,2}[/\\-]?[月]\\d{1,2}[/\\-]?[日]?\s*\d{4}",
            text
        )
        dates = []
        for item in candidates:
            parsed = self._parse_date(item)
            if parsed:
                dates.append(parsed)
        return sorted(set(dates))

    def _extract_visible_date_range(self, text: str):
        """Return the first explicit English event/offer date range in page text."""
        if not text:
            return None, None
        text = re.sub(r'\s+', ' ', text)
        months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
            'march': 3, 'mar': 3, 'april': 4, 'apr': 4, 'may': 5,
            'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
            'december': 12, 'dec': 12,
        }
        month_re = '|'.join(months)

        def iso(year, month, day):
            try:
                return datetime(int(year), int(month), int(day)).strftime('%Y-%m-%d')
            except (TypeError, ValueError):
                return None

        match = re.search(
            rf'\b({month_re})\s+(\d{{1,2}})\s*(?:-|–|—|to)\s*'
            rf'(?:(?:({month_re})\s+)?(\d{{1,2}})),?\s+(20\d{{2}})\b',
            text, re.IGNORECASE
        )
        if match:
            m1, d1, m2, d2, year = match.groups()
            start = iso(year, months[m1.lower()], d1)
            end = iso(year, months[(m2 or m1).lower()], d2)
            if start and end:
                return start, end

        match = re.search(
            rf'\b(\d{{1,2}})\s*(?:-|–|—|to)\s*(\d{{1,2}})\s+({month_re}),?\s+(20\d{{2}})\b',
            text, re.IGNORECASE
        )
        if match:
            d1, d2, month, year = match.groups()
            start = iso(year, months[month.lower()], d1)
            end = iso(year, months[month.lower()], d2)
            if start and end:
                return start, end

        match = re.search(
            rf'\b(\d{{1,2}})\s+({month_re})(?:\s+20\d{{2}})?\s*'
            rf'(?:-|–|—|to)\s*(\d{{1,2}})\s+({month_re})\s+(20\d{{2}})\b',
            text, re.IGNORECASE
        )
        if match:
            d1, m1, d2, m2, year = match.groups()
            start = iso(year, months[m1.lower()], d1)
            end = iso(year, months[m2.lower()], d2)
            if start and end:
                return start, end

        candidates = []
        for pattern, order in [
            (rf'\b({month_re})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b', 'mdy'),
            (rf'\b(\d{{1,2}})\s+({month_re})\s+(20\d{{2}})\b', 'dmy'),
        ]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                a, b, year = match.groups()
                value = iso(year, months[a.lower()], b) if order == 'mdy' else iso(year, months[b.lower()], a)
                if value:
                    candidates.append((match.start(), value))
        if candidates:
            ordered = [value for _, value in sorted(candidates)]
            start = ordered[0]
            end = next((value for value in ordered[1:] if value >= start), start)
            return start, end
        return None, None

    def _parse_price(self, text: str) -> Optional[float]:
        """Extract price from text"""
        if not text:
            return None
        match = re.search(r'(?:MOP|HKD|USD|\$|¥)\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
        match = re.search(r'([\d,]+(?:\.\d{2})?)', text)
        if match:
            return float(match.group(1).replace(',', ''))
        return None

    # ------------------------------------------------------------------
    # Image scoring and extraction
    # ------------------------------------------------------------------

    _IMAGE_BAD_TOKENS = (
        "logo", "icon", "favicon", "facebook", "youtube", "twitter",
        "instagram", "/frame/", "sprite", "arrow", "close", "menu",
        "footer", "header-bg", "nav-", "social", "share-", "button",
        "qr-", "/ads/", "banner-bg", "background-", "border-", "divider",
    )

    def _score_image(self, url: str, alt: str = "", classes: str = "", keywords: List[str] = None) -> int:
        """Score an image candidate for relevance to the event. Higher = better."""
        score = 0
        low = url.lower()
        if any(t in low for t in self._IMAGE_BAD_TOKENS):
            return -999
        img_ext = re.compile(r"\.(?:jpg|jpeg|png|webp|gif)(\?|$|#|&)", re.I)
        if not img_ext.search(low) and "/image" not in low and "/photo" not in low and "/media" not in low:
            score -= 10
        combined = low + " " + alt.lower() + " " + classes.lower()
        for kw in (keywords or []):
            if kw in combined:
                score += 12
        for good_cls in ("hero", "feature", "banner", "event", "cover", "main", "poster", "key-visual"):
            if good_cls in classes.lower():
                score += 8
        for dim in ("1920", "1280", "1200", "1080", "800", "1600"):
            if dim in url:
                score += 4
        if url.count("/") - 2 < 5:
            score += 3
        for small_cls in ("thumb-sm", "x-small", "avatar", "icon-", "nav-icon"):
            if small_cls in classes.lower():
                score -= 6
        return score

    def _extract_best_image(self, soup: BeautifulSoup, source_url: str = "", title: str = "") -> Optional[str]:
        """
        Extract the best matching event image from a parsed page.

        Priority order:
          1. og:image / twitter:image  (authoritative hero, set by the CMS)
          2. JSON-LD image field
          3. <img> tags near the title heading
          4. All remaining <img> tags, scored

        Works correctly on both static HTML and Playwright-rendered HTML (since
        Playwright serialises the fully rendered DOM, including JS-injected
        ``<img src="...">`` tags).
        """
        keywords = [
            w.lower() for w in re.findall(r"[a-zA-Z]{4,}", title)
            if w.lower() not in {"with", "from", "that", "this", "have", "been", "will", "into", "more", "than"}
        ]
        candidates: List[tuple] = []  # (score, url)

        # 1. OG / Twitter meta
        for sel, bonus in [
            ('meta[property="og:image"]', 200),
            ('meta[property="og:image:secure_url"]', 200),
            ('meta[name="twitter:image"]', 190),
            ('meta[name="twitter:image:src"]', 190),
        ]:
            for tag in soup.select(sel):
                src = tag.get("content", "").strip()
                if src:
                    abs_url = urljoin(source_url, src) if source_url else src
                    s = bonus + self._score_image(abs_url, "", "", keywords)
                    if s > -50:
                        candidates.append((s, abs_url))

        # 2. JSON-LD image
        for ld_event in self._extract_json_ld(soup):
            img = ld_event.get("image")
            if not img:
                continue
            if isinstance(img, list):
                img = img[0]
            if isinstance(img, dict):
                img = img.get("url") or img.get("@id", "")
            if isinstance(img, str) and img:
                abs_url = urljoin(source_url, img) if source_url else img
                s = 180 + self._score_image(abs_url, "", "", keywords)
                if s > -50:
                    candidates.append((s, abs_url))

        # 3 & 4. DOM images — prefer those near the event heading
        heading = None
        for h in soup.find_all(["h1", "h2"]):
            h_text = h.get_text(strip=True)
            if any(kw in h_text.lower() for kw in keywords) or len(h_text) > 10:
                heading = h
                break

        nearby_imgs: List = []
        if heading:
            for sib in list(heading.next_siblings)[:10]:
                nearby_imgs += (sib.find_all("img") if hasattr(sib, "find_all") else [])
            parent = heading.parent
            if parent:
                nearby_imgs += parent.find_all("img")

        for img_tag in (nearby_imgs or soup.find_all("img")):
            src = (
                img_tag.get("src") or img_tag.get("data-src") or
                img_tag.get("data-lazy-src") or img_tag.get("data-original") or
                img_tag.get("data-image") or ""
            )
            if not src:
                continue
            abs_url = urljoin(source_url, src) if source_url else src
            alt = img_tag.get("alt", "")
            classes = " ".join(img_tag.get("class", []))
            s = self._score_image(abs_url, alt, classes, keywords)
            bonus = 20 if img_tag in nearby_imgs else 0
            if s > -100:
                candidates.append((s + bonus, abs_url))

        if not candidates:
            return None

        candidates.sort(key=lambda x: -x[0])
        best_score, best_url = candidates[0]
        return best_url if best_score > -50 else None

    # ------------------------------------------------------------------
    # Abstract interface every subclass must implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def fetch_list_urls(self) -> List[str]:
        """Return list of event detail URLs to crawl"""
        pass
    
    @abstractmethod
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        """Parse event detail page into CrawledEvent"""
        pass
    
    # ------------------------------------------------------------------
    # Verify-before-commit layer
    # ------------------------------------------------------------------

    async def verify_event(self, event: 'CrawledEvent', html: str) -> tuple:
        """
        Run lightweight sanity checks on a parsed + AI-enriched event before
        it is written to the wiki.

        Checks performed:
          1. Image URL liveness (HEAD request; skip if no image set)
          2. Ticket URL liveness (HEAD request; skip if same as source URL)
          3. Date sanity (start_date is not more than 2 years in the past,
             end_date >= start_date when both present)
          4. Title sanity (non-empty, not a generic site-title placeholder)

        Returns:
          (confidence: float 0.0–1.0, flags: list[str])

        The event's publication_status is set to 'review' when confidence < 0.5.
        """
        flags: list[str] = []
        score: float = 1.0
        penalty_per_flag = 0.15

        # 1. Title sanity
        title = str(getattr(event, 'title', '') or '').strip()
        if not title:
            flags.append("missing_title")
            score -= penalty_per_flag * 2
        elif len(title) < 4:
            flags.append("title_too_short")
            score -= penalty_per_flag

        # 2. Date sanity
        start_raw = str(getattr(event, 'start_date', '') or '')
        end_raw = str(getattr(event, 'end_date', '') or '')
        if start_raw:
            try:
                start_dt = datetime.strptime(start_raw[:10], '%Y-%m-%d')
                now = datetime.utcnow()
                # More than 2 years in the past is probably stale/wrong
                delta_days = (now - start_dt).days
                if delta_days > 730:
                    flags.append(f"start_date_far_past:{start_raw[:10]}")
                    score -= penalty_per_flag
                if end_raw:
                    end_dt = datetime.strptime(end_raw[:10], '%Y-%m-%d')
                    if end_dt < start_dt:
                        flags.append("end_date_before_start")
                        score -= penalty_per_flag
            except ValueError:
                flags.append(f"unparseable_date:{start_raw[:10]}")
                score -= penalty_per_flag
        else:
            flags.append("missing_start_date")
            score -= penalty_per_flag

        # 3. Image URL liveness (HEAD request, non-fatal — timeout 8 s)
        featured_image = (
            getattr(event, 'featured_image', None)
            or (event.images[0] if getattr(event, 'images', None) else None)
        )
        if featured_image:
            img_url = featured_image if isinstance(featured_image, str) else featured_image.get('url', '')
            if img_url and img_url.startswith('http'):
                try:
                    async with self.session.head(
                        img_url, allow_redirects=True, timeout=8
                    ) as resp:
                        if resp.status >= 400:
                            flags.append(f"image_dead:{resp.status}")
                            score -= penalty_per_flag
                except Exception:
                    flags.append("image_unreachable")
                    score -= penalty_per_flag * 0.5  # softer — network hiccup

        # 4. Ticket URL liveness
        ticket_url = str(getattr(event, 'ticket_url', '') or '')
        source_url = str(getattr(event, 'source_url', '') or getattr(event, 'url', '') or '')
        if ticket_url and ticket_url != source_url and ticket_url.startswith('http'):
            try:
                async with self.session.head(
                    ticket_url, allow_redirects=True, timeout=8
                ) as resp:
                    if resp.status >= 400:
                        flags.append(f"ticket_url_dead:{resp.status}")
                        score -= penalty_per_flag * 0.5
            except Exception:
                pass  # ticket URL check is best-effort

        confidence = max(0.0, min(1.0, score))

        # Record verification results on the event
        existing_dq = getattr(event, 'data_quality', None) or {}
        if not isinstance(existing_dq, dict):
            existing_dq = {}
        existing_dq['verify_confidence'] = round(confidence, 3)
        existing_dq['verify_flags'] = flags
        event.data_quality = existing_dq

        if confidence < 0.5:
            event.publication_status = 'review'
            self.logger.info(
                f"verify_event: {getattr(event, 'title', url)!r} → review "
                f"(confidence={confidence:.2f}, flags={flags})"
            )

        return confidence, flags

    async def fetch_all(self) -> List[CrawledEvent]:
        """Main crawl method — fetches all events for this source."""
        events = []
        urls = await self.fetch_list_urls()
        self.events_found = len(urls)
        self.logger.info(f"Found {len(urls)} event URLs to process")

        for url in urls:
            try:
                # Smart fetch: Playwright for JS-heavy domains, HTTP otherwise.
                html = await self.fetch_html_smart(url)
                event = await self.parse_event(url, html)
                if event:
                    from ai_enrichment import enrich_event
                    event = await enrich_event(event, html, self.session)
                    # Verify before commit: image liveness, ticket URL, date + title sanity
                    await self.verify_event(event, html)
                    event.last_crawled = datetime.utcnow().isoformat() + 'Z'
                    event.crawl_hash = event.compute_hash()
                    event.status = event.compute_status()
                    event.data_quality = event.compute_data_quality()
                    events.append(event)
                    self.events_parsed += 1
            except Exception as e:
                self.errors.append(f"{url}: {e}")
                self.logger.warning(f"Failed to parse {url}: {e}")

        self.logger.info(f"Successfully parsed {self.events_parsed}/{self.events_found} events")
        return events


class WikiWriter:
    """Handles writing events to the wiki filesystem"""
    
    def __init__(self, wiki_root: str = None):
        self.wiki_root = Path(wiki_root) if wiki_root else Path(__file__).parent.parent
        self.events_dir = self.wiki_root / 'events'
        self.changes = []
    
    def get_event_path(self, event: CrawledEvent) -> Path:
        """Determine file path for event"""
        try:
            dt = datetime.strptime(event.start_date, '%Y-%m-%d')
            year = dt.strftime('%Y')
            month = dt.strftime('%m-%B').lower()
        except ValueError:
            year = datetime.now().strftime('%Y')
            month = datetime.now().strftime('%m-%B').lower()
        
        return self.events_dir / year / month / f"{event.id}.md"
    
    def read_existing(self, event: CrawledEvent) -> Optional[Dict]:
        """Read existing event file if exists"""
        path = self.get_event_path(event)
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    fm['_content'] = parts[2]
                    fm['_path'] = path
                    return fm
        except Exception:
            pass
        return None
    
    def write_event(self, event: CrawledEvent, is_new: bool = False):
        """Write event to wiki"""
        path = self.get_event_path(event)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        fm = event.to_frontmatter()
        existing = self.read_existing(event) or {}
        for key in ('featured_image', 'image', 'images', 'translations', 'ticket_url', 'ticket_info'):
            if not fm.get(key) and existing.get(key):
                fm[key] = existing[key]

        lines = ['---']
        for key, value in fm.items():
            if isinstance(value, list):
                if value:
                    lines.append(f'{key}:')
                    for item in value:
                        lines.append(f'  - {json.dumps(item, ensure_ascii=False)}' if isinstance(item, str) else f'  - {item}')
                else:
                    lines.append(f'{key}: []')
            elif isinstance(value, dict):
                lines.append(f'{key}:')
                for k, v in value.items():
                    lines.append(f'  {k}: {json.dumps(v) if isinstance(v, (dict, list)) else v}')
            elif isinstance(value, bool):
                lines.append(f'{key}: {str(value).lower()}')
            elif value is None:
                lines.append(f'{key}: null')
            else:
                needs_json = isinstance(value, str) and ("\n" in value or ":" in value)
                lines.append(f'{key}: {json.dumps(value) if needs_json else value}')
        lines.append('---')
        lines.append('')
        
        if event.description:
            lines.append('# Event Description')
            lines.append('')
            lines.append(event.description)
            lines.append('')
        
        content = '\n'.join(lines)
        path.write_text(content, encoding='utf-8')
        
        action = 'created' if is_new else 'updated'
        self.changes.append(f"{action}: {path.relative_to(self.wiki_root)}")
    
    def commit_changes(self, message: str = None):
        """Git commit changes"""
        import subprocess
        if not self.changes:
            print("No changes to commit")
            return
        
        if not message:
            message = f"crawl: {datetime.now().strftime('%Y-%m-%d')} - {len(self.changes)} changes"
        
        try:
            subprocess.run(['git', 'add', '-A'], cwd=self.wiki_root, check=True)
            subprocess.run(['git', 'commit', '-m', message], cwd=self.wiki_root, check=True)
            subprocess.run(['git', 'push'], cwd=self.wiki_root, check=True)
            print(f"Committed and pushed: {message}")
        except subprocess.CalledProcessError as e:
            print(f"Git commit failed: {e}")


import yaml
