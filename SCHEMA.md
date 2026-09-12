# Macau Events Wiki - Event Schema Specification

## 📋 Frontmatter Schema (YAML)

```yaml
---
# ===== IDENTIFIERS (Required) =====
id: "evt-2026-03-20-gastronomy-fest"      # Unique slug: evt-YYYY-MM-DD-slug
guid: "macaotourism.gov.mo:gastronomy-fest-2026"  # Source-domain:source-id
source: "macaotourism.gov.mo"              # Source domain
source_url: "https://www.macaotourism.gov.mo/en/events/calendar/gastronomy-fest-2026"
source_language: "en"                      # original source language: en, zh-hant, zh-cn, pt, ko, th, de, it, es, sq, vi, id
supported_languages: ["en", "zh-hant-yue", "zh-cn", "pt", "ko", "th", "de", "it", "es", "sq", "vi", "id"]
last_crawled: "2026-08-26T10:30:00Z"       # ISO 8601 UTC
crawl_hash: "sha256:abc123..."             # Content hash for change detection
status: "upcoming"                         # upcoming, ongoing, completed, cancelled, postponed

# ===== CORE EVENT INFO (Required) =====
title: "2026 International Cities of Gastronomy Fest, Macao"
title_zh: "2026澳門國際美食之都嘉年華"
title_pt: "Festival Internacional das Cidades da Gastronomia 2026, Macau"
title_alternatives: []                     # Other titles found

# ===== MULTILINGUAL WIKI CONTENT =====
# These translations are wiki information fields, not necessarily source-native text.
# Keep source-native text in source_language/source_url and mark translations as machine/manual reviewed.
translations:
  en:
    language_name: "English"
    title: "2026 International Cities of Gastronomy Fest, Macao"
    description: "A 10-day culinary celebration..."
    practical_info: "Free entry; workshops require registration."
    translation_status: "source"           # source, machine, human-reviewed
  zh-hant-yue:
    language_name: "Chinese Cantonese / Traditional Chinese"
    title: "2026澳門國際美食之都嘉年華"
    description: "..."
    practical_info: "..."
    translation_status: "machine"
  zh-cn:
    language_name: "Chinese Mandarin / Simplified Chinese"
    title: "2026澳门国际美食之都嘉年华"
    description: "..."
    practical_info: "..."
    translation_status: "machine"
  pt: { language_name: "Portuguese", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  ko: { language_name: "Korean", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  th: { language_name: "Thai", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  de: { language_name: "German", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  it: { language_name: "Italian", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  es: { language_name: "Spanish", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  sq: { language_name: "Albanian", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  vi: { language_name: "Vietnamese", title: "...", description: "...", practical_info: "...", translation_status: "machine" }
  id: { language_name: "Indonesian", title: "...", description: "...", practical_info: "...", translation_status: "machine" }

# ===== DATES & TIMES (Required) =====
start_date: "2026-03-20"                   # YYYY-MM-DD (local date)
end_date: "2026-03-29"                     # YYYY-MM-DD (local date)
start_time: "11:00"                        # HH:MM 24h (local time)
end_time: "22:00"                          # HH:MM 24h (local time)
timezone: "Asia/Macau"                     # IANA timezone
recurring: false                           # Boolean
recurrence_rule: null                      # RFC 5545 RRULE if recurring
recurrence_exceptions: []                  # EXDATE array

# ===== VENUE (Required) =====
venue_name: "Multiple venues across Macao"
venue_name_zh: "澳門多個場地"
venue_name_pt: "Vários locais em Macau"
address: "Various locations, Macao SAR"
address_zh: "澳門多個地點"
address_pt: "Vários locais, RAEM"
district: "Multiple"                       # Peninsula, Taipa, Coloane, Cotai, Multiple
coordinates:
  lat: 22.1987
  lng: 113.5439
venue_type: "festival"                     # theater, arena, bar, club, outdoor, museum, library, hotel, restaurant, convention, public_space
venue_id: "venue-multi"                    # Reference to venue index
venue_capacity: null                       # Number if known

# ===== ORGANIZER & PROMOTER =====
organizer: "Macao Government Tourism Office"
organizer_zh: "澳門特別行政區政府旅遊局"
organizer_pt: "Direcção dos Serviços de Turismo"
organizer_type: "government"               # government, casino, venue, promoter, media, cultural_institution
organizer_url: "https://www.macaotourism.gov.mo"
promoter: null                             # If different from organizer
promoter_zh: null
promoter_type: null
promoter_contact:
  email: null
  phone: null
  website: null
  social: {}

# ===== CATEGORIZATION =====
category: "festival"                       # Primary category
subcategory: "gastronomy"                  # Secondary category
tags: 
  - "food"
  - "international"
  - "family-friendly"
  - "free-entry"
  - "outdoor"
  - "cultural"
age_restriction: "all-ages"                # all-ages, 12+, 16+, 18+, 21+
dress_code: "casual"                       # casual, smart-casual, formal, costume, theme, none

# ===== TICKETING & ACCESS =====
ticket_required: true
ticket_price_min: 0                        # MOP (0 = free)
ticket_price_max: 500
ticket_currency: "MOP"                     # MOP, HKD, USD, CNY
ticket_url: "https://www.macaoticket.com/gastronomy-fest-2026"
ticket_info: "Free entry; workshops require registration"
ticket_type: "free"                        # free, paid, donation, registration, invite, membership
membership_required: false
membership_type: null                      # sands_rewards, galaxy_club, wynn_rewards, m_life, mgm_rewards, venue_member, none
membership_details: null
early_bird: false
early_bird_deadline: null
group_discount: false

# ===== PROGRAM DETAILS =====
headliners: []                             # Main attractions
performers: []                             # Performers list
djs: []                                    # DJs
speakers: []                               # Speakers
curators: []                               # Curators
conductors: []                             # Conductors
directors: []                              # Directors
chefs: []                                  # Chefs (for dining events)
artists: []                                # Visual artists
exhibitors: []                             # Exhibitors
description: "A 10-day culinary celebration featuring..."
description_zh: "為期10天的美食盛會..."
description_pt: "Uma celebração culinária de 10 dias..."
program_highlights: []                     # Key program points
schedule_url: null                         # Detailed schedule link

# ===== MEDIA =====
images:
  - url: "https://www.macaotourism.gov.mo/images/gastronomy-fest-2026-main.jpg"
    caption: "Festival main visual"
    credit: "MGTO"
    primary: true
featured_image: "https://www.macaotourism.gov.mo/images/gastronomy-fest-2026-main.jpg"
video_url: null
social_links:
  facebook: "https://facebook.com/macaotourism"
  instagram: "https://instagram.com/macaotourism"
  wechat: "macao-tourism"
  youtube: null
  x: null
hashtag: "#MacaoGastronomyFest2026"

# ===== PRACTICAL INFO =====
accessibility: "Wheelchair accessible; sign language interpretation for selected programs"
parking: "Public parking available at nearby facilities (Tap Seac, NAPE)"
transport: "Bus routes 1, 3, 10, 10A, 10B, 10X, 28B, 28C; Light Rail Taipa Line"
weather_policy: "Rain or shine; indoor alternatives for workshops"
covid_policy: null                         # If applicable
food_drink_policy: "Outside food not permitted in ticketed areas"
bag_policy: "Standard security checks"
reentry_allowed: true

# ===== INTERNAL / METADATA =====
crawl_priority: "high"                     # high, medium, low
crawl_frequency: "daily"                   # daily, weekly, monthly, once
data_quality: "complete"                   # complete, partial, minimal
data_completeness_score: 0.95              # 0-1 score
version: 1                                 # Increment on updates
previous_versions: []                      # Array of previous version timestamps
change_log: []                             # [{"date": "...", "field": "...", "old": "...", "new": "..."}]
flags:
  - "featured"
  - "free-entry"
notes: "Major annual festival; high attendance expected"
internal_tags: ["major-festival", "government-backed", "multi-venue"]
---
```

---

## 🌐 Required Wiki Languages

Every event should preserve the original source language and add a `translations` block for:

| Code | Wiki language |
|------|---------------|
| `en` | English |
| `zh-hant-yue` | Chinese Cantonese / Traditional Chinese |
| `zh-cn` | Chinese Mandarin / Simplified Chinese |
| `pt` | Portuguese |
| `ko` | Korean |
| `th` | Thai |
| `de` | German |
| `it` | Italian |
| `es` | Spanish |
| `sq` | Albanian |
| `vi` | Vietnamese |
| `id` | Indonesian |

For each language, store at minimum: `title`, `description`, `practical_info`, and `translation_status` (`source`, `machine`, or `human-reviewed`).

---

## 🏷️ Controlled Vocabularies

### Categories (Primary)
```yaml
categories:
  - festival
  - concert
  - theater
  - exhibition
  - workshop
  - talk
  - party
  - nightlife
  - dining
  - sports
  - family
  - cultural
  - religious
  - business
  - education
  - wellness
  - charity
  - market
  - parade
  - fireworks
  - film
  - comedy
  - dance
  - opera
  - circus
  - magic
  - other
```

### Subcategories (Examples)
```yaml
subcategories:
  festival: [gastronomy, music, arts, cultural, film, food, wine, beer, seasonal, religious]
  concert: [pop, rock, classical, jazz, electronic, indie, k-pop, mandopop, cantopop]
  theater: [musical, play, opera, ballet, contemporary, experimental, children]
  exhibition: [art, photography, design, history, science, technology, fashion]
  workshop: [art, craft, cooking, dance, music, writing, technology, wellness]
  party: [club, rooftop, pool, beach, themed, holiday, new-year, halloween]
  nightlife: [dj, live-music, karaoke, comedy, burlesque, drag]
  dining: [tasting, pairing, brunch, afternoon-tea, buffet, pop-up, chef-collab]
  sports: [running, cycling, dragon-boat, marathon, tennis, golf, water-sports]
```

### Venue Types
```yaml
venue_types:
  - theater
  - arena
  - concert_hall
  - bar
  - club
  - lounge
  - restaurant
  - hotel
  - casino
  - convention_center
  - museum
  - gallery
  - library
  - cultural_center
  - community_center
  - park
  - plaza
  - street
  - waterfront
  - rooftop
  - outdoor
  - virtual
  - other
```

### Districts
```yaml
districts:
  - "Macau Peninsula"
  - "Taipa"
  - "Coloane"
  - "Cotai"
  - "Multiple"
  - "Online"
```

### Organizer Types
```yaml
organizer_types:
  - government
  - casino
  - venue
  - promoter
  - media
  - cultural_institution
  - educational
  - non_profit
  - corporate
  - individual
  - consortium
```

### Age Restrictions
```yaml
age_restrictions:
  - all-ages
  - 6+
  - 12+
  - 16+
  - 18+
  - 21+
```

### Dress Codes
```yaml
dress_codes:
  - casual
  - smart-casual
  - formal
  - black-tie
  - costume
  - theme
  - beachwear
  - none
```

### Ticket Types
```yaml
ticket_types:
  - free
  - paid
  - donation
  - registration
  - invite
  - membership
  - lottery
```

### Membership Types
```yaml
membership_types:
  - sands_rewards
  - galaxy_club
  - wynn_rewards
  - m_life
  - mgm_rewards
  - venue_member
  - cultural_member
  - library_member
  - museum_friends
  - none
```

### Status Values
```yaml
statuses:
  - upcoming      # Start date in future
  - ongoing       # Started but not ended
  - completed     # End date in past
  - cancelled     # Officially cancelled
  - postponed     # Rescheduled, new dates TBD
  - rescheduled   # New dates confirmed
  - sold_out      # Tickets unavailable
  - tentative     # Not officially confirmed
```

---

## 📁 File Naming Convention

```
events/{YEAR}/{MM-MONTH}/{id}.md

Examples:
events/2026/03-march/evt-2026-03-20-gastronomy-fest.md
events/2026/08-august/evt-2026-08-15-sky21-dj-night.md
events/2025/12-december/evt-2025-12-31-nye-countdown.md
```

---

## 🔍 Validation Rules

### Required Fields (Must Have)
- `id`, `guid`, `source`, `source_url`, `source_language`
- `title`, `start_date`, `end_date`, `timezone`
- `venue_name`, `address`, `district`
- `organizer`, `organizer_type`
- `category`, `status`
- `last_crawled`, `crawl_hash`

### Conditional Required
- If `ticket_required: true` → `ticket_url` or `ticket_info` required
- If `recurring: true` → `recurrence_rule` required
- If `membership_required: true` → `membership_type` required

### Format Validation
- Dates: ISO 8601 (YYYY-MM-DD)
- Times: HH:MM 24-hour
- Timezone: Valid IANA (Asia/Macau)
- URLs: Valid HTTP/HTTPS
- Coordinates: lat -90 to 90, lng -180 to 180
- Price: Non-negative numbers
- Status: From controlled vocabulary

---

## 📄 Markdown Content Section (After Frontmatter)

```markdown
# Event Description

Full detailed description in English...

## 中文描述

完整的中文描述...

## Descrição em Português

Descrição completa em português...

## Program Schedule

| Date | Time | Event | Venue |
|------|------|-------|-------|
| 2026-03-20 | 11:00 | Opening Ceremony | Tap Seac Square |
| 2026-03-21 | 14:00 | Chef Demo: Portuguese Cuisine | Venue A |

## Featured Participants

### Headliners
- **Chef Name** - Michelin-starred chef from Portugal

### Performers
- **Group Name** - Traditional dance troupe

## Gallery

![Event](image-url.jpg)
*Caption*

## Related Links

- [Official Page](source_url)
- [Ticketing](ticket_url)
- [Facebook Event](facebook_url)
```

---

## 🔄 Version Control & Change Tracking

Each event file tracks changes in `change_log`:
```yaml
change_log:
  - date: "2026-08-26T10:30:00Z"
    field: "ticket_price_max"
    old: "300"
    new: "500"
    reason: "VIP packages added"
  - date: "2026-08-20T14:00:00Z"
    field: "status"
    old: "tentative"
    new: "upcoming"
    reason: "Officially confirmed by MGTO"
```

---

## 📊 Data Completeness Scoring

| Field Group | Weight | Fields |
|-------------|--------|--------|
| Core Identity | 20% | id, guid, source, title, dates |
| Venue | 15% | venue_name, address, district, coordinates |
| Organizer | 10% | organizer, organizer_type, contact |
| Categorization | 10% | category, subcategory, tags, age, dress_code |
| Ticketing | 15% | ticket_required, price, url, membership |
| Program | 10% | headliners, performers, description |
| Media | 10% | images, featured_image, social |
| Practical | 10% | accessibility, transport, parking, policies |

Score = sum of (weight × field_completeness) for each group