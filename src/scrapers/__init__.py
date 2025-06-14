"""Scraper modules for retrieving university rankings data."""

# Import main scraper classes to expose them at the package level
from .base_scraper import BaseScraper
from .rankings_scraper import RankingsScraper
from .selenium_rankings_scraper import SeleniumRankingsScraper
from .selenium_base_scraper import SeleniumBaseScraper
from .university_detail_scraper import UniversityDetailScraper

# Expose these classes for direct import from the package
__all__ = [
    "BaseScraper",
    "RankingsScraper",
    "SeleniumRankingsScraper",
    "SeleniumBaseScraper",
    "UniversityDetailScraper",
]
