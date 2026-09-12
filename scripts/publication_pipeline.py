#!/usr/bin/env python3
"""Build the local published feed and crawl/source-health reports."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import re

sys.path.insert(0, str(Path(__file__).parent))
from publication import load_events, write_json
from ai_enrichment import _fallback


# ---------------------------------------------------------------------------
# Tier 1 government sources — fast-track to published if they have
# the minimum required fields (title + start_date).  These are primary
# official sources and do not need additional credibility scoring.
# ---------------------------------------------------------------------------
TIER_1_SOURCES = {
    'macaotourism.gov.mo',
    'icm.gov.mo',
    'macaucci.gov.mo',
    'mam.gov.mo',
    'library.gov.mo',
}


def apply_government_fast_track(events: list[dict]) -> int:
    """
    Promote Tier 1 government events to 'published' when they have the
    minimum required fields.  Returns the count of events fast-tracked.
    """
    count = 0
    for event in events:
        source = str(event.get('source') or '')
        if source not in TIER_1_SOURCES:
            continue
        # Only fast-track if it isn't already in a terminal status
        if event.get('publication_status') in ('published', 'rejected'):
            continue
        # Require at least title and start_date to be trustworthy enough
        if event.get('title') and event.get('start_date'):
            event['publication_status'] = 'published'
            count += 1
    return count


def normalize_locations(events: list[dict]) -> None:
    """Repair known venue coordinates before creating the public feed."""
    for event in events:
        venue = str(event.get('venue_name') or '')
        if venue == 'Macao Museum of Art':
            event['coordinates'] = {'lat': 22.1888601, 'lng': 113.5545978}
            event['address'] = 'Avenida Xian Xing Hai, NAPE, Macau'
            event['address_zh'] = '澳門新口岸冼星海大馬路'


def ensure_intelligence(events: list[dict]) -> None:
    for event in events:
        if not event.get('intel_summary'):
            event.update(_fallback(SimpleNamespace(**event)))


def similarity(a: dict, b: dict) -> tuple[int, list[str]]:
    reasons = []
    if a.get('category') and a.get('category') == b.get('category'):
        reasons.append('same category')
    atags = set(a.get('tags') or []); btags = set(b.get('tags') or [])
    if atags & btags: reasons.append('shared tags: ' + ', '.join(sorted(atags & btags)[:3]))
    if a.get('venue_name') and a.get('venue_name') == b.get('venue_name'):
        reasons.append('same venue')
    if a.get('organizer') and a.get('organizer') == b.get('organizer'):
        reasons.append('same organizer')
    return len(reasons), reasons


def add_similar_events(events: list[dict]) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    eligible = [e for e in events if str(e.get('end_date') or e.get('start_date') or '')[:10] >= today]
    for event in events:
        candidates = []
        for other in eligible:
            if other.get('slug') == event.get('slug'): continue
            if event.get('guid') and other.get('guid') == event.get('guid'): continue
            score, reasons = similarity(event, other)
            if score:
                same_script = bool(re.search(r'[㐀-鿿]', str(event.get('title','')))) == bool(re.search(r'[㐀-鿿]', str(other.get('title',''))))
                candidates.append((score, same_script, str(other.get('start_date', '') or ''), other, reasons))
        candidates.sort(key=lambda row: (-int(row[0]), -int(row[1]), str(row[2] or ''), str(row[3].get('title') or '')))
        selected, seen = [], set()
        for _, _, _, other, reasons in candidates:
            key = other.get('guid') or other.get('source_url') or other.get('slug')
            if key in seen: continue
            seen.add(key)
            selected.append({'slug': other.get('slug'), 'title': other.get('title'), 'reason': ', '.join(reasons)})
            if len(selected) == 5: break
        event['similar_events'] = selected


def build(root: Path) -> int:
    now = datetime.now(timezone.utc).isoformat()
    events, load_errors = load_events(root / "events")

    # Government fast-track: promote Tier 1 events that have minimum fields
    fast_tracked = apply_government_fast_track(events)
    if fast_tracked:
        print(f"Government fast-track: promoted {fast_tracked} Tier 1 event(s) to published")

    published_all = [e for e in events if e.get("publication_status") == "published"]
    # Deduplicate by guid — keep the record with an English title as fallback,
    # preferring the one with the most translations filled in.
    _seen_guids: dict = {}
    for e in published_all:
        g = e.get("guid") or e.get("source_url") or e.get("slug", "")
        if g not in _seen_guids:
            _seen_guids[g] = e
        else:
            # Keep whichever has more translations
            existing = _seen_guids[g]
            if len((e.get("translations") or {})) > len((existing.get("translations") or {})):
                _seen_guids[g] = e
    published = list(_seen_guids.values())
    review = [e for e in events if e.get("publication_status") == "review"]
    rejected = [e for e in events if e.get("publication_status") == "rejected"]
    normalize_locations(published)
    ensure_intelligence(published)
    add_similar_events(published)
    feed = [{k: v for k, v in e.items() if not k.startswith("_")} for e in published]
    review_feed = [{k: v for k, v in e.items() if not k.startswith("_")} for e in review]
    write_json(root / "published" / "events.json", feed)
    write_json(root / "review" / "events.json", review_feed)
    write_json(root / "rejected" / "events.json", [{k: v for k, v in e.items() if not k.startswith("_")} for e in rejected])

    bands = Counter(e.get("credibility_band", "unknown") for e in events)
    statuses = Counter(e.get("publication_status", "unknown") for e in events)
    sources = defaultdict(lambda: {"total": 0, "published": 0, "review": 0, "rejected": 0, "trust_levels": Counter()})
    for event in events:
        src = str(event.get("source") or "unknown")
        row = sources[src]; row["total"] += 1
        status = event.get("publication_status", "unknown")
        if status in row: row[status] += 1
        row["trust_levels"][event.get("source_trust_level", "unknown")] += 1
    source_health = {}
    for src, row in sorted(sources.items()):
        source_health[src] = {**row, "trust_levels": dict(row["trust_levels"]),
                              "publication_rate": round(row["published"] / row["total"], 3) if row["total"] else 0}
    report = {
        "generated_at": now, "archive_events": len(events), "published_events": len(published),
        "review_events": len(review), "rejected_events": len(rejected),
        "load_errors": len(load_errors), "credibility_bands": dict(bands), "publication_status": dict(statuses),
        "government_fast_tracked": fast_tracked,
        "errors": load_errors,
    }
    write_json(root / "reports" / "latest-crawl.json", report)
    write_json(root / "reports" / "source-health.json", {"generated_at": now, "sources": source_health})
    # Warn about rejected sources — split by root cause so each is actionable
    fully_rejected = {
        src: row for src, row in source_health.items()
        if row["total"] > 0 and row["published"] == 0 and row["rejected"] > 0
        and src not in ("unknown",)
    }
    if fully_rejected:
        # Separate: unknown trust (needs COMMERCIAL_DOMAINS entry) vs known trust but bad data
        rej_events_by_src = {}
        for e in rejected:
            src = str(e.get("source") or "unknown")
            rej_events_by_src.setdefault(src, []).append(e)
        unknown_trust = {s: r for s, r in fully_rejected.items()
                        if all(e.get("source_trust_level","unknown") == "unknown"
                               for e in rej_events_by_src.get(s, []))}
        bad_data = {s: r for s, r in fully_rejected.items() if s not in unknown_trust}
        if unknown_trust:
            print("WARNING: untrusted source domains — add to COMMERCIAL_DOMAINS in publication.py:")
            for src in sorted(unknown_trust):
                print(f"  {src}: {unknown_trust[src]['rejected']} rejected")
        if bad_data:
            print("WARNING: trusted sources with 0 published events (data quality issue — likely missing start_date):")
            for src in sorted(bad_data):
                print(f"  {src}: {bad_data[src]['rejected']} rejected")

    print(f"Publication pipeline: archive={len(events)} published={len(published)} review={len(review)} rejected={len(rejected)} load_errors={len(load_errors)} gov_fast_tracked={fast_tracked}")
    return 1 if load_errors else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).parent.parent))
    args = parser.parse_args()
    raise SystemExit(build(Path(args.root).resolve()))
