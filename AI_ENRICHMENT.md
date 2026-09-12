# Macau Event Intelligence Enrichment

The crawler reads the complete event detail page before writing the Markdown record.
It adds factual visitor intelligence to the event frontmatter:

- `intel_summary`
- `event_type_explained`
- `best_for`
- `experience_level`
- `intel_highlights`
- `practical_intelligence`
- `considerations`
- `ai_confidence`
- `ai_enrichment_status`
- `ai_enrichment_model`
- `ai_enriched_at`

## AI endpoint

Set these environment variables for an OpenAI-compatible model endpoint:

```bash
export MACAU_AI_BASE_URL="http://127.0.0.1:11434"
export MACAU_AI_MODEL="your-model-name"
# Optional for hosted providers:
export MACAU_AI_API_KEY="..."
```

The crawler calls:

```text
POST ${MACAU_AI_BASE_URL}/v1/chat/completions
```

The model receives the structured event fields and cleaned source-page text.
The response must be JSON and is checked for all required intelligence fields.
Dates, prices, venues and access claims must come from the source; unknown
information must be stated as unknown or placed in `considerations`.

If no endpoint is configured, or the endpoint fails, the crawler uses a
conservative local fallback that summarizes only already-extracted fields and
marks the record as `fallback` or `fallback_after_error`. It never fabricates
facts.

## Similar events

After publication, `scripts/publication_pipeline.py` adds up to five
`similar_events` entries based on shared category, tags, venue or organizer.
These links are generated from published records only.

## Run manually

```bash
cd /Users/besa/macau-events-wiki
python scripts/crawl.py --source macaotourism.gov.mo
python scripts/generate_index.py
python scripts/validate.py --published-only
python scripts/publication_pipeline.py
```
