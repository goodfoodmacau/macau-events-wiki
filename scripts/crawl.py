#!/usr/bin/env python3
"""
Main Crawl Entry Point
Runs crawlers for specified tier/source and writes to wiki.
"""

import asyncio
import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from crawlers import get_crawlers_for_tier, WikiWriter
from translations import ensure_event_translations, missing_translation_languages


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('macau-events-crawl')


async def run_crawler(crawler_class, session, wiki_writer, dry_run=False):
    """Run a single crawler and process results"""
    crawler = crawler_class(session)
    logger.info(f"Starting crawl for {crawler.name}")
    
    try:
        events = await crawler.fetch_all()
        logger.info(f"{crawler.name}: Found {len(events)} events")
        
        new_count = 0
        updated_count = 0
        
        for event in events:
            existing = wiki_writer.read_existing(event)
            if existing and existing.get('translations'):
                # Translation is curated wiki data. Seed the freshly extracted
                # record from the event file, then fill only missing languages.
                event.translations = existing['translations']

            content_changed = not existing or event.crawl_hash != existing.get('crawl_hash', '')
            translation_needed = bool(missing_translation_languages(event))
            if existing and not content_changed and (not translation_needed or dry_run):
                logger.debug(f"  Unchanged: {event.title[:60]}")
                continue

            if not dry_run:
                translations_ready = await ensure_event_translations(event, session)
                if not translations_ready:
                    missing = ', '.join(missing_translation_languages(event))
                    logger.warning(f"  Translation incomplete ({missing}); record will not pass publication: {event.title[:60]}")
                wiki_writer.write_event(event, is_new=not bool(existing))

            if existing:
                updated_count += 1
                logger.info(f"  Updated: {event.title[:60]}")
            else:
                new_count += 1
                logger.info(f"  New: {event.title[:60]}")
        
        return {
            'source': crawler.name,
            'found': len(events),
            'new': new_count,
            'updated': updated_count,
            'errors': len(crawler.errors)
        }
        
    except Exception as e:
        logger.error(f"{crawler.name} failed: {e}")
        return {
            'source': crawler.name,
            'found': 0,
            'new': 0,
            'updated': 0,
            'errors': 1,
            'error_msg': str(e)
        }


async def main():
    parser = argparse.ArgumentParser(description='Macau Events Wiki Crawler')
    parser.add_argument('--tier', choices=['1', '2', '3', '4', 'all'], default='all',
                        help='Crawl tier to run')
    parser.add_argument('--source', help='Specific source key to crawl')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to wiki')
    parser.add_argument('--wiki-root', default='.', help='Wiki root directory')
    args = parser.parse_args()
    
    wiki_root = Path(args.wiki_root).resolve()
    wiki_writer = WikiWriter(str(wiki_root))
    
    # Run crawlers
    import aiohttp
    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Determine crawlers to run
        if args.source:
            # --source should override tier and run exactly one crawler.
            crawler_classes = get_crawlers_for_tier('1', source=args.source, session=session)
        elif args.tier == 'all':
            crawler_classes = []
            for tier in ['1', '2', '3', '4']:
                crawler_classes.extend(get_crawlers_for_tier(tier, session=session))
        else:
            crawler_classes = get_crawlers_for_tier(args.tier, session=session)
        
        if not crawler_classes:
            logger.error("No crawlers found for specified tier/source")
            sys.exit(1)
        
        logger.info(f"Running {len(crawler_classes)} crawlers for tier {args.tier}")
        
        results = []
        for crawler_class in crawler_classes:
            result = await run_crawler(crawler_class, session, wiki_writer, args.dry_run)
            results.append(result)
    
    # Summary
    total_found = sum(r['found'] for r in results)
    total_new = sum(r['new'] for r in results)
    total_updated = sum(r['updated'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    
    logger.info(f"\n{'='*50}")
    logger.info(f"CRAWL SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Sources:      {len(results)}")
    logger.info(f"Events found: {total_found}")
    logger.info(f"New:          {total_new}")
    logger.info(f"Updated:      {total_updated}")
    logger.info(f"Errors:       {total_errors}")
    
    for r in results:
        status = "✓" if r['errors'] == 0 else "✗"
        logger.info(f"  {status} {r['source']}: {r['found']} found, {r['new']} new, {r['updated']} updated")
        if 'error_msg' in r:
            logger.info(f"    Error: {r['error_msg']}")
    
    # Generate indexes if not dry run
    if not args.dry_run and (total_new > 0 or total_updated > 0):
        logger.info("Generating indexes...")
        # Import and run index generator
        sys.path.insert(0, str(wiki_root / 'scripts'))
        from generate_index import IndexGenerator
        
        generator = IndexGenerator(wiki_root / 'events', wiki_root)
        generator.run()
        
        # Commit changes
        msg = f"crawl: tier-{args.tier} {datetime.now().strftime('%Y-%m-%d')} - {total_new} new, {total_updated} updated"
        wiki_writer.commit_changes(msg)
    
    logger.info("Done!")
    
    # Exit with error code if any errors
    if total_errors > 0:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())