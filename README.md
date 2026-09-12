# Macau Events Wiki

> **Complete historical archive of Macau events** - Past, current, and future events from government, casinos, cultural venues, bars, and promoters.

## 🎯 Purpose

This wiki serves as the **single source of truth** for Macau events data. It stores:
- **Complete event details** (not just title/date - but organizers, promoters, dress codes, membership requirements, ticketing tiers, accessibility, transport, etc.)
- **Historical archive** (past events preserved forever)
- **Future events** (as soon as announced)
- **Multi-language wiki records** for every event: English, Chinese Cantonese / Traditional Chinese, Chinese Mandarin / Simplified Chinese, Portuguese, Korean, Thai, German, Italian, Spanish, Albanian, Vietnamese, and Indonesian.
- **Source attribution** (every event traced to its origin)

The public website ([macau-events.com](https://macau-events.com)) consumes this wiki and shows only **current & upcoming** events with rich filtering.

---

## 📁 Repository Structure

```
macau-events-wiki/
├── PLAN.md                    # Master plan & architecture
├── SCHEMA.md                  # Event data schema (YAML frontmatter)
├── SOURCES.md                 # Source catalog with crawl specs
├── CRAWL_SPEC.md              # Daily crawl specification
├── README.md                  # This file
├── events/                    # Event files (organized by year/month)
│   ├── 2025/
│   ├── 2026/
│   │   ├── 03-march/
│   │   │   └── evt-2026-03-20-gastronomy-fest.md
│   │   ├── 08-august/
│   │   │   └── evt-2026-08-15-galaxy-arena-jay-chou.md
│   │   └── ...
│   └── 2027/
├── sources/                   # Source documentation
│   ├── government/
│   │   ├── macaotourism.gov.mo.md
│   │   ├── icm.gov.mo.md
│   │   ├── macaucci.gov.mo.md
│   │   ├── mam.gov.mo.md
│   │   └── library.gov.mo.md
│   ├── casinos/
│   │   ├── galaxymacau.com.md
│   │   ├── sandsresortsmacao.com.md
│   │   ├── wynnmacau.com.md
│   │   ├── cityofdreamsmacau.com.md
│   │   ├── mgm.mo.md
│   │   └── grandlisboahotels.com.md
│   ├── venues/
│   │   ├── cuba-macao.md
│   │   └── sky21.md
│   └── promoters/
│       └── macaudailytimes.com.mo.md
├── categories/                # Category indexes (auto-generated)
├── venues/                    # Venue indexes (auto-generated)
└── scripts/                   # Crawler & maintenance scripts
    ├── crawl.py
    ├── validate.py
    ├── generate-index.py
    └── requirements.txt
```

---

## 📊 Event Schema

Every event is a Markdown file with **YAML frontmatter** containing 80+ structured fields:

### Required Fields
- `id`, `guid`, `source`, `source_url`, `source_language`
- `title`, `start_date`, `end_date`, `timezone`
- `venue_name`, `address`, `district`
- `organizer`, `organizer_type`
- `category`, `status`
- `last_crawled`, `crawl_hash`

### Rich Detail Fields
- **Ticketing**: prices, tiers, URLs, membership discounts
- **Program**: headliners, performers, DJs, speakers, chefs, curators
- **Media**: images, featured_image, video, social links, hashtags
- **Translations**: full multilingual title/description/practical-info block for EN, Cantonese Chinese, Mandarin Chinese, PT, KO, TH, DE, IT, ES, SQ, VI, ID
- **Practical**: accessibility, parking, transport, weather policy, bag policy
- **Categorization**: tags, age_restriction, dress_code, subcategory
- **Internal**: crawl_priority, data_quality, flags, notes

See [SCHEMA.md](SCHEMA.md) for complete specification.

---

## 🔄 Automated Daily Crawl

**GitHub Actions** runs daily at 06:00 UTC (14:00 Macau):

| Tier | Sources | Frequency | Time (UTC) |
|------|---------|-----------|------------|
| 1 | Government & Cultural (5 sources) | Daily | 06:00 |
| 2 | Major Casinos (6 sources) | Daily | 07:00 |
| 3 | Venues & Promoters (10 sources) | Weekly (Mon) | 06:00 |
| 4 | Deep Archive | Monthly (1st) | 06:00 |

**Crawl Process**:
1. Fetch event list URLs from each source
2. Fetch detail pages for each event
3. Extract structured data (JSON-LD → HTML → text patterns)
4. Compute content hash for change detection
5. Create/update event files in `events/YYYY/MM-month/`
6. Regenerate category/venue indexes
7. Commit changes with summary message

See [CRAWL_SPEC.md](CRAWL_SPEC.md) for complete specification.

---

## 🌐 Source Coverage

### Government & Cultural (Official) ⭐⭐⭐⭐⭐
| Source | Events/Year | Priority |
|--------|-------------|----------|
| MGTO (Tourism Office) | 50-100 | HIGH |
| ICM (Cultural Affairs) | 200-400 | HIGH |
| CCM (Cultural Centre) | 50-100 | HIGH |
| MAM (Museum of Art) | 30-60 | HIGH |
| Public Library | 100-200 | MEDIUM |

### Casino Resorts ⭐⭐⭐⭐
| Operator | Properties | Key Source |
|----------|------------|------------|
| Galaxy Entertainment | 7 | `/ticketing/event-list/` |
| Sands China | 7 | `/sands-lifestyle/events-ent.html` |
| Wynn Macau | 2 | `/en/events/` |
| City of Dreams | 4 | `/en/entertainment/` |
| MGM China | 2 | `/en/entertainment/events` |
| Grand Lisboa | 2 | `/en/entertainment/` |

### Venues & Promoters ⭐⭐⭐
- Bars & clubs (Cuba, Sky 21, Bob Bar, etc.)
- Media (Macau Daily Times, TDM, Inside Asian Living)

---

## 🛠️ Local Development

```bash
# Clone wiki (separate repo)
git clone https://github.com/your-org/macau-events-wiki.wiki.git wiki
cd wiki

# Install dependencies
pip install -r scripts/requirements.txt

# Test crawl single source
python scripts/crawl.py --source macaotourism.gov.mo --dry-run

# Test full tier
python scripts/crawl.py --tier 1 --dry-run

# Validate all events
python scripts/validate.py

# Generate indexes
python scripts/generate-index.py
```

---

## 📈 Data Quality Tiers

| Tier | Criteria | Action |
|------|----------|--------|
| **Complete** | All required + description + images + ticketing | Publish immediately |
| **Partial** | Required + some optional | Publish, flag for enrichment |
| **Minimal** | Only title, date, source URL | Hold for manual review |
| **Duplicate** | Matches existing by GUID or title+date+venue | Merge or skip |

---

## 🔗 Public Website

The wiki powers: **https://macau-events.com** (to be built)

- **Stack**: Astro + React (static, fast, SEO-friendly)
- **Data**: GitHub Wiki via API or local clone at build time
- **Search**: Pagefind (client-side, no server needed)
- **i18n**: EN, ZH-HANT/YUE, ZH-CN/Mandarin, PT, KO, TH, DE, IT, ES, SQ, VI, ID
- **Filters**: Date, category, district, price, organizer, tags, age, dress code
- **Views**: List, Calendar, Map, Categories, Venues

---

## 📝 Contributing

### Manual Event Addition
1. Create file: `events/2026/08-august/evt-2026-08-15-event-slug.md`
2. Use frontmatter from [SCHEMA.md](SCHEMA.md)
3. Run `python scripts/validate.py` to check
4. Commit & push

### Source Updates
1. Update relevant file in `sources/`
2. Adjust crawler in `scripts/crawlers/`
3. Test with `--dry-run`

---

## 📄 License & Attribution

- **Event data**: © respective sources (attributed in each event's `source` field)
- **Wiki structure & code**: MIT License
- **Attribution required** when republishing event data

---

## 🤝 Contact

- **Issues**: GitHub Issues
- **Email**: data@macau-events.com
- **Website**: https://macau-events.com

---

*Last updated: 2026-08-26 | Next crawl: 2026-08-27 06:00 UTC*