"""Scraper modules for retrieving university rankings data."""

from .base_scraper import BaseScraper
from .rankings_scraper import RankingsScraper
from .selenium_rankings_scraper import SeleniumRankingsScraper
from .selenium_base_scraper import SeleniumBaseScraper
from .university_detail_scraper import UniversityDetailScraper

__all__ = [
    "BaseScraper",
    "RankingsScraper",
    "SeleniumRankingsScraper",
    "SeleniumBaseScraper",
    "UniversityDetailScraper",
]
