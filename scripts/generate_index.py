#!/usr/bin/env python3
"""Generate wiki indexes and website-ready feeds from event markdown."""
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json
import yaml

class IndexGenerator:
    def __init__(self, events_dir: Path, output_dir: Path):
        self.events_dir = events_dir
        self.output_dir = output_dir
        self.events = []

    def load_events(self):
        self.events = []
        for filepath in self.events_dir.rglob('*.md'):
            try:
                content = filepath.read_text(encoding='utf-8')
                if not content.startswith('---'):
                    continue
                parts = content.split('---', 2)
                fm = yaml.safe_load(parts[1]) or {}
                rel = filepath.relative_to(self.output_dir)
                fm['_path'] = str(rel)
                fm['_link'] = str(rel)
                self.events.append(fm)
            except Exception as e:
                print(f"Error loading {filepath}: {e}")

    def run(self):
        print('Loading events...')
        self.load_events()
        print(f'Loaded {len(self.events)} events')
        self.generate_events_index()
        self.generate_category_index()
        self.generate_venue_index()
        self.generate_year_indexes()
        self.generate_upcoming_feed()
        self.generate_json_feed()
        print('Done!')

    def _normalize_date(self, date_val):
        """Normalize date to string for consistent sorting."""
        if isinstance(date_val, str):
            return date_val
        elif hasattr(date_val, 'isoformat'):
            return date_val.isoformat()
        return ''

    def event_row(self, evt, include_category=True):
        start = evt.get('start_date', 'TBD')
        end = evt.get('end_date', '')
        date = start if end in ('', start) else f'{start} → {end}'
        title = evt.get('title', 'Untitled')
        venue = evt.get('venue_name', 'TBD')
        district = evt.get('district', 'TBD')
        status = evt.get('status', 'unknown')
        category = evt.get('category', 'other')
        link = f'[{title}]({evt.get("_link")})'
        if include_category:
            return f'| {date} | {link} | {category} | {venue} | {district} | {status} |'
        return f'| {date} | {link} | {venue} | {district} | {status} |'

    def generate_events_index(self):
        lines = ['# Events Archive','',f'Total events: {len(self.events)}','', '| Date | Event | Category | Venue | District | Status |','|---|---|---|---|---|---|']
        for evt in sorted(self.events, key=lambda x: self._normalize_date(x.get('start_date','')), reverse=True):
            lines.append(self.event_row(evt))
        (self.events_dir / 'index.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    def generate_category_index(self):
        out = self.output_dir / 'categories'; out.mkdir(exist_ok=True)
        grouped = defaultdict(list)
        for evt in self.events: grouped[evt.get('category','other')].append(evt)
        lines = ['# Event Categories','','| Category | Count |','|---|---|']
        for cat in sorted(grouped):
            lines.append(f'| [{cat.title()}]({cat}.md) | {len(grouped[cat])} |')
            page=[f'# {cat.title()} Events','',f'Total: {len(grouped[cat])}','','| Date | Event | Venue | District | Status |','|---|---|---|---|---|']
            for evt in sorted(grouped[cat], key=lambda x: self._normalize_date(x.get('start_date','')), reverse=True): page.append(self.event_row(evt, False))
            (out/f'{cat}.md').write_text('\n'.join(page)+'\n', encoding='utf-8')
        (out/'index.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    def generate_venue_index(self):
        out = self.output_dir / 'venues'; out.mkdir(exist_ok=True)
        by_venue=defaultdict(list); by_district=defaultdict(list)
        for evt in self.events:
            by_venue[evt.get('venue_name','Unknown')].append(evt)
            by_district[evt.get('district','Unknown')].append(evt)
        lines=['# Venue Index','','| Venue | Events | District | Type |','|---|---:|---|---|']
        for venue, events in sorted(by_venue.items()):
            first=events[0]
            lines.append(f'| {venue} | {len(events)} | {first.get("district","Unknown")} | {first.get("venue_type","Unknown")} |')
        (out/'index.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
        for district, events in by_district.items():
            safe=district.lower().replace(' ','-')
            page=[f'# Events in {district}','',f'Total: {len(events)}','','| Date | Event | Category | Venue | Status |','|---|---|---|---|---|']
            for evt in sorted(events, key=lambda x: self._normalize_date(x.get('start_date','')), reverse=True):
                page.append(f'| {evt.get("start_date","TBD")} | [{evt.get("title","Untitled")}]({evt.get("_link")}) | {evt.get("category","other")} | {evt.get("venue_name","TBD")} | {evt.get("status","unknown")} |')
            (out/f'{safe}.md').write_text('\n'.join(page)+'\n', encoding='utf-8')

    def generate_year_indexes(self):
        by_year=defaultdict(list)
        for evt in self.events:
            year=self._normalize_date(evt.get('start_date') or 'unknown')[:4]
            by_year[year].append(evt)
        for year, events in by_year.items():
            ydir=self.events_dir/year
            if ydir.exists():
                lines=[f'# Events in {year}','',f'Total: {len(events)}','','| Date | Event | Category | Venue | District | Status |','|---|---|---|---|---|---|']
                for evt in sorted(events, key=lambda x: self._normalize_date(x.get('start_date','')), reverse=True): lines.append(self.event_row(evt))
                (ydir/'index.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    def generate_upcoming_feed(self):
        today=datetime.now().date()
        upcoming=[]
        for evt in self.events:
            try:
                end=datetime.strptime(evt.get('end_date',''), '%Y-%m-%d').date()
                if end >= today and evt.get('status') in ['upcoming','ongoing']:
                    upcoming.append(evt)
            except Exception:
                pass
        lines=['# Upcoming Events Feed','',f'Generated: {datetime.now().isoformat(timespec="seconds")}',f'Total: {len(upcoming)} upcoming/ongoing events','','| Date | Event | Category | Venue | District |','|---|---|---|---|---|']
        for evt in sorted(upcoming, key=lambda x: self._normalize_date(x.get('start_date',''))):
            lines.append(f'| {evt.get("start_date","TBD")} | [{evt.get("title","Untitled")}]({evt.get("_link")}) | {evt.get("category","other")} | {evt.get("venue_name","TBD")} | {evt.get("district","TBD")} |')
        (self.output_dir/'upcoming.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')

    def generate_json_feed(self):
        out=[]
        for evt in self.events:
            event_data = {k: evt.get(k) for k in ['id','title','start_date','end_date','start_time','end_time','status','category','venue_name','district','source','source_url','featured_image','translations']}
            # Normalize date fields to strings for JSON serialization
            for key in ['start_date', 'end_date']:
                if key in event_data and hasattr(event_data[key], 'isoformat'):
                    event_data[key] = event_data[key].isoformat()
            out.append(event_data)
        (self.output_dir/'events.json').write_text(json.dumps(out, ensure_ascii=False, indent=2).encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace'), encoding='utf-8')

if __name__ == '__main__':
    base = Path(__file__).parent.parent
    IndexGenerator(base/'events', base).run()
