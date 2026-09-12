# Crawlers package
from .base import BaseCrawler, CrawledEvent, WikiWriter
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
from .fishermanswharf import FishermansWharfCrawler
from .londoner import LondonerCrawler
from .lisboeta import LisboetaCrawler

# Tier 3 — venue/nightlife (weekly)
from .sky21 import Sky21Crawler
from .cubamacao import CubaMacaoCrawler
from .bobbar import BobBarCrawler
from .theden import TheDenCrawler
from .laferrari import LaFerrariCrawler

# Tier 3 — media (weekly)
from .centralmacau import CentralMacauCrawler
from .macaunews import MacauNewsCrawler

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
    'wynnresortsmacau.com': WynnCrawler,
    'cityofdreamsmacau.com': CityOfDreamsCrawler,
    'mgm.mo': MGMCrawler,
    'sjmresorts.com': GrandLisboaCrawler,
    'londonermacao.com': LondonerCrawler,
    'lisboetamacau.com': LisboetaCrawler,

    # Tier 3 — Independent venues & nightlife (Weekly)
    'fishermanswharf.com.mo': FishermansWharfCrawler,
    'sky21.com.mo': Sky21Crawler,          # actual domain: skyconceptmacau.com
    'cubamacao.com': CubaMacaoCrawler,
    'bobbarmacau.com': BobBarCrawler,
    'thedenbar.com': TheDenCrawler,
    'laferrari.com.mo': LaFerrariCrawler,

    # Tier 3 — Media / Lifestyle (Weekly)
    'centralmacau.com': CentralMacauCrawler,
    'macaunews.mo': MacauNewsCrawler,
}

TIER_SOURCES = {
    '1': ['macaotourism.gov.mo', 'icm.gov.mo', 'macaucci.gov.mo', 'mam.gov.mo', 'library.gov.mo'],
    '2': ['galaxymacau.com', 'sandsresortsmacao.com', 'wynnresortsmacau.com', 'cityofdreamsmacau.com',
          'mgm.mo', 'sjmresorts.com', 'londonermacao.com', 'lisboetamacau.com'],
    '3': ['fishermanswharf.com.mo', 'sky21.com.mo', 'cubamacao.com', 'bobbarmacau.com',
          'thedenbar.com', 'laferrari.com.mo', 'centralmacau.com', 'macaunews.mo'],
    '4': list(CRAWL_REGISTRY.keys()),  # All sources for monthly deep crawl
}

def get_crawlers_for_tier(tier: str, source: str = None, session=None):
    if source:
        if source in CRAWL_REGISTRY:
            return [CRAWL_REGISTRY[source]]
        else:
            raise ValueError(f"Unknown source: {source}")
    return [CRAWL_REGISTRY[s] for s in TIER_SOURCES.get(tier, []) if s in CRAWL_REGISTRY]

__all__ = [
    'BaseCrawler',
    'CrawledEvent',
    'WikiWriter',
    'CRAWL_REGISTRY',
    'TIER_SOURCES',
    'get_crawlers_for_tier',
]
