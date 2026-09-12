# Macau Events Wiki - Daily Crawl Specification

> **Purpose**: Defines exactly what to crawl, how often, and in what priority order
> **Execution**: GitHub Actions daily at 06:00 UTC (14:00 Macau)

---

## 🎯 Crawl Targets by Priority

### TIER 1 - DAILY (High Priority, Official Sources)
*Run every day at 06:00 UTC*

| # | Source | URL | Method | Est. Events | Selectors |
|---|--------|-----|--------|-------------|-----------|
| 1 | **MGTO Calendar** | `https://www.macaotourism.gov.mo/en/events/calendar` | HTML | 30-50 | `.event-list-item a`, `table.calendar a` |
| 2 | **MGTO Calendar (ZH)** | `https://www.macaotourism.gov.mo/zh-hant/events/calendar` | HTML | 30-50 | Same as EN |
| 3 | **ICM Calendar** | `https://www.icm.gov.mo/en/events/calendar` | HTML | 50-100 | `.fc-event`, `.calendar-table a` |
| 4 | **ICM Calendar (ZH)** | `https://www.icm.gov.mo/zh/events/calendar` | HTML | 50-100 | Same as EN |
| 5 | **CCM Events** | `https://www.macaucci.gov.mo/en/events` | HTML + Pagination | 20-40 | `.event-item a`, `.program-list a` |
| 6 | **CCM Events (ZH)** | `https://www.macaucci.gov.mo/zh/events` | HTML + Pagination | 20-40 | Same as EN |
| 7 | **MAM Current Exhibitions** | `https://www.mam.gov.mo/en/exhibitions/` | HTML | 5-15 | `.exhibition-item a` |
| 8 | **MAM Upcoming** | `https://www.mam.gov.mo/en/exhibitions/preview` | HTML | 5-15 | `.exhibition-item a` |
| 9 | **MAM Public Programs** | `https://www.mam.gov.mo/en/eventList/56` | HTML | 10-30 | `.event-item a` |
| 10 | **Galaxy Ticketing / Offers** | `https://www.galaxymacau.com/ticketing/event-list/` | HTML + JSON-LD | 10-30 | `/offers/entertainment/`, `/offers/dining/` detail links |
| 11 | **Sands / Venetian Events** | `https://www.venetianmacao.com/entertainment.html` | HTML | 5-15 | `/entertainment/*.html` |
| 12 | **Wynn Dated Dining Offers** | `https://www.wynnresortsmacau.com/en/wynn-palace/offers` | HTML | 0-10 | `/offers/` detail links, date required |

---

### TIER 2 - DAILY (Medium Priority, Casino Resorts)
*Run every day at 07:00 UTC (after Tier 1 completes)*

| # | Source | URL | Method | Est. Events |
|---|--------|-----|--------|-------------|
| 13 | **City of Dreams** | `https://www.cityofdreamsmacau.com/en/events` | HTML + metadata | 0-10 |
| 14 | **Studio City** | `https://www.studiocity-macau.com/en/events` | HTML + metadata | 5-15 |
| 15 | **MGM Events / Dining** | `https://www.mgm.mo/en/best-deal` | HTML + JSON-LD | 5-15 |
| 16 | **SJM / Grand Lisboa** | `https://www.sjmresorts.com/en/happenings` | HTML | 5-20 |
| 17 | **MAM (ZH-CN)** | `https://www.mam.gov.mo/cn/exhibitions/` | HTML | 5-15 |
| 18 | **Public Library** | `https://www.library.gov.mo/en/promotion-events` | HTML + Venue drill | 20-50 |

---

### TIER 3 - WEEKLY (Monday 06:00 UTC)
*Venues, promoters, social media*

| # | Source | URL | Method | Notes |
|---|--------|-----|--------|-------|
| 19 | **Cuba Macau** | `https://www.cubamacao.com` | HTML + IG | Live music schedule |
| 20 | **Sky 21** | `https://www.sky21.com.mo` | HTML | Rooftop events |
| 21 | **Bob Bar** | `https://www.bobbarmacau.com` | HTML + IG | Cocktail events |
| 22 | **La Ferrari** | `https://www.laferrari.com.mo` | Social (IG/FB) | Nightclub events |
| 23 | **Central** | `https://www.centralmacau.com` | Social | Bar/club |
| 24 | **The Den** | `https://www.thedenmacau.com` | Social | Speakeasy |
| 25 | **Macau Daily Times** | `https://www.macaudailytimes.com.mo` | HTML + RSS | Event listings |
| 26 | **TDM** | `https://www.tdm.com.mo` | HTML | Cultural events |
| 27 | **Inside Asian Living** | `https://www.insideasianliving.com` | HTML | Lifestyle events |
| 28 | **Macau News** | `https://www.macaunews.mo` | HTML | Event calendar |

---

### TIER 4 - MONTHLY (1st of month 06:00 UTC)
*Deep archive, historical data, verification*

| # | Source | URL | Purpose |
|---|--------|-----|---------|
| 29 | **MGTO Archive** | `https://www.macaotourism.gov.mo/en/events/calendar?year=YYYY` | Historical backfill |
| 30 | **ICM Archive** | `https://www.icm.gov.mo/en/events/calendar?year=YYYY` | Historical backfill |
| 31 | **CCM Archive** | `https://www.macaucci.gov.mo/en/events?page=X` | Past events |
| 32 | **All Sources** | Full re-crawl | Data integrity check |

---

## 🤖 Crawler Implementation

### Multilingual Enrichment Requirement

After extracting the source event page, each wiki event record must include:

1. Original source text and `source_language`.
2. Image URLs from the event page in `images` and the best display image in `featured_image`.
3. A `translations` block for English, Chinese Cantonese / Traditional Chinese, Chinese Mandarin / Simplified Chinese, Portuguese, Korean, Thai, German, Italian, Spanish, Albanian, Vietnamese, and Indonesian.
4. `translation_status` per language: `source`, `machine`, or `human-reviewed`.

The website can choose which languages to show, but the wiki should store the full multilingual information archive.

### Main Entry Point
```python
# scripts/crawl.py
import asyncio
import argparse
from crawlers import CRAWL_REGISTRY
from wiki import WikiWriter
from validators import validate_event

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tier', choices=['1', '2', '3', '4', 'all'], default='all')
    parser.add_argument('--source', help='Specific source key')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    wiki = WikiWriter()
    results = {'new': 0, 'updated': 0, 'errors': 0, 'skipped': 0}

    # Determine which crawlers to run
    crawlers = get_crawlers_for_tier(args.tier, args.source)

    for crawler in crawlers:
        try:
            events = await crawler.fetch_all()
            for event in events:
                if not validate_event(event):
                    results['errors'] += 1
                    continue
                
                existing = wiki.get(event.id)
                if existing:
                    if event.crawl_hash != existing.crawl_hash:
                        wiki.update(event)
                        results['updated'] += 1
                    else:
                        results['skipped'] += 1
                else:
                    wiki.create(event)
                    results['new'] += 1
        except Exception as e:
            log.error(f"{crawler.name} failed: {e}")
            results['errors'] += 1

    # Generate indexes
    wiki.generate_indexes()
    
    # Commit if not dry-run
    if not args.dry_run and (results['new'] > 0 or results['updated'] > 0):
        wiki.commit(f"crawl: {date.today()} - {results['new']} new, {results['updated']} updated")

    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
```

### Base Crawler Class
```python
# crawlers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup
import hashlib
import json

@dataclass
class CrawledEvent:
    id: str
    guid: str
    source: str
    source_url: str
    source_language: str
    title: str
    title_zh: Optional[str] = None
    title_pt: Optional[str] = None
    start_date: str = ""
    end_date: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timezone: str = "Asia/Macau"
    venue_name: str = ""
    venue_name_zh: Optional[str] = None
    address: str = ""
    address_zh: Optional[str] = None
    district: str = ""
    coordinates: Optional[dict] = None
    venue_type: str = ""
    organizer: str = ""
    organizer_zh: Optional[str] = None
    organizer_type: str = ""
    category: str = ""
    subcategory: Optional[str] = None
    tags: List[str] = None
    age_restriction: str = "all-ages"
    dress_code: str = "casual"
    ticket_required: bool = False
    ticket_price_min: float = 0
    ticket_price_max: float = 0
    ticket_currency: str = "MOP"
    ticket_url: Optional[str] = None
    ticket_info: Optional[str] = None
    ticket_type: str = "free"
    membership_required: bool = False
    membership_type: Optional[str] = None
    description: str = ""
    description_zh: Optional[str] = None
    description_pt: Optional[str] = None
    images: List[dict] = None
    featured_image: Optional[str] = None
    social_links: dict = None
    hashtag: Optional[str] = None
    accessibility: Optional[str] = None
    parking: Optional[str] = None
    transport: Optional[str] = None
    weather_policy: Optional[str] = None
    crawl_priority: str = "high"
    crawl_frequency: str = "daily"
    data_quality: str = "partial"
    last_crawled: str = ""
    crawl_hash: str = ""
    version: int = 1
    flags: List[str] = None
    notes: Optional[str] = None

    def compute_hash(self) -> str:
        """Content hash for change detection"""
        key_fields = [
            self.title, self.start_date, self.end_date, self.start_time,
            self.end_time, self.venue_name, self.address, self.ticket_price_min,
            self.ticket_price_max, self.ticket_url, self.description
        ]
        content = '|'.join(str(f) for f in key_fields if f)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def compute_status(self) -> str:
        from datetime import date, datetime
        today = date.today()
        start = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        end = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        if start > today:
            return 'upcoming'
        elif start <= today <= end:
            return 'ongoing'
        else:
            return 'completed'

class BaseCrawler(ABC):
    name: str = ""
    base_url: str = ""
    rate_limit: float = 3.0  # seconds between requests
    priority: str = "high"
    frequency: str = "daily"
    languages: List[str] = ['en']
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.last_request = 0
    
    async def _rate_limited_get(self, url: str) -> str:
        import time
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()
        
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()
    
    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, 'lxml')
    
    def _extract_json_ld(self, soup: BeautifulSoup) -> List[dict]:
        events = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    events.extend([d for d in data if d.get('@type') == 'Event'])
                elif data.get('@type') == 'Event':
                    events.append(data)
            except:
                pass
        return events
    
    @abstractmethod
    async def fetch_list_urls(self) -> List[str]:
        """Return list of event detail URLs to crawl"""
        pass
    
    @abstractmethod
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        """Parse event detail page into CrawledEvent"""
        pass
    
    async def fetch_all(self) -> List[CrawledEvent]:
        events = []
        urls = await self.fetch_list_urls()
        for url in urls:
            try:
                html = await self._rate_limited_get(url)
                event = await self.parse_event(url, html)
                if event:
                    event.last_crawled = datetime.utcnow().isoformat() + 'Z'
                    event.crawl_hash = event.compute_hash()
                    event.status = event.compute_status()
                    events.append(event)
            except Exception as e:
                log.warning(f"Failed to parse {url}: {e}")
        return events
```

### Example: MGTO Crawler
```python
# crawlers/macaotourism.py
from crawlers.base import BaseCrawler, CrawledEvent
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime

class MGTOCrawler(BaseCrawler):
    name = "macaotourism.gov.mo"
    base_url = "https://www.macaotourism.gov.mo"
    rate_limit = 2.0
    priority = "high"
    frequency = "daily"
    languages = ['en', 'zh-hant', 'pt', 'th', 'id']
    
    async def fetch_list_urls(self) -> List[str]:
        urls = []
        for lang in self.languages:
            cal_url = f"{self.base_url}/{lang}/events/calendar"
            html = await self._rate_limited_get(cal_url)
            soup = self._soup(html)
            
            # Find event detail links
            for link in soup.select('a[href*="/events/calendar/"]'):
                href = link.get('href')
                if href and not href.endswith('/calendar'):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)
        return urls
    
    async def parse_event(self, url: str, html: str) -> Optional[CrawledEvent]:
        soup = self._soup(html)
        
        # Try JSON-LD first
        json_events = self._extract_json_ld(soup)
        if json_events:
            return self._from_json_ld(json_events[0], url)
        
        # Fallback to HTML parsing
        title_el = soup.select_one('h1, .event-title, .page-title')
        title = title_el.get_text(strip=True) if title_el else ''
        
        # Extract date from page
        date_text = soup.get_text()
        date_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', date_text)
        
        # ... more parsing logic
        
        return CrawledEvent(
            id=self._make_id(title),
            guid=f"{self.name}:{self._make_id(title)}",
            source=self.name,
            source_url=url,
            source_language=self._detect_lang(url),
            title=title,
            # ... populate all fields
        )
    
    def _make_id(self, title: str) -> str:
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        return f"evt-{datetime.now().strftime('%Y-%m-%d')}-{slug[:50]}"
```

---

## 📅 GitHub Actions Workflow

```yaml
# .github/workflows/daily-crawl.yml
name: Daily Event Crawl

on:
  schedule:
    - cron: '0 6 * * *'   # Tier 1: 06:00 UTC daily
    - cron: '0 7 * * *'   # Tier 2: 07:00 UTC daily
    - cron: '0 6 * * 1'   # Tier 3: 06:00 UTC Monday
    - cron: '0 6 1 * *'   # Tier 4: 06:00 UTC 1st of month
  workflow_dispatch:
    inputs:
      tier:
        description: 'Crawl tier'
        required: false
        type: choice
        options: ['1', '2', '3', '4', 'all']
      source:
        description: 'Specific source key'
        required: false

permissions:
  contents: write

jobs:
  crawl-tier-1:
    name: Crawl Tier 1 (Official Gov)
    if: github.event.inputs.tier != '2' && github.event.inputs.tier != '3' && github.event.inputs.tier != '4'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          repository: ${{ github.repository }}-wiki
          token: ${{ secrets.WIKI_PAT }}
          path: wiki
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install deps
        run: |
          cd wiki
          pip install -r scripts/requirements.txt
      
      - name: Run Tier 1 Crawl
        run: |
          cd wiki
          python scripts/crawl.py --tier 1
        env:
          GITHUB_TOKEN: ${{ secrets.WIKI_PAT }}
      
      - name: Commit changes
        run: |
          cd wiki
          git config user.name "macau-events-bot"
          git config user.email "bot@macau-events.com"
          git add -A
          git diff --staged --quiet || git commit -m "crawl: tier-1 $(date -u +%Y-%m-%d)"
          git push

  crawl-tier-2:
    name: Crawl Tier 2 (Casinos)
    needs: crawl-tier-1
    if: github.event.inputs.tier != '1' && github.event.inputs.tier != '3' && github.event.inputs.tier != '4'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      # ... same pattern, --tier 2

  crawl-tier-3:
    name: Crawl Tier 3 (Venues/Promoters)
    if: github.event.schedule == '0 6 * * 1' || github.event.inputs.tier == '3'
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      # ... --tier 3

  crawl-tier-4:
    name: Crawl Tier 4 (Monthly Deep)
    if: github.event.schedule == '0 6 1 * *' || github.event.inputs.tier == '4'
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      # ... --tier 4

  notify:
    name: Notify Website Rebuild
    needs: [crawl-tier-1, crawl-tier-2, crawl-tier-3, crawl-tier-4]
    if: always() && github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - name: Trigger website deploy
        run: |
          curl -X POST ${{ secrets.WEBHOOK_URL }} \
            -H "Content-Type: application/json" \
            -d '{"source": "wiki-update", "timestamp": "${{ github.event.workflow_run.updated_at }}"}'
```

---

## 📋 Requirements.txt

```text
# scripts/requirements.txt
aiohttp==3.9.1
beautifulsoup4==4.12.2
lxml==5.1.0
pyyaml==6.0.1
python-dateutil==2.8.2
pytz==2024.1
requests==2.31.0
tenacity==8.2.3
tqdm==4.66.1
```

---

## 📊 Monitoring & Alerting

### Success Metrics (per crawl)
- Events fetched per source
- New vs updated vs skipped
- Error rate per source
- Crawl duration

### Alert Conditions
- Any Tier 1 source returns 0 events (possible site change)
- Error rate > 10% for any source
- Crawl duration > 25 minutes
- Wiki commit fails

### Logging
```python
import logging
import json

class StructuredLogger:
    def __init__(self):
        self.logger = logging.getLogger('macau-events')
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_crawl_start(self, tier: str, sources: List[str]):
        self.logger.info(json.dumps({
            'event': 'crawl_start',
            'tier': tier,
            'sources': sources,
            'timestamp': datetime.utcnow().isoformat()
        }))
    
    def log_crawl_result(self, source: str, result: dict):
        self.logger.info(json.dumps({
            'event': 'crawl_result',
            'source': source,
            **result,
            'timestamp': datetime.utcnow().isoformat()
        }))
    
    def log_error(self, source: str, error: str, url: str = None):
        self.logger.error(json.dumps({
            'event': 'crawl_error',
            'source': source,
            'error': error,
            'url': url,
            'timestamp': datetime.utcnow().isoformat()
        }))
```

---

## 🔧 Local Development

```bash
# Clone wiki repo
git clone https://github.com/your-org/macau-events-wiki.wiki.git wiki

# Install deps
cd wiki
pip install -r scripts/requirements.txt

# Test single source
python scripts/crawl.py --source macaotourism.gov.mo --dry-run

# Test full tier
python scripts/crawl.py --tier 1 --dry-run

# Validate all events
python scripts/validate.py

# Generate indexes
python scripts/generate-index.py
```

---

## 📝 Source-Specific Parsing Notes

### MGTO
- Calendar paginates by month; crawl current + next 3 months
- Detail pages have consistent structure
- Multi-language: crawl each language separately, merge by GUID

### ICM
- Calendar uses FullCalendar.js; may need to simulate AJAX calls
- Category filters: performances, exhibitions, lectures, festivals
- Detail pages at `/en/events/detail/{id}`

### Galaxy Ticketing
- **Best structured data** - has prices, seat maps, showtimes
- Event list loads via AJAX; check network tab for API endpoint
- Each event has unique ticketing URL

### Sands Lifestyle
- Single page with category tabs (Entertainment, MICE)
- Events loaded dynamically; check for API endpoint
- Property-specific events may be on subdomain

### CCM
- Paginated list; follow "Next" links
- Detail pages have rich data: cast, creative team, synopsis
- Ticketing redirects to macauticket.com

### MAM
- Three tabs: Current, Preview, Review
- Public programs separate endpoint
- Friends events require membership

### Venues (Tier 3)
- Most rely on Instagram/Facebook for event announcements
- Consider using Instagram Graph API or public page scraping
- Less structured; capture: title, date, time, cover charge, DJ/performer