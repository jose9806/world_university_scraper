"""Base scraper class for all scrapers."""

import logging
import time
from typing import Dict, Any, Optional

from requests.exceptions import RequestException

from ..utils.http import create_session, get_random_user_agent
from ..utils.exceptions import ScraperException

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all scrapers with common functionality."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize base scraper with configuration.

        Args:
            config: Scraper configuration dictionary
        """
        self.config = config
        self.session = create_session()
        self.delay = config.get("request_delay", 2)

    def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Make HTTP request with retry logic and delay.

        Args:
            url: URL to request
            headers: Optional request headers

        Returns:
            Response text content

        Raises:
            ScraperException: If the request fails after retries
        """
        if headers is None:
            headers = {"User-Agent": get_random_user_agent()}

        max_retries = self.config.get("max_retries", 3)
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(f"Making request to {url}")
                response = self.session.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                # Respect the site's terms by adding delay between requests
                time.sleep(self.delay)

                return response.text
            except RequestException as e:
                retry_count += 1
                wait_time = 2**retry_count  # Exponential backoff
                logger.warning(
                    f"Request failed ({e}). Retrying in {wait_time}s "
                    f"({retry_count}/{max_retries})"
                )
                time.sleep(wait_time)

        raise ScraperException(f"Failed to retrieve {url} after {max_retries} attempts")
