#!/usr/bin/env python3
import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
from publication import assess_event
from translations import REQUIRED_LANGUAGES, ensure_event_translations, has_complete_translations


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return False
    def raise_for_status(self): return None
    async def json(self): return self.payload


class FakeSession:
    def __init__(self, blocks): self.blocks = blocks
    def post(self, *_, **__):
        return FakeResponse({"choices": [{"message": {"content": json.dumps(self.blocks, ensure_ascii=False)}}]})


class TranslationTests(unittest.TestCase):
    def test_complete_translation_blocks_are_required_for_publication(self):
        base = {
            "title": "Official event", "description": "Description", "source_language": "en",
            "start_date": "2099-01-01", "end_date": "2099-01-02", "venue_name": "Venue",
            "address": "Macau", "organizer": "Organizer", "source": "mam.gov.mo",
            "source_url": "https://mam.gov.mo/event",
        }
        self.assertEqual(assess_event(base)["publication_status"], "review")
        base["translations"] = {lang: {
            "title": "Title", "description": "Description", "practical_info": "Official details",
            "translation_status": "machine",
        } for lang in REQUIRED_LANGUAGES}
        self.assertEqual(assess_event(base)["publication_status"], "published")

    def test_ingestion_stores_all_languages_under_the_event(self):
        event = SimpleNamespace(
            title="Macau event", description="A factual description.", source_language="en",
            ticket_info="MOP 100", translations={},
        )
        blocks = {lang: {
            "title": f"{lang} title", "description": f"{lang} description",
            "practical_info": f"{lang} practical",
        } for lang in REQUIRED_LANGUAGES if lang != "en"}
        old = __import__('os').environ.get('MACAU_AI_BASE_URL')
        __import__('os').environ['MACAU_AI_BASE_URL'] = 'http://translator.test'
        try:
            ready = asyncio.run(ensure_event_translations(event, FakeSession(blocks)))
        finally:
            if old is None: __import__('os').environ.pop('MACAU_AI_BASE_URL', None)
            else: __import__('os').environ['MACAU_AI_BASE_URL'] = old
        self.assertTrue(ready)
        self.assertTrue(has_complete_translations(event))
        self.assertEqual(set(event.translations), set(REQUIRED_LANGUAGES))
        self.assertEqual(event.translations['en']['translation_status'], 'source')
        self.assertEqual(event.translations['pt']['translation_status'], 'machine')


if __name__ == '__main__':
    unittest.main()
