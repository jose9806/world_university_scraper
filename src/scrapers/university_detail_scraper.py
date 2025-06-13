"""Scraper for individual university detail pages on THE."""

import logging
import time
from typing import Dict, Any, List

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .selenium_base_scraper import SeleniumBaseScraper


logger = logging.getLogger(__name__)


class UniversityDetailScraper(SeleniumBaseScraper):
    """Scraper for individual university detail pages using Selenium."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the university detail scraper.

        Args:
            config: Scraper configuration dictionary
        """
        super().__init__(config)
        self.base_delay = config.get(
            "university_delay", 3
        )  # Longer delay between university pages

    def scrape_university_details(
        self, university_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Scrape details for multiple universities.

        Args:
            university_urls: List of university detail URLs

        Returns:
            List of dictionaries containing university details

        Raises:
            ScraperException: If scraping fails
        """
        if not university_urls:
            logger.warning("No university URLs provided")
            return []

        results = []

        try:
            self._initialize_driver()

            for i, url in enumerate(university_urls, 1):
                try:
                    logger.info(
                        f"Scraping university {i}/{len(university_urls)}: {url}"
                    )

                    university_data = self._scrape_single_university(url)
                    if university_data:
                        results.append(university_data)

                    # Add delay between universities to be respectful
                    if i < len(university_urls):
                        time.sleep(self.base_delay)

                except Exception as e:
                    logger.error(f"Failed to scrape university {url}: {str(e)}")
                    continue

        finally:
            if self.driver:
                self.driver.quit()

        logger.info(
            f"Successfully scraped {len(results)} out of {len(university_urls)} universities"
        )
        return results

    def _scrape_single_university(self, url: str) -> Dict[str, Any]:
        """Scrape details for a single university.

        Args:
            url: University detail page URL

        Returns:
            Dictionary containing university details
        """
        if not url:
            logger.warning("Empty URL provided")
            return {}

        try:
            # Navigate to the university page
            self.driver.get(url)
            time.sleep(2)  # Let the page load

            # Handle cookie consent if it appears
            self._handle_cookie_consent()

            # Wait for main content to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "profile-header"))
                )
            except TimeoutException:
                logger.warning(f"Profile header not found for {url}")

            # Extract university data
            university_data = {
                "url": url,
                "name": self._extract_university_name(),
                "ranking_data": self._extract_ranking_data(),
                "key_stats": self._extract_key_stats(),
                "subjects": self._extract_subjects_data(),
                "scrape_timestamp": time.time(),
            }

            return university_data

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "error": str(e), "scrape_timestamp": time.time()}

    def _extract_university_name(self) -> str:
        """Extract university name from the page."""
        try:
            # Try multiple selectors for the university name
            selectors = [
                "h1.profile-header__title",
                "h1.hero-title",
                ".profile-header h1",
                "h1",
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text.strip():
                        return element.text.strip()
                except NoSuchElementException:
                    continue

            return "Unknown"

        except Exception as e:
            logger.warning(f"Failed to extract university name: {str(e)}")
            return "Unknown"

    def _extract_ranking_data(self) -> Dict[str, Any]:
        """Extract ranking information from ranking cards/boxes."""
        ranking_data = {}

        try:
            # Look for ranking cards or similar containers
            ranking_selectors = [
                ".ranking-card",
                ".rank-card",
                ".profile-ranking",
                ".university-ranking",
            ]

            for selector in ranking_selectors:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for card in cards:
                        rank_info = self._parse_ranking_card(card)
                        if rank_info:
                            ranking_data.update(rank_info)
                except NoSuchElementException:
                    continue

            # If no cards found, try to find individual ranking elements
            if not ranking_data:
                ranking_data = self._extract_individual_rankings()

        except Exception as e:
            logger.warning(f"Failed to extract ranking data: {str(e)}")

        return ranking_data

    def _parse_ranking_card(self, card_element) -> Dict[str, Any]:
        """Parse a single ranking card element."""
        try:
            card_data = {}

            # Extract ranking title/type
            title_elem = card_element.find_element(
                By.CSS_SELECTOR, ".card-title, h3, h4, .ranking-title"
            )
            if title_elem:
                title = title_elem.text.strip()

            # Extract rank number
            rank_elem = card_element.find_element(
                By.CSS_SELECTOR, ".rank, .ranking-number, .position"
            )
            if rank_elem:
                rank = rank_elem.text.strip()
                card_data[f"{title.lower().replace(' ', '_')}_rank"] = rank

            # Extract year if available
            year_elem = card_element.find_element(
                By.CSS_SELECTOR, ".year, .ranking-year"
            )
            if year_elem:
                card_data[f"{title.lower().replace(' ', '_')}_year"] = (
                    year_elem.text.strip()
                )

            return card_data

        except NoSuchElementException:
            return {}

    def _extract_individual_rankings(self) -> Dict[str, Any]:
        """Extract ranking data from individual elements when cards are not available."""
        ranking_data = {}

        try:
            # Common patterns for ranking information
            rank_patterns = [
                {"selector": ".world-rank", "key": "world_rank"},
                {"selector": ".overall-rank", "key": "overall_rank"},
                {"selector": ".reputation-rank", "key": "reputation_rank"},
            ]

            for pattern in rank_patterns:
                try:
                    element = self.driver.find_element(
                        By.CSS_SELECTOR, pattern["selector"]
                    )
                    ranking_data[pattern["key"]] = element.text.strip()
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"No individual rankings found: {str(e)}")

        return ranking_data

    def _extract_key_stats(self) -> Dict[str, Any]:
        """Extract key statistics from the university page."""
        stats = {}

        try:
            # Look for key stats section
            stats_selectors = [
                ".key-stats",
                ".university-stats",
                ".profile-stats",
                ".stats-container",
            ]

            for selector in stats_selectors:
                try:
                    stats_container = self.driver.find_element(
                        By.CSS_SELECTOR, selector
                    )
                    stats = self._parse_stats_container(stats_container)
                    if stats:
                        break
                except NoSuchElementException:
                    continue

            # If no dedicated stats section, look for individual stat elements
            if not stats:
                stats = self._extract_individual_stats()

        except Exception as e:
            logger.warning(f"Failed to extract key stats: {str(e)}")

        return stats

    def _parse_stats_container(self, container) -> Dict[str, Any]:
        """Parse statistics from a stats container element."""
        stats = {}

        try:
            # Look for stat items within the container
            stat_items = container.find_elements(
                By.CSS_SELECTOR, ".stat-item, .key-stat, dt, .metric"
            )

            for item in stat_items:
                stat_name, stat_value = self._parse_stat_item(item)
                if stat_name and stat_value:
                    stats[stat_name] = stat_value

        except Exception as e:
            logger.debug(f"Failed to parse stats container: {str(e)}")

        return stats

    def _parse_stat_item(self, item) -> tuple[str, str]:
        """Parse an individual statistic item."""
        try:
            # Try different patterns for stat name and value
            name = ""
            value = ""

            # Pattern 1: Name and value in separate elements
            try:
                name_elem = item.find_element(By.CSS_SELECTOR, ".stat-name, .label, dt")
                value_elem = item.find_element(
                    By.CSS_SELECTOR, ".stat-value, .value, dd"
                )
                name = name_elem.text.strip()
                value = value_elem.text.strip()
            except NoSuchElementException:
                # Pattern 2: Combined text that needs to be split
                text = item.text.strip()
                if ":" in text:
                    parts = text.split(":", 1)
                    name = parts[0].strip()
                    value = parts[1].strip()

            return name, value

        except Exception:
            return "", ""

    def _extract_individual_stats(self) -> Dict[str, Any]:
        """Extract stats from individual elements when no container is found."""
        stats = {}

        try:
            # Common stat patterns
            stat_patterns = [
                {"selector": ".student-count", "key": "total_students"},
                {"selector": ".faculty-count", "key": "faculty_count"},
                {"selector": ".established", "key": "established"},
                {"selector": ".campus-size", "key": "campus_size"},
            ]

            for pattern in stat_patterns:
                try:
                    element = self.driver.find_element(
                        By.CSS_SELECTOR, pattern["selector"]
                    )
                    stats[pattern["key"]] = element.text.strip()
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"No individual stats found: {str(e)}")

        return stats

    def _extract_subjects_data(self) -> List[Dict[str, Any]]:
        """Extract subject rankings and information."""
        subjects = []

        try:
            # Look for subjects section
            subjects_selectors = [
                ".subjects-section",
                ".subject-rankings",
                ".disciplines",
                ".academic-areas",
            ]

            for selector in subjects_selectors:
                try:
                    subjects_container = self.driver.find_element(
                        By.CSS_SELECTOR, selector
                    )
                    subjects = self._parse_subjects_container(subjects_container)
                    if subjects:
                        break
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.warning(f"Failed to extract subjects data: {str(e)}")

        return subjects

    def _parse_subjects_container(self, container) -> List[Dict[str, Any]]:
        """Parse subjects from a subjects container."""
        subjects = []

        try:
            # Look for individual subject items
            subject_items = container.find_elements(
                By.CSS_SELECTOR, ".subject-item, .discipline, .subject-rank"
            )

            for item in subject_items:
                subject_data = self._parse_subject_item(item)
                if subject_data:
                    subjects.append(subject_data)

        except Exception as e:
            logger.debug(f"Failed to parse subjects container: {str(e)}")

        return subjects

    def _parse_subject_item(self, item) -> Dict[str, Any]:
        """Parse an individual subject item."""
        try:
            subject_data = {}

            # Extract subject name
            name_elem = item.find_element(
                By.CSS_SELECTOR, ".subject-name, .discipline-name, h3, h4"
            )
            if name_elem:
                subject_data["name"] = name_elem.text.strip()

            # Extract subject rank
            rank_elem = item.find_element(
                By.CSS_SELECTOR, ".subject-rank, .rank, .position"
            )
            if rank_elem:
                subject_data["rank"] = rank_elem.text.strip()

            # Extract subject score if available
            score_elem = item.find_element(By.CSS_SELECTOR, ".subject-score, .score")
            if score_elem:
                subject_data["score"] = score_elem.text.strip()

            return subject_data if subject_data else {}

        except NoSuchElementException:
            return {}

    def _handle_cookie_consent(self):
        """Handle cookie consent dialog if it appears."""
        try:
            # Common cookie consent selectors
            consent_selectors = [
                "#onetrust-accept-btn-handler",
                ".cookie-consent-accept",
                ".accept-cookies",
                "[data-cookieconsent='accept']",
            ]

            for selector in consent_selectors:
                try:
                    consent_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    consent_btn.click()
                    logger.debug("Cookie consent accepted")
                    time.sleep(1)
                    return
                except TimeoutException:
                    continue

        except Exception as e:
            logger.debug(f"No cookie consent found or failed to handle: {str(e)}")
