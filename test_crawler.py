import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json

async def test():
    connector = aiohttp.TCPConnector(limit=5, ssl=False)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        url = 'https://www.macaotourism.gov.mo/en/events/calendar'
        async with session.get(url) as resp:
            print(f'Status: {resp.status}')
            html = await resp.text()
            print(f'Length: {len(html)}')
            soup = BeautifulSoup(html, 'lxml')
            # Check for JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                content = script.string
                if content:
                    print(f'JSON-LD found (first 500 chars): {content[:500]}')
                    try:
                        data = json.loads(content)
                        print(f'Parsed JSON-LD type: {type(data)}')
                        if isinstance(data, list):
                            for d in data:
                                print(f'  Item type: {d.get("@type")}')
                        elif isinstance(data, dict):
                            print(f'  Item type: {data.get("@type")}')
                    except json.JSONDecodeError as e:
                        print(f'JSON decode error: {e}')
                else:
                    print('JSON-LD: empty string')
            # Check for m-calendar__item
            items = soup.select('a.m-calendar__item[href*="/events/calendar/"]')
            print(f'Calendar items: {len(items)}')
            for item in items[:3]:
                print(f'  {item.get("href")}')

asyncio.run(test())