"""Specialized Selenium scraper for THE World University Rankings."""

import logging
import time
from typing import Dict, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.scrapers.selenium_base_scraper import SeleniumBaseScraper
from src.utils.exceptions import ScraperException

logger = logging.getLogger(__name__)


class SeleniumRankingsScraper(SeleniumBaseScraper):
    """Specialized scraper for THE World University Rankings using Selenium."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the rankings scraper with configuration.

        Args:
            config: Scraper configuration dictionary
        """
        super().__init__(config)
        self.base_url = config.get(
            "base_url", "https://www.timeshighereducation.com/world-university-rankings"
        )

    def scrape_rankings(self, year="2025", view="reputation") -> str:
        """Scrape university rankings data for a specific year and view.

        Args:
            year: The ranking year to scrape
            view: The ranking view/filter to use

        Returns:
            HTML content containing the rankings table

        Raises:
            ScraperException: If scraping fails
        """
        url = f"{self.base_url}/{year}/world-ranking/results?view={view}"

        try:
            self._initialize_driver()
            if self.driver:
                logger.info(f"Scraping rankings for year {year}, view {view}")
                self.driver.get(url)

                time.sleep(3)

                self._handle_cookie_consent()

                try:
                    logger.info("Waiting for rankings table to load")

                    _ = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "table.rankings-table, table.data-table, table#datatable-1",
                            )
                        )
                    )

                    logger.info("Rankings table found")

                    self._scroll_to_load_all_data()

                    html_content = self.driver.page_source
                    return html_content

                except TimeoutException:
                    logger.warning("Timeout waiting for rankings table")

                    return self.driver.page_source
            else:
                logger.info(
                    f"Scraping rankings for year had an issue initializing the driver"
                )

        except Exception as e:
            logger.error(f"Error scraping rankings: {str(e)}")
            raise ScraperException(f"Failed to scrape rankings: {str(e)}")

    def _handle_cookie_consent(self):
        """Handle cookie consent dialog if it appears."""
        try:
            if self.driver:
                consent_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(@id, 'accept') or contains(@class, 'accept')]",
                )

                if consent_buttons:
                    logger.info("Clicking cookie consent button")
                    consent_buttons[0].click()
                    time.sleep(1)
            else:
                logger.info(
                    f"Scraping rankings for year had an issue initializing the driver"
                )
        except Exception as e:
            logger.warning(f"Error handling cookie consent: {str(e)}")

    def _scroll_to_load_all_data(self):
        """Scroll down the page to trigger loading of all data."""
        try:
            if self.driver:
                last_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )

                while True:

                    self.driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )

                    time.sleep(2)

                    new_height = self.driver.execute_script(
                        "return document.body.scrollHeight"
                    )
                    if new_height == last_height:

                        break
                    last_height = new_height

                logger.info("Scrolled through page to load all content")
            else:
                logger.info(
                    f"Scraping rankings for year had an issue initializing the driver"
                )
        except Exception as e:
            logger.warning(f"Error during scrolling: {str(e)}")

    def get_total_universities(self) -> int:
        """Get the total number of universities in the rankings.

        Returns:
            Total number of universities or 0 if unable to determine
        """
        try:
            if self.driver:
                total_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, ".total-count, .results-count"
                )

                if total_elements:

                    import re

                    text = total_elements[0].text
                    match = re.search(r"(\d+(?:,\d+)*)", text)
                    if match:

                        return int(match.group(1).replace(",", ""))

                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                return len(rows)
            else:
                logger.info(
                    f"Scraping rankings for year had an issue initializing the driver"
                )

        except Exception as e:
            logger.warning(f"Error getting total universities count: {str(e)}")
            return 0
