# Macau Events Wiki - Source Catalog

> **Last Updated**: 2026-09-10  
> **Status**: Living document - updated with each crawl cycle

---

## 🏛️ Government & Cultural Institutions (Official Sources)

### 1. Macao Government Tourism Office (MGTO)
- **Domains**: `macaotourism.gov.mo`, `www.macaotourism.gov.mo`
- **Languages**: EN, ZH-HANT, ZH-CN, PT, TH, ID
- **Primary URLs**:
  - Events Hub: `https://www.macaotourism.gov.mo/en/events`
  - Calendar: `https://www.macaotourism.gov.mo/en/events/calendar`
  - Detail Pattern: `https://www.macaotourism.gov.mo/en/events/calendar/{slug}`
- **Event Types**: Public holidays, major festivals, parades, fireworks, gastronomy festivals, travel expos, dragon boat races, cultural celebrations
- **Structure**: Calendar grid with filter by year/month → detail pages with dates, venues, descriptions
- **Crawl Selectors**:
  - List: `.event-list-item`, `table.calendar td a`, `.calendar-event`
  - Detail: `.event-detail`, `.article-content`, `main article`
- **Rate Limit**: Respectful (1 req/2s)
- **Robots**: Allows `/en/events/`, `/zh-hant/events/`
- **Credibility**: ⭐⭐⭐⭐⭐ Official government source
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: Multi-language; each language has separate URL path; detail pages have structured data

### 2. Cultural Affairs Bureau (ICM) - 澳門特別行政區政府文化局
- **Domains**: `icm.gov.mo`, `www.icm.gov.mo`
- **Languages**: EN, ZH
- **Primary URLs**:
  - Calendar: `https://www.icm.gov.mo/en/events/calendar`
  - Categories: `/en/events/1,2,21,23,24,25,47` (Performances), `/en/events/3,4,14` (Exhibitions), `/en/events/5,8,16,18,22,28,29,49` (Lectures)
  - Festivals: `/en/events/13` (Macao Arts Festival), `/en/events/12` (Macao Intl Music Festival), `/en/events/76` (Parade), `/en/events/77` (Heritage Day), `/en/events/80` (Fringe Festival)
- **Event Types**: Theater, dance, music, exhibitions, lectures, workshops, major festivals, heritage events
- **Structure**: Interactive calendar with year/month/category filters; detail pages at `/en/events/detail/{id}`
- **Crawl Selectors**:
  - Calendar: `.fc-event`, `.calendar-day a`, `table.events-table`
  - Detail: `.event-detail-content`, `.activity-detail`
- **Rate Limit**: 1 req/2s
- **Credibility**: ⭐⭐⭐⭐⭐ Official government source
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: Rich categorization; historical archives back to 1999; bilingual

### 3. Macao Cultural Centre (CCM) - 澳門文化中心
- **Domains**: `macaucci.gov.mo`, `www.macaucci.gov.mo`
- **Languages**: EN, ZH
- **Primary URLs**:
  - Events: `https://www.macaucci.gov.mo/en/events`
  - Detail Pattern: `https://www.macaucci.gov.mo/en/detail/{id}`
- **Event Types**: Performing arts (theater, dance, music), exhibitions, film screenings, workshops
- **Structure**: List view with pagination → detail pages with venue, date, time, ticketing, program
- **Crawl Selectors**:
  - List: `.event-item`, `.program-list li`
  - Detail: `.program-detail`, `.event-info`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐⭐ Official venue
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: Ticketing links to macauticket.com; venue-specific (Grand Auditorium, Small Auditorium, etc.)

### 4. Macao Museum of Art (MAM) - 澳門藝術博物館
- **Domains**: `mam.gov.mo`, `www.mam.gov.mo`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Current: `https://www.mam.gov.mo/en/exhibitions/`
  - Upcoming: `https://www.mam.gov.mo/en/exhibitions/preview`
  - Past: `https://www.mam.gov.mo/en/exhibitions/review`
  - Off-site: `https://www.mam.gov.mo/en/list/27/`
  - Public Programs: `https://www.mam.gov.mo/en/eventList/56`
  - Friends Events: `https://www.mam.gov.mo/en/eventList/32`
- **Event Types**: Art exhibitions (current/upcoming/past), public programs, workshops, talks, members-only events
- **Structure**: Category tabs → exhibition list → detail pages with curator, artists, dates, venue
- **Crawl Selectors**:
  - List: `.exhibition-item`, `.list-item`
  - Detail: `.exhibition-detail`, `.content-area`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐⭐ Official museum
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: Membership events (Friends of MAM); bilingual but ZH-CN primary

### 5. Macao Public Library - 澳門公共圖書館
- **Domains**: `library.gov.mo`, `www.library.gov.mo`
- **Languages**: EN, ZH-HANT
- **Primary URLs**:
  - Events Hub: `https://www.library.gov.mo/en/promotion-events`
  - Venues: `/en/promotion-events/venues` (Central, Senado, Ho Tung, Mong Ha, etc.)
  - Venue Events: `/en/promotion-events/venues/{venue-slug}`
- **Event Types**: Workshops, talks, reading programs, exhibitions, children activities, cultural events
- **Structure**: Venue-based navigation → event listings per venue
- **Crawl Selectors**:
  - List: `.event-item`, `.activity-list li`
  - Detail: `.event-detail`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Official public institution
- **Priority**: MEDIUM
- **Frequency**: Weekly
- **Notes**: Many free community events; venue-specific calendars

---

## 🎰 Major Casino Resorts (Integrated Resorts)

### 6. Sands China Limited - 金沙中國有限公司
- **Properties**: The Venetian Macao, The Parisian Macao, Four Seasons Macao, Conrad Macao, Sheraton Grand Macao, The St. Regis Macao, Holiday Inn Macao
- **Domains**: `en.sandsresortsmacao.com`, `venetianmacao.com`, `parisianmacao.com`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Unified: `https://en.sandsresortsmacao.com/sands-lifestyle/events-ent.html`
  - Venetian: `https://www.venetianmacao.com/entertainment.html`
  - Parisian: `https://www.parisianmacao.com/entertainment.html`
  - Venetian offers: `https://www.venetianmacao.com/promotions.html`
  - Parisian offers: `https://www.parisianmacao.com/offers.html`
- **Event Types**: Theater shows (House of Dancing Water, etc.), concerts, dining events, MICE, seasonal celebrations
- **Structure**: Category tabs (Entertainment, MICE) → event cards with "Learn More" links
- **Crawl Selectors**:
  - List: `.event-card`, `.lifestyle-event-item`
  - Detail: `.event-detail-page`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: Unified lifestyle portal; some events property-specific; loyalty program (Sands Rewards) events

### 7. Galaxy Entertainment Group - 銀河娛樂集團
- **Properties**: Galaxy Macau, Broadway Macau, Hotel Okura Macau, The Raku, Banyan Tree Macau, JW Marriott Macau, The Ritz-Carlton Macau
- **Domains**: `galaxyentertainment.com`, `galaxymacau.com`, `broadwaymacau.com`, `okuramacau.com`, `rakumacao.com`, `banyantreemacao.com`, `jwmarriottmacau.com`, `ritzcarltonmacau.com`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Main: `https://www.galaxymacau.com/en/entertainment/`
  - Ticketing: `https://www.galaxymacau.com/ticketing/event-list/` ⭐ KEY SOURCE
  - Shows: `/entertainment/galaxy-macau-diamond-show/`, `/entertainment/crystal-lobby/`
  - Dining Events: `/dining/exclusive-gastronomic-events/`
- **Event Types**: Arena concerts (Galaxy Arena), lobby shows, dining events, theater, nightlife, seasonal
- **Structure**: Ticketing page has structured event list with dates, times, prices, seating maps
- **Crawl Selectors**:
  - Ticketing: `.event-list-item`, `.ticket-event`
  - Detail: `.event-detail`, `.ticketing-detail`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: HIGH
- **Frequency**: Daily
- **Notes**: **Ticketing page is goldmine** - structured data, prices, seat maps, direct purchase links

### 8. Wynn Macau - 永利澳門
- **Properties**: Wynn Palace, Wynn Macau
- **Domains**: `wynnresortsmacau.com`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Wynn Palace offers: `https://www.wynnresortsmacau.com/en/wynn-palace/offers`
  - Wynn Macau offers: `https://www.wynnresortsmacau.com/en/wynn-macau/offers`
- **Event Types**: Theater productions (The House of Magic, etc.), dining events, nightlife, seasonal
- **Structure**: Category filters → event cards → detail with booking
- **Crawl Selectors**:
  - List: `.event-item`, `.show-card`
  - Detail: `.event-detail`
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: MEDIUM
- **Frequency**: Daily
- **Notes**: SSL cert issues sometimes; Wynn Rewards member events

### 9. Melco Resorts - City of Dreams & Studio City
- **Properties**: City of Dreams, Studio City, Morpheus, Nüwa
- **Domains**: `cityofdreamsmacau.com`, `studiocity-macau.com`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - CoD: `https://www.cityofdreamsmacau.com/en/events`
  - Studio City: `https://www.studiocity-macau.com/en/events`
  - Dated dining offers: `/en/offers`
- **Event Types**: Water show (House of Dancing Water - at CoD), theater, nightlife, dining, seasonal
- **Structure**: Category tabs → event listings
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: MEDIUM
- **Frequency**: Daily
- **Notes**: House of Dancing Water is permanent show; Studio City has unique events

### 10. MGM China - 美高梅中國
- **Properties**: MGM Macau, MGM Cotai
- **Domains**: `mgm.mo`, `mgmchina.mo`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Happenings: `https://www.mgm.mo/en/entertainment`
  - Dated dining/bar offers: `https://www.mgm.mo/en/best-deal`
- **Event Types**: Theater (MGM Theater), dining, nightlife (MGM Lion Club), seasonal
- **Structure**: Event calendar/list → detail pages
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: MEDIUM
- **Frequency**: Daily
- **Notes**: MGM Theater has regular productions; M Life Rewards events

### 11. SJM Resorts / Grand Lisboa - 葡京綜合度假村 / 葡京酒店
- **Properties**: Grand Lisboa, Grand Lisboa Palace
- **Domains**: `sjmresorts.com`, `grandlisboa.com`, `grandlisboapalace.com`
- **Languages**: EN, ZH-CN
- **Primary URLs**:
  - Group happenings: `https://www.sjmresorts.com/en/happenings`
  - Palace happenings: `https://www.grandlisboapalace.com/en/happenings`
- **Event Types**: Shows, dining events, MICE, seasonal
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐⭐ Major operator
- **Priority**: MEDIUM
- **Frequency**: Daily

### 12. SJM Resorts - Lisboa, Casino Lisboa, etc.
- **Properties**: Hotel Lisboa, Casino Lisboa, Jai Alai, etc.
- **Domains**: `sjmholdings.com`, `hotellisboa.com.mo`
- **Languages**: EN, ZH-CN, PT
- **Priority**: LOW (limited public event listings)
- **Frequency**: Weekly

---

## 🍸 Bars, Clubs & Independent Venues

### 13. Macau Fisherman's Wharf (Tier 3 official venue)
- **Domain**: `fishermanswharf.com.mo`
- **Primary URLs**:
  - Scheduled events: `https://www.fishermanswharf.com.mo/whats-on/`
  - Dated dining/nightlife offers: `https://www.fishermanswharf.com.mo/promotions/`
- **Event Types**: Expos and public events; restaurant, buffet, brunch, tasting and bar promotions only when an explicit date range is published
- **Rate Limit**: 1 req/3s
- **Credibility**: ⭐⭐⭐ Official venue/operator website
- **Priority**: LOW
- **Frequency**: Weekly
- **Admission rule**: Reject generic restaurant pages, hotel packages, vouchers and `from now` offers without a source-stated start date. Recurring offers must publish both a validity range and cadence.

### Unverified/Not Onboarded Nightlife Domains
Previously listed bar and club domains were removed from the active source plan because they did not provide a validated, live, crawlable schedule on 2026-09-10. Social-only announcements and generic venue pages are not Tier-3 sources. Add a venue only after its official website exposes dated recurring or scheduled events.

### Crawl Strategy for Venues
- **Primary**: Website event pages (if exist)
- **Secondary**: Instagram/Facebook (via public pages or Graph API)
- **Tertiary**: Third-party listings (Time Out, Macau Lifestyle, etc.)
- **Frequency**: Weekly (less structured, more volatile)
- **Data Quality**: Often partial - capture what's available

---

## 📢 Promoters, Media & Aggregators

| Source | Domain | Type | Value |
|--------|--------|------|-------|
| **Macau Daily Times** | `macaudailytimes.com.mo` | English daily | Event listings, reviews, previews |
| **TDM** | `tdm.com.mo` | Public broadcaster | Cultural events, festivals, live broadcasts |
| **Macau News** | `macaunews.mo` | News portal | Event calendar section |
| **Inside Asian Living** | `insideasianliving.com` | Lifestyle mag | Curated events, venue profiles |
| **Time Out Macau** | `timeout.com/macau` | City guide | Curated listings (may block scrapers) |
| **Macau Lifestyle** | `macaulifestyle.com` / IG | Media | Event coverage, party photos |
| **Hong Kong Macau Events** | FB Groups | Community | User-submitted events |
| **WeChat Official Accounts** | Various | Chinese social | Venue/promoter official accounts |

---

## 🔧 Technical Crawl Specifications

### User-Agent String
```
Mozilla/5.0 (compatible; MacauEventsBot/1.0; +https://github.com/your-org/macau-events-wiki; bot@macau-events.com)
```

### Headers
```python
DEFAULT_HEADERS = {
    'User-Agent': UA_STRING,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-Hant;q=0.8,zh;q=0.7,pt;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}
```

### Rate Limiting Per Domain
```python
RATE_LIMITS = {
    'macaotourism.gov.mo': 2.0,      # 1 req per 2 seconds
    'icm.gov.mo': 2.0,
    'macaucci.gov.mo': 3.0,
    'mam.gov.mo': 3.0,
    'library.gov.mo': 3.0,
    'sandsresortsmacao.com': 3.0,
    'galaxymacau.com': 3.0,
    'galaxyentertainment.com': 3.0,
    'wynnmacau.com': 3.0,
    'cityofdreamsmacau.com': 3.0,
    'studiocitymacau.com': 3.0,
    'mgm.mo': 3.0,
    'grandlisboahotels.com': 3.0,
    # Venues: 5.0s
    # Promoters: 5.0s
}
```

### Retry Policy
- Max retries: 3
- Backoff: exponential (2s, 4s, 8s)
- Retry on: 429, 500, 502, 503, 504, timeout, connection error

### Content Extraction Priority
1. **Structured Data** (JSON-LD, Microdata, RDFa) - highest fidelity
2. **Meta Tags** (Open Graph, Twitter Cards, schema.org)
3. **Semantic HTML** (article, time, address, etc.)
4. **CSS Selectors** (site-specific)
5. **Text Patterns** (regex for dates, prices, etc.)

---

## 📝 Data Quality Tiers

| Tier | Criteria | Action |
|------|----------|--------|
| **Complete** | All required fields + description + images + ticketing | Publish immediately |
| **Partial** | Required fields + some optional | Publish, flag for enrichment |
| **Minimal** | Only title, date, source URL | Hold for manual review |
| **Duplicate** | Same id or title+date+venue match existing | Merge or skip |

### Required Fields for "Complete"
- id, source, source_url, title, start_date, end_date, venue_name, address, category, status

---

## 🔄 Update Detection Strategy

### For Calendar Pages
- Hash the event list HTML → detect changes
- Compare event count vs last crawl
- Check `Last-Modified` / `ETag` headers

### For Detail Pages
- Hash key content areas (description, dates, pricing)
- Track `last_crawled` vs page `lastmod` (sitemap)

### Change Types
- `new` - First time seen
- `updated` - Content changed (time, venue, price, description)
- `cancelled` - Status changed to cancelled
- `rescheduled` - Dates changed
- `enriched` - Added missing fields (images, ticketing, etc.)

---

## 📦 Output: Wiki Commit Format

Each crawl cycle produces:
```
events/2026/08-august/evt-2026-08-26-gastronomy-fest.md
sources/government/macaotourism.gov.mo.md (updated last_crawled)
categories/festival.md (updated index)
venues/venue-index.md (updated)
```

Commit message: `crawl: 2026-08-26 - 47 new, 12 updated, 3 cancelled across 15 sources`