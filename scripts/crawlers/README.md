# Macau Events Wiki - Crawler Implementations

## Crawler Architecture

```
scripts/
├── crawl.py              # Main entry point
├── crawlers/
│   ├── __init__.py
│   ├── base.py           # BaseCrawler class
│   ├── macaotourism.py   # MGTO
│   ├── icm.py            # Cultural Affairs Bureau
│   ├── macaucci.py       # Macao Cultural Centre
│   ├── mam.py            # Macao Museum of Art
│   ├── library.py        # Public Library
│   ├── galaxymacau.py    # Galaxy Entertainment
│   ├── sands.py          # Sands China
│   ├── wynn.py           # Wynn Macau
│   ├── cityofdreams.py   # Melco Resorts
│   ├── mgm.py            # MGM China
│   ├── grandlisboa.py    # Grand Lisboa
│   └── venue_social.py   # Bars/venues via social media
├── validate.py
├── generate-index.py
└── requirements.txt
```

## CRAWLER REGISTRY

```python
# scripts/crawlers/__init__.py
from .macaotourism import MGTOCrawler
from .icm import ICMCrawler
from .macaucci import CCMCrawler
from .mam import MAMCrawler
from .library import LibraryCrawler
from .galaxymacau import GalaxyCrawler
from .sands import SandsCrawler
from .wynn import WynnCrawler
from .cityofdreams import CityOfDreamsCrawler
from .mgm import MGMCrawler
from .grandlisboa import GrandLisboaCrawler

CRAWL_REGISTRY = {
    # Tier 1 - Government (Daily 06:00 UTC)
    'macaotourism.gov.mo': MGTOCrawler,
    'icm.gov.mo': ICMCrawler,
    'macaucci.gov.mo': CCMCrawler,
    'mam.gov.mo': MAMCrawler,
    'library.gov.mo': LibraryCrawler,
    
    # Tier 2 - Casinos (Daily 07:00 UTC)
    'galaxymacau.com': GalaxyCrawler,
    'sandsresortsmacao.com': SandsCrawler,
    'wynnmacau.com': WynnCrawler,
    'cityofdreamsmacau.com': CityOfDreamsCrawler,
    'mgm.mo': MGMCrawler,
    'grandlisboahotels.com': GrandLisboaCrawler,
}

TIER_SOURCES = {
    '1': ['macaotourism.gov.mo', 'icm.gov.mo', 'macaucci.gov.mo', 'mam.gov.mo', 'library.gov.mo'],
    '2': ['galaxymacau.com', 'sandsresortsmacao.com', 'wynnresortsmacau.com', 'cityofdreamsmacau.com', 'mgm.mo', 'sjmresorts.com'],
    '3': ['fishermanswharf.com.mo'],
    '4': list(CRAWL_REGISTRY.keys()),  # All sources for monthly deep crawl
}

def get_crawlers_for_tier(tier: str, source: str = None):
    if source:
        return [CRAWL_REGISTRY[source]()]
    return [CRAWL_REGISTRY[s]() for s in TIER_SOURCES.get(tier, [])]
```