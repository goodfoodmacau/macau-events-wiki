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
        lang = 'en'
        cal_url = f"{crawler.base_url}/{lang}/events/calendar"
        print(f"Fetching: {cal_url}")
        try:
            html = await crawler.fetch_html(cal_url)
            print(f"Got HTML length: {len(html)}")
            soup = crawler._soup(html)
            print(f"Soup created successfully")
            # Find all event detail links - m-calendar__item ARE the <a> tags
            items = soup.select('a.m-calendar__item[href*="/events/calendar/"]')
            print(f"Calendar items found: {len(items)}")
            for item in items[:3]:
                print(f'  {item.get("href")}')
        except Exception as e:
            traceback.print_exc()

asyncio.run(test())