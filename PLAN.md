# Macau Events Platform - Master Plan

## 🎯 Vision
Build a comprehensive, curated events platform for Macau that aggregates events from government, casinos, bars, promoters, and cultural venues. The platform consists of:
1. **GitHub Wiki** - Complete historical archive (past, current, future events with full details)
2. **Public Website** - Shows only current & upcoming events with rich filtering

---

## 📊 Phase 1: Source Discovery & Cataloging (COMPLETED)

### ✅ Verified Working Sources

#### 🏛️ Government & Cultural (Chinese + English)
| Source | URL | Language | Event Types | Structure |
|--------|-----|----------|-------------|-----------|
| **Macao Government Tourism Office (MGTO)** | `https://www.macaotourism.gov.mo/en/events/calendar` | EN/PT/TH/ID/ZH-HANT | Public holidays, major festivals, parades, gastronomy, travel expo, dragon boat | Calendar pages with detail links |
| **Cultural Affairs Bureau (ICM)** | `https://www.icm.gov.mo/en/events/calendar` | EN/ZH | Performances, exhibitions, lectures, arts festival, music festival, parade, fringe festival | Calendar with year/month filter, category tabs |
| **Macao Cultural Centre (CCM)** | `https://www.macaucci.gov.mo/en/events` | EN/ZH | Theater, dance, music, exhibitions | Detail pages with dates, venues, ticketing |
| **Macao Museum of Art (MAM)** | `https://www.mam.gov.mo/en/exhibitions` | EN/ZH-CN | Current/upcoming/past exhibitions, public programs | Category tabs: current, preview, review, off-site |
| **Macao Public Library** | `https://www.library.gov.mo/en/promotion-events` | EN/ZH-HANT | Workshops, talks, exhibitions, children events | Venue-based filtering |

#### 🎰 Major Casino Resorts (English + Chinese)
| Resort Group | Properties | Events URL | Event Types |
|--------------|------------|------------|-------------|
| **Sands China** | Venetian, Parisian, Four Seasons, Conrad, Sheraton, St. Regis, Holiday Inn | `https://www.sandsresortsmacao.com/sands-lifestyle/events-ent.html?lang=en` | Shows, concerts, MICE, dining events |
| **Galaxy Entertainment** | Galaxy Macau, Broadway, Okura, Raku, Banyan Tree, JW Marriott, Ritz-Carlton | `https://www.galaxymacau.com/en/entertainment/` + `/ticketing/event-list/` | Arena shows, lobby shows, dining events, ticketing |
| **Wynn Macau** | Wynn Palace, Wynn Macau | `https://www.wynnmacau.com/en/events/` | Theater shows, dining, nightlife |
| **City of Dreams** | CoD, Studio City, Morpheus, Nüwa | `https://www.cityofdreamsmacau.com/en/entertainment/` | Shows, nightlife, dining |
| **MGM China** | MGM Macau, MGM Cotai | `https://www.mgm.mo/en/entertainment/events` | Theater, dining, nightlife |
| **Grand Lisboa Hotels** | Grand Lisboa, Grand Lisboa Palace | `https://www.grandlisboahotels.com/en/entertainment/` | Shows, dining, MICE |

#### 🍸 Bars, Clubs & Nightlife Venues
| Venue | URL | Type |
|-------|-----|------|
| **Cuba Macau** | `https://www.cubamacao.com` | Live music, DJ nights |
| **Sky 21** | `https://www.sky21.com.mo` | Rooftop bar, events |
| **Bob Bar** | `https://www.bobbarmacau.com` | Cocktail bar, events |
| **La Ferrari** | `https://www.laferrari.com.mo` | Nightclub |
| **Central** | `https://www.centralmacau.com` | Bar/club |
| **The Den** | `https://www.thedenmacau.com` | Speakeasy |
| **Vida Rica** | `https://www.vidarica.com.mo` | Hotel bar |
| **Mizumi** | `https://www.mizumimacao.com` | Restaurant/lounge |

#### 📢 Promoters & Media
| Promoter/Media | URL | Focus |
|----------------|-----|-------|
| **Macau Daily Times** | `https://www.macaudailytimes.com.mo` | Event listings, reviews |
| **TDM (Teledifusão de Macau)** | `https://www.tdm.com.mo` | Cultural events, festivals |
| **Macau News** | `https://www.macaunews.mo` | Events calendar |
| **Inside Asian Living** | `https://www.insideasianliving.com` | Lifestyle events |
| **Macau Lifestyle Media** | Various IG/FB pages | Bar/club events |

---

## 📋 Phase 2: Wiki Data Structure (GitHub Wiki)

### Event Schema (Markdown Frontmatter + Content)

```yaml
---
# Required identifiers
id: "evt-2026-001"                    # Unique slug
source: "macaotourism.gov.mo"         # Source domain
source_url: "https://www.macaotourism.gov.mo/en/events/calendar/gastronomy-fest-2026"
source_language: "en"                 # original source language
supported_languages: ["en", "zh-hant-yue", "zh-cn", "pt", "ko", "th", "de", "it", "es", "sq", "vi", "id"]
last_crawled: "2026-08-26T10:30:00Z"  # ISO timestamp
status: "upcoming"                    # upcoming, ongoing, completed, cancelled

# Core event info
title: "2026 International Cities of Gastronomy Fest, Macao"
title_zh: "2026澳門國際美食之都嘉年華"
title_pt: "Festival Internacional das Cidades da Gastronomia 2026, Macau"

# Wiki translations for display/search
translations:
  en: { title: "...", description: "...", practical_info: "...", translation_status: "source" }
  zh-hant-yue: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  zh-cn: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  pt: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  ko: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  th: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  de: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  it: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  es: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  sq: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  vi: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  id: { title: "...", description: "...", practical_info: "...", translation_status: "machine" }

# Dates & Times
start_date: "2026-03-20"
end_date: "2026-03-29"
start_time: "11:00"
end_time: "22:00"
timezone: "Asia/Macau"
recurring: false
recurrence_rule: null                 # RRULE if recurring

# Venue details
venue_name: "Multiple venues across Macao"
venue_name_zh: "澳門多個場地"
address: "Various locations, Macao SAR"
address_zh: "澳門多個地點"
district: "Multiple"                  # Peninsula, Taipa, Coloane, Cotai
coordinates: { lat: 22.1987, lng: 113.5439 }
venue_type: "festival"                # theater, arena, bar, club, outdoor, museum, library, hotel

# Organizer & Promoter
organizer: "Macao Government Tourism Office"
organizer_zh: "澳門特別行政區政府旅遊局"
organizer_type: "government"          # government, casino, venue, promoter, media
promoter: null                        # If different from organizer
promoter_type: null
promoter_contact: null

# Categorization
category: "festival"                  # festival, concert, theater, exhibition, workshop, party, sports, dining, nightlife
subcategory: "gastronomy"
tags: ["food", "international", "family-friendly", "free-entry", "outdoor"]
age_restriction: "all-ages"           # all-ages, 18+, 21+, 16+
dress_code: "casual"                  # casual, smart-casual, formal, costume, theme

# Ticketing & Access
ticket_required: true
ticket_price_min: 0                   # MOP
ticket_price_max: 500
ticket_currency: "MOP"
ticket_url: "https://www.macaoticket.com/gastronomy-fest-2026"
ticket_info: "Free entry; workshops require registration"
membership_required: false
membership_type: null                 # loyalty, vip, member, none
membership_details: null

# Program Details
headliners: []                        # Artists, performers, chefs, speakers
performers: []
djs: []
speakers: []
curators: []
description: "A 10-day culinary celebration..."
description_zh: "為期10天的美食盛會..."
description_pt: "Uma celebração culinária de 10 dias..."

# Media
images: []
featured_image: "https://www.macaotourism.gov.mo/images/gastronomy-fest-2026.jpg"
video_url: null
social_links:
  facebook: "https://facebook.com/macaotourism"
  instagram: "https://instagram.com/macaotourism"
  wechat: "macao-tourism"

# Practical Info
accessibility: "wheelchair accessible, sign language interpretation available"
parking: "Public parking available at nearby facilities"
transport: "Bus routes 1, 3, 10, 10A, 10B, 10X, 28B, 28C"
weather_policy: "Rain or shine; indoor alternatives for workshops"

# Internal
crawl_priority: "high"                # high, medium, low
crawl_frequency: "daily"              # daily, weekly, monthly
data_quality: "complete"              # complete, partial, minimal
notes: ""
---
```

### Wiki Directory Structure
```
macau-events-wiki/
├── _config.yml                          # Wiki config
├── README.md                            # Main index
├── events/
│   ├── 2026/
│   │   ├── 01-january/
│   │   ├── 02-february/
│   │   ├── 03-march/
│   │   └── ...
│   ├── 2025/
│   └── 2027/
├── sources/
│   ├── government/
│   │   ├── macaotourism.gov.mo.md
│   │   ├── icm.gov.mo.md
│   │   ├── macaucci.gov.mo.md
│   │   ├── mam.gov.mo.md
│   │   └── library.gov.mo.md
│   ├── casinos/
│   │   ├── sandsresortsmacao.com.md
│   │   ├── galaxymacau.com.md
│   │   ├── wynnmacau.com.md
│   │   ├── cityofdreamsmacau.com.md
│   │   ├── mgm.mo.md
│   │   └── grandlisboahotels.com.md
│   ├── venues/
│   │   ├── bars.md
│   │   ├── clubs.md
│   │   └── restaurants.md
│   └── promoters/
│       ├── macaudailytimes.com.mo.md
│       ├── tdm.com.mo.md
│       └── social-media.md
├── categories/
│   ├── festival.md
│   ├── concert.md
│   ├── exhibition.md
│   ├── theater.md
│   ├── nightlife.md
│   └── dining.md
├── venues/
│   ├── venue-index.md
│   ├── peninsula.md
│   ├── taipa.md
│   ├── coloane.md
│   └── cotai.md
└── scripts/
    ├── crawl.py
    ├── validate.py
    ├── generate-index.py
    └── sync-to-web.py
```

---

## 🔄 Phase 3: Daily Crawl Specification

### Crawl Targets & Frequency

| Priority | Sources | Frequency | Method | Selectors/API |
|----------|---------|-----------|--------|---------------|
| **HIGH** | MGTO Calendar | Daily | HTML scrape | `.event-item`, `/events/calendar/*` |
| **HIGH** | ICM Calendar | Daily | HTML scrape | Calendar table, category tabs |
| **HIGH** | CCM Events | Daily | HTML scrape | `.event-list`, `/en/detail/*` |
| **HIGH** | MAM Exhibitions | Daily | HTML scrape | `/exhibitions/`, `/exhibitions/preview` |
| **HIGH** | Galaxy Ticketing | Daily | HTML scrape | `/ticketing/event-list/` |
| **HIGH** | Sands Lifestyle | Daily | HTML scrape | `/sands-lifestyle/events-ent.html` |
| **MEDIUM** | Wynn Events | Daily | HTML scrape | `/en/events/` |
| **MEDIUM** | CoD Entertainment | Daily | HTML scrape | `/en/entertainment/` |
| **MEDIUM** | MGM Events | Daily | HTML scrape | `/en/entertainment/events` |
| **MEDIUM** | Grand Lisboa | Daily | HTML scrape | `/en/entertainment/` |
| **MEDIUM** | Public Library | Weekly | HTML scrape | `/promotion-events/` |
| **LOW** | Individual Bars | Weekly | HTML scrape + Social | Venue-specific |
| **LOW** | Promoters/Media | Weekly | HTML scrape + RSS | Site-specific |

### Crawl Algorithm (Pseudocode)
```python
async def daily_crawl():
    for source in HIGH_PRIORITY_SOURCES:
        events = await fetch_events(source)
        for event in events:
            existing = wiki.get(event.id)
            if not existing or event.updated > existing.last_crawled:
                event.last_crawled = now()
                event.status = compute_status(event.start_date, event.end_date)
                wiki.save(event)
                log_change(event, "updated" if existing else "new")
    
    # Generate indexes
    generate_monthly_indexes()
    generate_category_indexes()
    generate_venue_indexes()
    generate_upcoming_feed()  # For website
```

---

## 🌐 Phase 4: Public Website Features

### Tech Stack Recommendation
- **Static Site**: Astro + React/React Islands (fast, SEO-friendly)
- **Data Source**: GitHub Wiki (via GitHub API or local clone)
- **Search**: Pagefind (client-side) or Algolia
- **Hosting**: Cloudflare Pages / Vercel / Netlify
- **i18n**: EN, Chinese Cantonese / Traditional Chinese, Chinese Mandarin / Simplified Chinese, Portuguese, Korean, Thai, German, Italian, Spanish, Albanian, Vietnamese, Indonesian

### Website Pages
| Page | URL | Data Source |
|------|-----|-------------|
| Home | `/` | Featured upcoming, this weekend, categories |
| Events List | `/events` | All upcoming + ongoing (filterable) |
| Event Detail | `/events/[slug]` | Single event markdown |
| Calendar View | `/calendar` | Month/week/day view |
| Categories | `/category/[cat]` | Filtered by category |
| Venues | `/venues` | Venue directory with events |
| Venues Detail | `/venues/[slug]` | Venue info + upcoming events |
| Sources | `/sources` | Source credibility page |
| About | `/about` | Mission, methodology |
| API | `/api/events.json` | Machine-readable feed |

### Filters (Client-side)
- Date range (this week, this month, custom)
- Category (festival, concert, exhibition, nightlife, etc.)
- District (Peninsula, Taipa, Coloane, Cotai)
- Price (free, paid, price range)
- Language (EN, ZH, PT)
- Age restriction
- Organizer type (gov, casino, venue, promoter)
- Tags

---

## 📁 Phase 5: Implementation Roadmap

### Week 1: Foundation
- [ ] Create GitHub repo with wiki enabled
- [ ] Set up wiki structure (directories, index files)
- [ ] Create event schema validation script
- [ ] Build crawler for top 5 sources (MGTO, ICM, CCM, MAM, Galaxy)

### Week 2: Data Population
- [ ] Crawl all HIGH priority sources (historical + current)
- [ ] Build crawler for MEDIUM priority sources
- [ ] Create data validation & deduplication
- [ ] Generate first wiki indexes

### Week 3: Website MVP
- [ ] Set up Astro project
- [ ] Build event list page with filters
- [ ] Build event detail page
- [ ] Build calendar view
- [ ] Deploy to staging

### Week 4: Polish & Launch
- [ ] Add i18n support
- [ ] Build venue pages
- [ ] Add search (Pagefind)
- [ ] Set up automated daily crawl (GitHub Actions)
- [ ] Production deploy
- [ ] Documentation

---

## 🤖 Automation: GitHub Actions Workflow

```yaml
# .github/workflows/daily-crawl.yml
name: Daily Event Crawl

on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC = 2 PM Macau
  workflow_dispatch:

jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: your-org/macau-events-wiki
          token: ${{ secrets.WIKI_TOKEN }}
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r scripts/requirements.txt
      
      - name: Run crawler
        run: python scripts/crawl.py --all
        env:
          GITHUB_TOKEN: ${{ secrets.WIKI_TOKEN }}
      
      - name: Validate data
        run: python scripts/validate.py
      
      - name: Generate indexes
        run: python scripts/generate-index.py
      
      - name: Commit & push changes
        run: |
          git config user.name "macau-events-bot"
          git config user.email "bot@macau-events.com"
          git add events/ sources/ categories/ venues/
          git diff --staged --quiet || git commit -m "Daily crawl: $(date -u +%Y-%m-%d)"
          git push
      
      - name: Trigger website rebuild
        if: github.event_name == 'schedule'
        run: |
          curl -X POST ${{ secrets.WEBHOOK_URL }} \
            -H "Content-Type: application/json" \
            -d '{"source": "wiki-update"}'
```

---

## 📈 Success Metrics

| Metric | Target |
|--------|--------|
| Sources crawled | 25+ |
| Events in wiki (year 1) | 2,000+ |
| Daily crawl success rate | >99% |
| Website load time | <2s |
| Data freshness | <24h lag |
| Languages supported | 4 (EN, ZH-HANT, ZH-CN, PT) |

---

## 🔐 Legal & Compliance

- Respect `robots.txt` and rate limits
- Cache with `ETag`/`Last-Modified` headers
- Attribution for each source
- No commercial use of copyrighted images without permission
- PDPA/privacy compliance for any user data
- Terms of service for website users

---

## 💡 Future Enhancements

- **Mobile App** (React Native / Flutter)
- **Push Notifications** for favorite categories/venues
- **Personal Calendar** integration (ICS export)
- **Social Features** (save, share, review events)
- **AI Curation** (auto-tagging, similarity matching)
- **Revenue** (affiliate ticketing, promoted listings)
- **API Access** for developers
- **WeChat Mini Program** for Chinese users