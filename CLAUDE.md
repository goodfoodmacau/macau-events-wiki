# Macau Events Wiki — Claude Code Instructions

## Project Overview
This is the **crawler pipeline and knowledge base** for [macauevent.good-food-macau.workers.dev](https://macauevent.good-food-macau.workers.dev).

It scrapes, enriches, and publishes Macau event listings from 22 sources across hotels, nightlife, arts venues, and news outlets.

## Repository Layout
```
scripts/          ← Python crawler pipeline (the main engine)
  crawlers/       ← One file per source (22 crawlers)
  ai_enrichment.py
  publication_pipeline.py
  scheduled-crawl.sh
  url_map.json
events/           ← Raw scraped event JSON files
published/        ← Cleaned & enriched events ready for the website
rejected/         ← Events that failed verify_event() checks
logs/             ← Crawl and pipeline run logs
sources/          ← Per-source metadata and notes
venues/           ← Venue reference data
categories/       ← Event category taxonomy
```

## Key Docs to Read First
- `CRAWL_SPEC.md` — Full technical spec for the pipeline
- `CRAWL_REGISTRY.md` — All 22 registered sources with tiers and URLs
- `SOURCES.md` — Source-by-source notes, quirks, and anti-bot status
- `SCHEMA.md` — Event JSON schema (required fields, formats)
- `AI_CRAWLER_INSTRUCTIONS.md` — How Claude should build or modify crawlers
- `AI_ENRICHMENT.md` — How the enrichment step works

## How to Run
```bash
cd scripts/

# Run a single crawler
python crawlers/londoner.py

# Run the full Tier 1 pipeline (government/official sources)
python publication_pipeline.py --tier 1

# Run the scheduled crawl (all tiers, with logging)
bash scheduled-crawl.sh

# Run enrichment on scraped events
python ai_enrichment.py
```

## Crawler Tiers
| Tier | Frequency | Sources |
|------|-----------|---------|
| 1 | Daily | Government / official venues (MGM, Wynn, Galaxy, Sands, etc.) |
| 2 | Every 3 days | Major hotels (Londoner, Lisboeta, etc.) |
| 3 | Weekly | Bars, nightlife, lifestyle (8 sources) |
| 4 | Monthly | Deep crawl — news outlets, aggregators |

## Anti-Bot Notes
- **Londoner & Lisboeta** use Playwright with UA/viewport rotation and cookie-consent dismissal
- **Lisboeta** has exponential back-off with jitter
- All crawlers rotate User-Agent strings (see `base.py`)
- Do NOT remove the `verify_event()` check — it prevents hallucinated events

## Adding a New Crawler
1. Read `AI_CRAWLER_INSTRUCTIONS.md` fully
2. Copy the closest existing crawler as a template
3. Register it in `crawlers/__init__.py` with the correct tier
4. Add its seed URL to `url_map.json`
5. Add source notes to `SOURCES.md`
6. Test with: `python crawlers/yourcrawler.py`

## Connected Website Repo
The website that consumes this data: [goodfoodmacau/macau.events](https://github.com/goodfoodmacau/macau.events)

The `crawler/` folder in that repo is a mirror of `scripts/` here.

## Do NOT
- Delete or truncate `events.json` (it is the live event database)
- Commit log files (`*.log`) — they are gitignored
- Remove `verify_event()` calls from any crawler
- Push directly to `main` without testing at least one crawler run
