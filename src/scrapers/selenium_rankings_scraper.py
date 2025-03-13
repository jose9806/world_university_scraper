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

            # Navigate to the URL
            logger.info(f"Scraping rankings for year {year}, view {view}")
            self.driver.get(url)

            # Wait for page to initially load
            time.sleep(3)

            # Accept cookies if the dialog appears
            self._handle_cookie_consent()

            # Wait for the data table to load - the table might have a different ID,
            # so we're looking for any table with a specific class or within a specific container
            try:
                logger.info("Waiting for rankings table to load")

                # Wait for table - adjust the selector based on the actual page structure
                table = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "table.rankings-table, table.data-table, table#datatable-1",
                        )
                    )
                )

                logger.info("Rankings table found")

                # Scroll down to load all data (in case of lazy loading)
                self._scroll_to_load_all_data()

                # Get the final page source with all data loaded
                html_content = self.driver.page_source
                return html_content

            except TimeoutException:
                logger.warning("Timeout waiting for rankings table")
                # Even if we hit timeout, return whatever HTML we have - the parser can try to handle it
                return self.driver.page_source

        except Exception as e:
            logger.error(f"Error scraping rankings: {str(e)}")
            raise ScraperException(f"Failed to scrape rankings: {str(e)}")

    def _handle_cookie_consent(self):
        """Handle cookie consent dialog if it appears."""
        try:
            # Look for common cookie consent buttons
            # This needs to be adjusted based on the actual site's cookie consent implementation
            consent_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(text(), 'Accept') or contains(text(), 'I agree') or contains(@id, 'accept') or contains(@class, 'accept')]",
            )

            if consent_buttons:
                logger.info("Clicking cookie consent button")
                consent_buttons[0].click()
                time.sleep(1)  # Wait for dialog to disappear
        except Exception as e:
            logger.warning(f"Error handling cookie consent: {str(e)}")
            # Continue even if consent handling fails

    def _scroll_to_load_all_data(self):
        """Scroll down the page to trigger loading of all data."""
        try:
            # Get scroll height
            last_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )

            while True:
                # Scroll down to bottom
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )

                # Wait to load page
                time.sleep(2)

                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )
                if new_height == last_height:
                    # If heights are the same, we've reached the bottom
                    break
                last_height = new_height

            logger.info("Scrolled through page to load all content")
        except Exception as e:
            logger.warning(f"Error during scrolling: {str(e)}")
            # Continue even if scrolling fails

    def get_total_universities(self) -> int:
        """Get the total number of universities in the rankings.

        Returns:
            Total number of universities or 0 if unable to determine
        """
        try:
            # Look for elements that might contain the total count
            # This needs to be adjusted based on the actual page structure
            total_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".total-count, .results-count"
            )

            if total_elements:
                # Extract the number from text like "1,000 universities"
                import re

                text = total_elements[0].text
                match = re.search(r"(\d+(?:,\d+)*)", text)
                if match:
                    # Remove commas and convert to int
                    return int(match.group(1).replace(",", ""))

            # Fallback: Count table rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            return len(rows)

        except Exception as e:
            logger.warning(f"Error getting total universities count: {str(e)}")
            return 0
