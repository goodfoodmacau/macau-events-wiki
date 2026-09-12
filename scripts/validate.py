#!/usr/bin/env python3
"""
Event Validation Script
Validates all event files against the schema.
"""

import os
import sys
import yaml
import re
from publication import assess_event
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Any, Optional

# Schema constants
REQUIRED_FIELDS = [
    'id', 'guid', 'source', 'source_url', 'source_language',
    'title', 'start_date', 'end_date', 'timezone',
    'venue_name', 'address', 'district',
    'organizer', 'organizer_type',
    'category', 'status',
    'last_crawled', 'crawl_hash'
]

VALID_STATUSES = ['upcoming', 'ongoing', 'completed', 'cancelled', 'postponed', 'rescheduled', 'sold_out', 'tentative']
VALID_CATEGORIES = ['festival', 'concert', 'theater', 'exhibition', 'workshop', 'talk', 'party', 'nightlife', 'dining', 'sports', 'family', 'cultural', 'religious', 'business', 'education', 'wellness', 'charity', 'market', 'parade', 'fireworks', 'film', 'comedy', 'dance', 'opera', 'circus', 'magic', 'other']
VALID_DISTRICTS = ['Macau Peninsula', 'Taipa', 'Coloane', 'Cotai', 'Multiple', 'Online']
VALID_ORGANIZER_TYPES = ['government', 'casino', 'venue', 'promoter', 'media', 'cultural_institution', 'educational', 'non_profit', 'corporate', 'individual', 'consortium']
VALID_AGE_RESTRICTIONS = ['all-ages', '6+', '12+', '16+', '18+', '21+']
VALID_DRESS_CODES = ['casual', 'smart-casual', 'formal', 'black-tie', 'costume', 'theme', 'beachwear', 'none']
VALID_TICKET_TYPES = ['free', 'paid', 'donation', 'registration', 'invite', 'membership', 'lottery']
VALID_VENUE_TYPES = ['theater', 'arena', 'concert_hall', 'bar', 'club', 'lounge', 'restaurant', 'hotel', 'casino', 'convention_center', 'museum', 'gallery', 'library', 'cultural_center', 'community_center', 'park', 'plaza', 'street', 'waterfront', 'rooftop', 'outdoor', 'virtual', 'other', 'festival']
VALID_LANGUAGES = ['en', 'zh-hant', 'zh-hant-yue', 'zh-cn', 'pt', 'ko', 'th', 'de', 'it', 'es', 'sq', 'vi', 'id']
REQUIRED_TRANSLATION_LANGUAGES = ['en', 'zh-hant-yue', 'zh-cn', 'pt', 'ko', 'th', 'de', 'it', 'es', 'sq', 'vi', 'id']

class EventValidator:
    def __init__(self, events_dir: Path, published_only: bool = False):
        self.events_dir = events_dir
        self.published_only = published_only
        self.errors = []
        self.warnings = []
        self.stats = {'total': 0, 'valid': 0, 'errors': 0, 'warnings': 0}
    
    def validate_all(self) -> bool:
        event_files = [p for p in self.events_dir.rglob('*.md') if p.name != 'index.md']
        if self.published_only:
            selected = []
            for filepath in event_files:
                try:
                    parts = filepath.read_text(encoding='utf-8').split('---', 2)
                    fm = yaml.safe_load(parts[1]) or {}
                    if isinstance(fm, dict) and assess_event(fm).get('publication_status') == 'published':
                        selected.append(filepath)
                except Exception:
                    pass
            event_files = selected
        self.stats['total'] = len(event_files)
        
        for filepath in event_files:
            self.validate_file(filepath)
        
        self.print_summary()
        return self.stats['errors'] == 0
    
    def validate_file(self, filepath: Path):
        try:
            content = filepath.read_text(encoding='utf-8')
            frontmatter, body = self.parse_frontmatter(content)
            
            if not frontmatter:
                self.add_error(filepath, "No frontmatter found")
                return

            # PyYAML resolves ISO YAML scalars to datetime.date. Keep the
            # original archive untouched, but give validators a stable path.
            frontmatter['_filepath'] = filepath
            
            self.validate_frontmatter(filepath, frontmatter)
            self.validate_dates(frontmatter)
            self.validate_urls(frontmatter)
            self.validate_coordinates(frontmatter)
            
            if not self.has_errors_for_file(filepath):
                self.stats['valid'] += 1
                
        except Exception as e:
            self.add_error(filepath, f"Parse error: {e}")
    
    def parse_frontmatter(self, content: str) -> tuple:
        if not content.startswith('---'):
            return None, content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None, content
        
        try:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2]
            return frontmatter, body
        except yaml.YAMLError as e:
            return None, content
    
    def validate_frontmatter(self, filepath: Path, fm: Dict):
        # Required fields
        for field in REQUIRED_FIELDS:
            if field not in fm or not fm[field]:
                self.add_error(filepath, f"Missing required field: {field}")
        
        # Enum validations
        if 'status' in fm and fm['status'] not in VALID_STATUSES:
            self.add_error(filepath, f"Invalid status: {fm['status']}")
        
        if 'category' in fm and fm['category'] not in VALID_CATEGORIES:
            self.add_warning(filepath, f"Non-standard category: {fm['category']}")
        
        if 'district' in fm and fm['district'] not in VALID_DISTRICTS:
            self.add_warning(filepath, f"Non-standard district: {fm['district']}")
        
        if 'organizer_type' in fm and fm['organizer_type'] not in VALID_ORGANIZER_TYPES:
            self.add_warning(filepath, f"Non-standard organizer_type: {fm['organizer_type']}")
        
        if 'age_restriction' in fm and fm['age_restriction'] not in VALID_AGE_RESTRICTIONS:
            self.add_warning(filepath, f"Non-standard age_restriction: {fm['age_restriction']}")
        
        if 'dress_code' in fm and fm['dress_code'] not in VALID_DRESS_CODES:
            self.add_warning(filepath, f"Non-standard dress_code: {fm['dress_code']}")
        
        if 'ticket_type' in fm and fm['ticket_type'] not in VALID_TICKET_TYPES:
            self.add_warning(filepath, f"Non-standard ticket_type: {fm['ticket_type']}")
        
        if 'venue_type' in fm and fm['venue_type'] not in VALID_VENUE_TYPES:
            self.add_warning(filepath, f"Non-standard venue_type: {fm['venue_type']}")
        
        if 'source_language' in fm and fm['source_language'] not in VALID_LANGUAGES:
            self.add_warning(filepath, f"Non-standard source_language: {fm['source_language']}")

        # Translation coverage validation (warnings for legacy/sample records)
        translations = fm.get('translations')
        if translations:
            if not isinstance(translations, dict):
                self.add_warning(filepath, "translations must be a mapping by language code")
            else:
                missing_langs = [lang for lang in REQUIRED_TRANSLATION_LANGUAGES if lang not in translations]
                if missing_langs:
                    self.add_warning(filepath, f"Missing translations for: {', '.join(missing_langs)}")
                for lang, block in translations.items():
                    if lang not in REQUIRED_TRANSLATION_LANGUAGES:
                        self.add_warning(filepath, f"Non-standard translation language: {lang}")
                    if isinstance(block, dict):
                        for required_key in ['title', 'description', 'practical_info', 'translation_status']:
                            if not block.get(required_key):
                                self.add_warning(filepath, f"translations.{lang} missing {required_key}")
                    else:
                        self.add_warning(filepath, f"translations.{lang} must be a mapping")
        else:
            self.add_warning(filepath, "Missing translations block for multilingual wiki archive")
        
        # ID format
        if 'id' in fm:
            if not re.match(r'^evt-\d{4}-\d{2}-\d{2}-', fm['id']):
                self.add_warning(filepath, f"ID format non-standard: {fm['id']}")
        
        # GUID format
        if 'guid' in fm:
            if not re.match(r'^[^:]+:.+', fm['guid']):
                self.add_warning(filepath, f"GUID format non-standard: {fm['guid']}")
        
        # Conditional required
        if fm.get('ticket_required') and not fm.get('ticket_url') and not fm.get('ticket_info'):
            self.add_warning(filepath, "ticket_required=true but no ticket_url or ticket_info")
        
        if fm.get('recurring') and not fm.get('recurrence_rule'):
            self.add_warning(filepath, "recurring=true but no recurrence_rule")
        
        if fm.get('membership_required') and not fm.get('membership_type'):
            self.add_warning(filepath, "membership_required=true but no membership_type")
        
        # Price validation
        for price_field in ['ticket_price_min', 'ticket_price_max']:
            if price_field in fm and fm[price_field] is not None:
                try:
                    val = float(fm[price_field])
                    if val < 0:
                        self.add_error(filepath, f"{price_field} cannot be negative")
                except (ValueError, TypeError):
                    self.add_error(filepath, f"{price_field} must be a number")
        
        # Data quality
        if 'data_completeness_score' in fm:
            try:
                score = float(fm['data_completeness_score'])
                if not 0 <= score <= 1:
                    self.add_warning(filepath, f"data_completeness_score out of range: {score}")
            except (ValueError, TypeError):
                self.add_warning(filepath, "data_completeness_score must be a number")
    
    def validate_dates(self, fm: Dict):
        date_fields = ['start_date', 'end_date']
        for field in date_fields:
            if field in fm and fm[field]:
                try:
                    d = fm[field]
                    if isinstance(d, (datetime, date)):
                        d = d.strftime('%Y-%m-%d')
                    datetime.strptime(str(d), '%Y-%m-%d')
                except (TypeError, ValueError):
                    self.add_error(fm.get('_filepath', 'unknown'), f"Invalid date format for {field}: {fm[field]} (expected YYYY-MM-DD)")
        
        # Time format
        for field in ['start_time', 'end_time']:
            if field in fm and fm[field]:
                try:
                    datetime.strptime(str(fm[field]), '%H:%M')
                except (TypeError, ValueError):
                    self.add_error(fm.get('_filepath', 'unknown'), f"Invalid time format for {field}: {fm[field]} (expected HH:MM)")
        
        # Timezone
        if 'timezone' in fm and fm['timezone'] != 'Asia/Macau':
            self.add_warning(fm.get('_filepath', 'unknown'), f"Non-standard timezone: {fm['timezone']}")
        
        # Logical date checks
        if 'start_date' in fm and 'end_date' in fm and fm['start_date'] and fm['end_date']:
            try:
                start = self._as_date(fm['start_date'])
                end = self._as_date(fm['end_date'])
                if start > end:
                    self.add_error(fm.get('_filepath', 'unknown'), "start_date after end_date")
            except (TypeError, ValueError):
                pass

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    
    def validate_urls(self, fm: Dict):
        url_fields = ['source_url', 'ticket_url', 'organizer_url', 'video_url', 'schedule_url']
        for field in url_fields:
            if field in fm and fm[field]:
                url = fm[field]
                if not (url.startswith('http://') or url.startswith('https://')):
                    self.add_warning(fm.get('_filepath', 'unknown'), f"{field} not a valid URL: {url}")
        
        # Social links
        if 'social_links' in fm and isinstance(fm['social_links'], dict):
            for platform, url in fm['social_links'].items():
                if url and platform != 'wechat' and not (url.startswith('http://') or url.startswith('https://')):
                    self.add_warning(fm.get('_filepath', 'unknown'), f"social_links.{platform} not a valid URL: {url}")
    
    def validate_coordinates(self, fm: Dict):
        if 'coordinates' in fm and isinstance(fm['coordinates'], dict):
            coords = fm['coordinates']
            if 'lat' in coords:
                try:
                    lat = float(coords['lat'])
                    if not -90 <= lat <= 90:
                        self.add_error(fm.get('_filepath', 'unknown'), f"Invalid latitude: {lat}")
                except (ValueError, TypeError):
                    self.add_error(fm.get('_filepath', 'unknown'), f"Latitude must be a number: {coords['lat']}")
            
            if 'lng' in coords:
                try:
                    lng = float(coords['lng'])
                    if not -180 <= lng <= 180:
                        self.add_error(fm.get('_filepath', 'unknown'), f"Invalid longitude: {lng}")
                except (ValueError, TypeError):
                    self.add_error(fm.get('_filepath', 'unknown'), f"Longitude must be a number: {coords['lng']}")
    
    def add_error(self, filepath: Path, message: str):
        self.errors.append(f"{filepath}: {message}")
        self.stats['errors'] += 1
    
    def add_warning(self, filepath: Path, message: str):
        self.warnings.append(f"{filepath}: {message}")
        self.stats['warnings'] += 1
    
    def has_errors_for_file(self, filepath: Path) -> bool:
        return any(str(filepath) in e for e in self.errors)
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total files:     {self.stats['total']}")
        print(f"Valid:           {self.stats['valid']}")
        print(f"Errors:          {self.stats['errors']}")
        print(f"Warnings:        {self.stats['warnings']}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for err in self.errors[:20]:
                print(f"  - {err}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings[:20]:
                print(f"  - {warn}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate Macau event records')
    parser.add_argument('--published-only', action='store_true', help='Validate only records that pass publication policy')
    args = parser.parse_args()
    events_dir = Path(__file__).parent.parent / 'events'
    if not events_dir.exists():
        print(f"Events directory not found: {events_dir}")
        sys.exit(1)
    
    validator = EventValidator(events_dir, published_only=args.published_only)
    success = validator.validate_all()
    sys.exit(0 if success else 1)