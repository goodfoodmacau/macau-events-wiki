import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import sys
import traceback
sys.path.insert(0, '/Users/besa/macau-events-wiki/scripts')
from crawlers.macaotourism import MGTOCrawler

async def test():
    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        crawler = MGTOCrawler(session)
        try:
            urls = await crawler.fetch_list_urls()
            print(f'Found {len(urls)} URLs:')
            for url in urls[:10]:
                print(f'  {url}')
        except Exception as e:
            traceback.print_exc()

asyncio.run(test())