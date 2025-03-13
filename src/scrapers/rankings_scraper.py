"""Scraper for THE World University Rankings."""

import logging
from typing import Dict, Any

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RankingsScraper(BaseScraper):
    """Scraper for THE World University Rankings website."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize rankings scraper with configuration.

        Args:
            config: Scraper configuration dictionary
        """
        super().__init__(config)
        self.rankings_url = config["url"]

    def scrape(self) -> str:
        """Scrape the THE World University Rankings page.

        Returns:
            Raw HTML content of the rankings page
        """
        logger.info("Scraping rankings data from THE website")

        html_content = self._make_request(self.rankings_url)

        logger.info(f"Successfully scraped {len(html_content)} bytes of data")
        return html_content
