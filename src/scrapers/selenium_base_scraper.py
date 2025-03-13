"""Base Selenium scraper class for all Selenium-based scrapers."""

import logging
import time
from typing import Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from src.utils.exceptions import ScraperException

logger = logging.getLogger(__name__)


class SeleniumBaseScraper:
    """Base class for all Selenium-based scrapers with common functionality."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Selenium base scraper with configuration.

        Args:
            config: Scraper configuration dictionary
        """
        self.config = config
        self.driver = None
        self.headless = config.get("headless", True)
        self.page_load_timeout = config.get("page_load_timeout", 30)
        self.wait_timeout = config.get("wait_timeout", 10)
        self.delay = config.get("request_delay", 2)

    def _initialize_driver(self):
        """Initialize the Selenium WebDriver."""
        if self.driver:
            return

        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")

            # Add additional options for stability
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # Set user agent
            user_agent = self.config.get("user_agent")
            if user_agent:
                chrome_options.add_argument(f"--user-agent={user_agent}")

            # Initialize the Chrome WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)

            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise ScraperException(f"WebDriver initialization failed: {str(e)}")

    def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Make request using Selenium WebDriver.

        Args:
            url: URL to request
            headers: Optional request headers (Not directly used in Selenium,
                    but kept for interface compatibility)

        Returns:
            HTML content of the page after JavaScript execution

        Raises:
            ScraperException: If the request fails after retries
        """
        if self.driver is None:
            self._initialize_driver()

        max_retries = self.config.get("max_retries", 3)
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(f"Navigating to {url} with Selenium")
                self.driver.get(url)

                # Wait for page to load completely
                time.sleep(2)  # Initial pause to let JS start executing

                # Get the page source after JavaScript has executed
                html_content = self.driver.page_source

                # Respect the site's terms by adding delay between requests
                time.sleep(self.delay)

                return html_content

            except (WebDriverException, Exception) as e:
                retry_count += 1
                wait_time = 2**retry_count  # Exponential backoff
                logger.warning(
                    f"Selenium request failed ({e}). Retrying in {wait_time}s "
                    f"({retry_count}/{max_retries})"
                )
                time.sleep(wait_time)

                # Try to reinitialize the driver if there was an error
                try:
                    if self.driver:
                        self.driver.quit()
                    self.driver = None
                    self._initialize_driver()
                except Exception as re_init_error:
                    logger.error(f"Failed to reinitialize driver: {str(re_init_error)}")

        raise ScraperException(f"Failed to retrieve {url} after {max_retries} attempts")

    def __del__(self):
        """Clean up WebDriver resources on deletion."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.warning(f"Error closing WebDriver: {str(e)}")
