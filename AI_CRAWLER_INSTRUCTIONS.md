# AI Crawler Instructions
# Macau Events Wiki — Complete Operating Manual

> Read this file first. It tells you everything you need to do in one place.
> Supporting detail is in the linked source files — read them when you need
> selectors, HTML structure, or source-specific rules.

---

## Step 1 — Read the registry

Open `CRAWL_REGISTRY.md`. Build your task list from every row where `enabled = true`.
Skip rows where `enabled = false` entirely — do not crawl them.

For each enabled source, note:
- its `domain` (used for rate limiting and deduplication)
- its `primary url` (starting point)
- its `detail` link (open this for selectors and source-specific rules)

---

## Step 2 — Determine what to crawl today

| Tier | Frequency | Run when |
|------|-----------|----------|
| Tier 1 — Government | Daily | Every run |
| Tier 2 — Casinos | Daily | Every run |
| Tier 3 — Venues & Media | Weekly | Monday only (or if forced) |

To force a full crawl of all tiers, pass `--all-tiers` to the crawler script.

---

## Step 3 — Crawl each source

For each source in your task list:

1. Open the source's detail file (linked in the registry)
2. Read its `## Crawl Strategy` and `## HTML Structure` sections
3. Fetch the primary URL using the shared headers in `SOURCES.md → Technical Crawl Specifications`
4. Respect the rate limit for that domain (default: 1 request per 3 seconds)
5. Extract all event URLs from the listing page
6. Fetch each detail URL and extract event data

### What to extract from each event

Required fields — skip the event if any are missing:
- `title` — event name in source language
- `start_date` — ISO 8601 (YYYY-MM-DD)
- `source_url` — the detail page URL
- `source` — the domain (e.g. `macaotourism.gov.mo`)

Optional fields — extract if present:
- `end_date`, `venue_name`, `address`, `category`, `organizer`
- `description`, `price`, `tickets_url`, `featured_image`
- `status` (default: `confirmed`)

### Extraction priority order

1. JSON-LD structured data (`<script type="application/ld+json">`)
2. Open Graph / meta tags
3. CSS selectors from the source detail file
4. Text patterns (dates, prices via regex)


---

## Step 4 — Write the event to the wiki

Save each event as a Markdown file at:
```
events/<YYYY>/<MM>-<month-name>/evt-<YYYY>-<MM>-<DD>-<slug>.md
```

Use this frontmatter format:
```yaml
---
guid: <source-domain>:<slug>
title: <event title>
start_date: <YYYY-MM-DD>
end_date: <YYYY-MM-DD or null>
venue_name: <venue>
address: <address>
category: <category>
organizer: <organizer>
source: <domain>
source_url: <url>
source_language: <en|zh|pt|...>
status: confirmed
price: <free|MOP XXX|null>
tickets_url: <url or null>
featured_image: <url or null>
last_crawled: <YYYY-MM-DDTHH:MM:SS+08:00>
---

<description paragraphs>
```

### Deduplication rule

Before writing, check if a file with the same `guid` already exists.
- If found and content changed → update the file, set `last_crawled`
- If found and content same → update only `last_crawled`
- If not found → create new file

The `guid` format is `<source-domain>:<slug>` — e.g. `macaotourism.gov.mo:gastronomy-fest-2026`

---

## Step 5 — AI enrichment (if endpoint configured)

After writing the raw event, call the AI enrichment endpoint defined in `AI_ENRICHMENT.md`.
Pass the extracted fields plus the cleaned source page text.
The AI adds: `intel_summary`, `best_for`, `highlights`, `practical_intelligence`, `considerations`.

If no endpoint is configured → skip enrichment, mark `ai_enrichment_status: skipped`.
If endpoint fails → mark `ai_enrichment_status: fallback_after_error`, do not fabricate facts.

---

## Step 6 — Reject bad events

Do NOT write an event if:
- No explicit start date (e.g. "ongoing" with no date range, "available now")
- Generic venue/hotel package with no event date
- Duplicate of an existing guid with identical content
- Past event (end_date before today) unless in archive mode

Log rejected events to `rejected/events.json` with reason.


---

## Step 7 — After all sources complete

1. Run `scripts/generate_index.py` — rebuilds the event index
2. Run `scripts/validate.py --published-only` — checks data quality
3. Run `scripts/publication_pipeline.py` — scores credibility, moves events to:
   - `published/events.json` — high confidence, goes live on website
   - `review/events.json` — uncertain, needs manual check
   - `rejected/events.json` — failed validation

Commit message format:
```
crawl: <YYYY-MM-DD> — <N> new, <N> updated, <N> rejected across <N> sources
```

---

## Rules that always apply

- Never fabricate dates, prices, venues, or descriptions
- If a field is unknown, leave it null — do not guess
- Preserve existing `featured_image` if your crawl omits it (image may be manually curated)
- Respect robots.txt and rate limits in `SOURCES.md`
- Log all errors to `logs/scheduled-crawl.log`

---

## Quick reference — key files

| file | purpose |
|------|---------|
| `CRAWL_REGISTRY.md` | Master list of sources — enable/disable here |
| `AI_CRAWLER_INSTRUCTIONS.md` | This file — the AI's operating manual |
| `SOURCES.md` | Full technical detail for all sources |
| `CRAWL_SPEC.md` | Crawl schedule and CSS selectors |
| `AI_ENRICHMENT.md` | AI enrichment endpoint and field spec |
| `sources/TEMPLATE.md` | Template for adding a new source file |
| `sources/government/` | Government source detail files |
| `sources/casinos/` | Casino resort source detail files |
| `sources/venues/` | Venue source detail files |
| `sources/promoters/` | Media and promoter source detail files |
