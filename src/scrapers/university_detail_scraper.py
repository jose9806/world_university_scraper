"""Scraper for individual university detail pages on THE."""

import logging
import time
import re
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
            time.sleep(3)  # Increased wait time to ensure page loads completely

            # Handle cookie consent if it appears
            self._handle_cookie_consent()

            # Wait for main content to load with updated selector
            try:
                WebDriverWait(self.driver, 15).until(  # Increased timeout
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[data-testid='profile-header']")
                    )
                )
                logger.info("Profile header loaded successfully")
            except TimeoutException:
                logger.warning(f"Profile header not found for {url}, continuing anyway")

            # Additional wait for dynamic content
            time.sleep(2)

            # Extract university data
            university_data = {
                "url": url,
                "name": self._extract_university_name(),
                "ranking_data": self._extract_ranking_data(),
                "key_stats": self._extract_key_stats(),
                "subjects": self._extract_subjects_data(),
                "scrape_timestamp": time.time(),
            }

            # Log success with data summary
            logger.info(
                f"Extracted data for {university_data['name']}: "
                + f"Rankings: {len(university_data['ranking_data'])}, "
                + f"Stats: {len(university_data['key_stats'])}, "
                + f"Subjects: {len(university_data['subjects'])}"
            )

            return university_data

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {"url": url, "error": str(e), "scrape_timestamp": time.time()}

    def _extract_university_name(self) -> str:
        """Extract university name from the page."""
        try:
            # Updated selectors for the university name
            selectors = [
                "h1.css-y89yc2",  # Primary university name selector
                "h1[data-testid='institution-title']",
                "[data-testid='institution-page-header'] h1",
                "div.css-ejuz3m h1",
                "h1",  # Fallback
            ]

            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text.strip():
                        name = element.text.strip()
                        return name
                except NoSuchElementException:
                    continue

            return "Unknown"

        except Exception as e:
            logger.warning(f"Failed to extract university name: {str(e)}")
            return "Unknown"

    def _extract_ranking_data(self) -> Dict[str, Any]:
        """Extract comprehensive ranking information from all ranking sections."""
        ranking_data = {}

        try:
            logger.info("Extracting ranking data")

            # 1. First capture the main ranking metrics from the chart/score section
            # These are the items like "Overall", "Teaching", "Research Environment", etc.
            main_ranking_section = self._get_main_ranking_section()
            if main_ranking_section:
                logger.info("Found main ranking section")
                main_rankings = self._extract_main_rankings(main_ranking_section)
                ranking_data.update(main_rankings)
                logger.info(f"Extracted {len(main_rankings)} main ranking metrics")

            # 2. Get all the ranking cards showing positions (1st, 2nd, 3rd, etc.)
            rank_position_cards = self._get_ranking_position_cards()
            position_rankings = self._extract_ranking_positions(rank_position_cards)
            ranking_data.update(position_rankings)
            logger.info(f"Extracted {len(position_rankings)} ranking position cards")

            # 3. Look for any other ranking data we might have missed
            additional_rankings = self._extract_additional_rankings()
            ranking_data.update(additional_rankings)

            # Log overall extraction results
            logger.info(f"Extracted total of {len(ranking_data)} ranking metrics")

            return ranking_data

        except Exception as e:
            logger.warning(f"Failed to extract ranking data: {str(e)}")
            return {}

    def _get_main_ranking_section(self):
        """Get the main ranking section with scores."""
        try:
            # Try multiple selectors to find the main ranking section
            selectors = [
                # Section showing the ranking bars with scores
                "div.css-1heidyz",
                "div[data-testid='RankingOverviewChart']",
                # Fallbacks
                "div.css-ejuz3m > div:nth-child(1)",
                "div:has(> div > span.barlabel-text)",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        return elements[0]
                except NoSuchElementException:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Failed to get main ranking section: {str(e)}")
            return None

    def _extract_main_rankings(self, section) -> Dict[str, Any]:
        """Extract rankings from the main chart section with score bars."""
        rankings = {}

        if not section:
            return rankings

        try:
            # Look for pairs of labels and scores
            # Based on the image, each ranking metric has:
            # 1. A label (e.g., "Overall", "Teaching")
            # 2. A score (e.g., "98.5", "96.8")

            # First try to find structured rows
            ranking_rows = section.find_elements(
                By.CSS_SELECTOR, "div.css-1heidyz > div"
            )

            if not ranking_rows or len(ranking_rows) < 3:  # If no structured rows found
                # Try another approach - look for the labels and scores directly
                labels = section.find_elements(
                    By.CSS_SELECTOR,
                    ".barlabel-text, div[role='rowheader'], div.css-1kroxql",
                )
                scores = section.find_elements(
                    By.CSS_SELECTOR, ".barlabel-score, div[role='cell']"
                )

                # Match labels with scores if possible
                for i, label in enumerate(labels):
                    if i < len(scores):
                        label_text = label.text.strip()
                        score_text = scores[i].text.strip()

                        if label_text and score_text:
                            key = self._clean_ranking_key(label_text)
                            rankings[f"{key}_score"] = score_text
            else:
                # Process structured rows
                for row in ranking_rows:
                    # Each row might contain the label and score
                    row_text = row.text.strip()
                    if row_text:
                        # Try to separate label and score
                        parts = row_text.split("\n")
                        if len(parts) >= 2:
                            label = parts[0].strip()
                            score = parts[1].strip()

                            if label and score:
                                key = self._clean_ranking_key(label)
                                rankings[f"{key}_score"] = score

            # If we still have no rankings, try one more approach with JS paths
            if not rankings:
                # Extract all text from the section to look for patterns
                section_text = section.text

                # Look for common patterns in the text like "Overall 98.5" or "Teaching 96.8"
                patterns = [
                    (r"Overall\s+(\d+\.?\d*)", "overall"),
                    (r"Teaching\s+(\d+\.?\d*)", "teaching"),
                    (r"Research\s+(\d+\.?\d*)", "research"),
                    (r"Research Environment\s+(\d+\.?\d*)", "research_environment"),
                    (r"Research Quality\s+(\d+\.?\d*)", "research_quality"),
                    (r"Industry\s+(\d+\.?\d*)", "industry"),
                    (r"International Outlook\s+(\d+\.?\d*)", "international_outlook"),
                ]

                for pattern, key in patterns:
                    match = re.search(pattern, section_text)
                    if match:
                        rankings[f"{key}_score"] = match.group(1)

            return rankings
        except Exception as e:
            logger.debug(f"Failed to extract main rankings: {str(e)}")
            return {}

    def _get_ranking_position_cards(self) -> List:
        """Get all ranking position cards."""
        cards = []

        try:
            # Based on the image, there are cards showing subject rankings with position badges (1st, 2nd, 3rd, etc.)
            card_selectors = [
                "div.css-q24je2",  # Cards container
                "div.css-ze6z4k",  # Individual cards
                "div.css-ivje2h",  # Alternative card class
                "div[role='tab']",  # Tabs that might contain ranking info
                "div.chakra-card",  # Generic chakra card class
            ]

            for selector in card_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        cards.extend(elements)
                except NoSuchElementException:
                    continue

            logger.debug(f"Found {len(cards)} potential ranking position cards")
            return cards

        except Exception as e:
            logger.debug(f"Failed to get ranking position cards: {str(e)}")
            return []

    def _extract_ranking_positions(self, cards) -> Dict[str, Any]:
        """Extract ranking positions from cards."""
        rankings = {}

        if not cards:
            return rankings

        try:
            for card in cards:
                try:
                    card_text = card.text.strip()

                    # Skip empty cards
                    if not card_text:
                        continue

                    # Extract data from the card
                    # Look for ranking category (e.g., World University Rankings 2025) and position (e.g., 1st)
                    lines = card_text.split("\n")

                    if len(lines) >= 2:
                        category = lines[0].strip()
                        position = None

                        # Look for position indicator (could be 1st, 2nd, 3rd, etc.)
                        for line in lines[1:]:
                            position_match = re.search(r"(\d+(?:st|nd|rd|th))", line)
                            if position_match:
                                position = position_match.group(1)
                                break

                        if category and position:
                            # Clean and standardize the category name for the key
                            key = self._clean_ranking_key(category)
                            # Remove suffixes like st, nd, rd, th from position
                            clean_position = re.sub(r"(st|nd|rd|th)$", "", position)
                            rankings[f"{key}_rank"] = clean_position
                except Exception as e:
                    logger.debug(f"Failed to process ranking card: {str(e)}")
                    continue

            return rankings
        except Exception as e:
            logger.debug(f"Failed to extract ranking positions: {str(e)}")
            return {}

    def _extract_additional_rankings(self) -> Dict[str, Any]:
        """Extract any additional ranking data we might have missed."""
        rankings = {}

        try:
            # Look for ranking information in the main data sections
            # This is a backup approach to catch anything we missed
            selectors = [
                "div[data-testid='keyStats']",
                "div.css-ejuz3m",
                "div.css-1heidyz",
            ]

            # Keywords that indicate ranking information
            ranking_keywords = ["rank", "ranking", "position", "score", "#"]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        element_text = element.text.strip()

                        # Skip if there's no text or it doesn't contain ranking info
                        if not any(
                            keyword in element_text.lower()
                            for keyword in ranking_keywords
                        ):
                            continue

                        # Look for lines that might contain ranking info
                        lines = element_text.split("\n")

                        for i in range(len(lines) - 1):
                            current_line = lines[i].strip()
                            next_line = lines[i + 1].strip()

                            # If this line contains a ranking keyword and the next line looks like a value
                            if any(
                                keyword in current_line.lower()
                                for keyword in ranking_keywords
                            ) and re.match(
                                r"^[\d\.]+$|^[\d]+(st|nd|rd|th)$", next_line
                            ):
                                key = self._clean_ranking_key(current_line)
                                value = re.sub(r"(st|nd|rd|th)$", "", next_line)

                                # Decide if this is a score or a rank
                                if (
                                    re.match(r"^[\d\.]+$", value)
                                    and float(value) > 0
                                    and float(value) <= 100
                                ):
                                    rankings[f"{key}_score"] = value
                                else:
                                    rankings[f"{key}_rank"] = value

                except NoSuchElementException:
                    continue

            return rankings

        except Exception as e:
            logger.debug(f"Failed to extract additional rankings: {str(e)}")
            return {}

    def _clean_ranking_key(self, text) -> str:
        """Clean and standardize ranking text into a key."""
        if not text:
            return "unknown"

        # Convert to lowercase
        text = text.lower()

        # Remove common words and phrases
        text = re.sub(
            r"\b(ranking|rankings|rank|score|position|the|and|in|of|for|year|#|-|–)\b",
            " ",
            text,
        )

        # Handle specific cases like "World University Rankings 2025" -> "world_university_2025"
        if "world" in text and "university" in text and re.search(r"\b20\d{2}\b", text):
            return "world_university"

        # Clean up whitespace and replace spaces with underscores
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace(" ", "_")

        # Remove any non-alphanumeric characters except underscores
        text = re.sub(r"[^a-z0-9_]", "", text)

        # Make sure we don't have empty string
        if not text:
            return "unknown"

        return text

    def _parse_ranking_card(self, card_element) -> Dict[str, Any]:
        """Parse a single ranking card element."""
        try:
            card_data = {}

            # Process all potential ranking data within the card
            # Look at all elements that might contain rankings

            # 1. Look for specific structured ranking data
            rank_items = card_element.find_elements(
                By.CSS_SELECTOR, "div.css-11m5q9m, div.css-1dvz8m0"
            )

            for item in rank_items:
                text = item.text.strip()
                # Look for ranking information
                if text and (
                    "rank" in text.lower() or "score" in text.lower() or "=" in text
                ):
                    parts = text.split("\n")
                    if len(parts) >= 2:
                        # Format: "Label\nValue"
                        label = parts[0].strip()
                        value = parts[1].strip()

                        key = self._clean_ranking_key(label)

                        # Determine if this is a score or rank
                        if "score" in label.lower() or (
                            re.match(r"^[\d\.]+$", value)
                            and float(value) > 0
                            and float(value) <= 100
                        ):
                            card_data[f"{key}_score"] = value
                        else:
                            card_data[f"{key}_rank"] = value

            # 2. If no structured data found, try to extract from all text
            if not card_data:
                all_text = card_element.text.strip()

                # Look for common ranking patterns
                patterns = [
                    # Format: "Label: Value" or "Label = Value"
                    (
                        r"([^:=\n]+)[:=]([^:=\n]+)",
                        lambda m: (m.group(1).strip(), m.group(2).strip()),
                    ),
                    # Format: "Label Value" where Value is numeric or has st/nd/rd/th
                    (
                        r"([a-zA-Z\s]+)\s+((?:\d+\.?\d*)|(?:\d+(?:st|nd|rd|th)))",
                        lambda m: (m.group(1).strip(), m.group(2).strip()),
                    ),
                ]

                for pattern, extract in patterns:
                    matches = re.finditer(pattern, all_text)
                    for match in matches:
                        label, value = extract(match)
                        key = self._clean_ranking_key(label)

                        # Determine if this is a score or rank
                        if re.search(r"score", label, re.IGNORECASE) or (
                            re.match(r"^[\d\.]+$", value)
                            and float(value) > 0
                            and float(value) <= 100
                        ):
                            card_data[f"{key}_score"] = re.sub(
                                r"(st|nd|rd|th)$", "", value
                            )
                        else:
                            card_data[f"{key}_rank"] = re.sub(
                                r"(st|nd|rd|th)$", "", value
                            )

            return card_data

        except Exception as e:
            logger.debug(f"Failed to parse ranking card: {str(e)}")
            return {}

    def _extract_individual_rankings(self) -> Dict[str, Any]:
        """Extract ranking data from individual elements when cards are not available."""
        ranking_data = {}

        try:
            # Look for ranking elements in the main page content
            # Updated to cover more ranking indicators

            # 1. Look for specific label and score pairs
            try:
                # Find all visible labels
                label_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "span.barlabel-text, td.ranking-label, div.ranking-name",
                )

                for element in label_elements:
                    label = element.text.strip()
                    if not label:
                        continue

                    # Try to find the associated score element
                    try:
                        # Look for the next element with a score
                        score_element = element.find_element(
                            By.XPATH,
                            "./following-sibling::*[contains(@class, 'score') or contains(@class, 'value')]",
                        )
                        if score_element:
                            score = score_element.text.strip()
                            key = self._clean_ranking_key(label)
                            ranking_data[f"{key}_score"] = score
                    except NoSuchElementException:
                        pass
            except Exception:
                pass

            # 2. Look for ranking positions in tabs or segments
            try:
                position_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".ranking-position, div:has(> .position-badge), div:has(> span:contains('st'), span:contains('nd'), span:contains('rd'), span:contains('th'))",
                )

                for i, element in enumerate(position_elements):
                    position_text = element.text.strip()
                    if not position_text:
                        continue

                    # Look for ranking positions like 1st, 2nd, etc.
                    position_match = re.search(r"(\d+)(?:st|nd|rd|th)", position_text)
                    if position_match:
                        # Try to find the category name
                        try:
                            category_element = element.find_element(
                                By.XPATH, "./preceding-sibling::*[1]"
                            )
                            category = category_element.text.strip()
                        except NoSuchElementException:
                            category = f"ranking_{i+1}"

                        key = self._clean_ranking_key(category)
                        ranking_data[f"{key}_rank"] = position_match.group(1)
            except Exception:
                pass

            # 3. Direct extraction from specialized ranking elements
            try:
                # Extract from the chart with ranking data
                chart = self.driver.find_element(
                    By.CSS_SELECTOR, "div[data-testid='RankingOverviewChart']"
                )
                if chart:
                    # Look for all rows inside the chart
                    rows = chart.find_elements(
                        By.CSS_SELECTOR, "div.css-1kroxql, div.css-1dvz8m0"
                    )

                    for row in rows:
                        text = row.text.strip()
                        if text:
                            # Split into label and score if possible
                            parts = text.split("\n")
                            if len(parts) >= 2:
                                label = parts[0].strip()
                                score = parts[1].strip()

                                key = self._clean_ranking_key(label)
                                ranking_data[f"{key}_score"] = score
            except NoSuchElementException:
                pass

        except Exception as e:
            logger.debug(f"No individual rankings found: {str(e)}")

        return ranking_data

    def _extract_key_stats(self) -> Dict[str, Any]:
        """Extract key statistics from the university page."""
        stats = {}

        try:
            logger.info("Extracting key stats")

            # Try to find the key stats section specifically using the title first
            stat_title_elements = self.driver.find_elements(
                By.XPATH, "//h2[contains(text(), 'Key Student Statistics')]"
            )

            if stat_title_elements:
                logger.info("Found Key Student Statistics heading")
                # Get the parent container of the statistics
                stats_section = None
                for title in stat_title_elements:
                    try:
                        # Navigate up to find the container
                        stats_section = title.find_element(
                            By.XPATH,
                            "./ancestor::div[contains(@data-testid, 'profiles-section-wrapper')]",
                        )
                        break
                    except NoSuchElementException:
                        continue

                if stats_section:
                    logger.info("Found stats section container")
                    # Extract stats from this section specifically
                    stats.update(self._extract_stats_from_section(stats_section))

            # If no stats found with the above approach, try alternative selectors
            if not stats:
                logger.info("Trying alternative stats selectors")
                stats_selectors = [
                    "div[data-testid='keyStats']",
                    "div[data-testid='profiles-section-wrapper']",
                ]

                for selector in stats_selectors:
                    try:
                        stats_containers = self.driver.find_elements(
                            By.CSS_SELECTOR, selector
                        )
                        logger.info(
                            f"Found {len(stats_containers)} potential stat containers"
                        )

                        for container in stats_containers:
                            container_stats = self._extract_stats_from_section(
                                container
                            )
                            if container_stats:
                                logger.info(
                                    f"Extracted {len(container_stats)} stats from container"
                                )
                                stats.update(container_stats)
                    except NoSuchElementException:
                        continue

            # Direct extraction for specific stats shown in the images
            if not stats:
                logger.info("Attempting direct extraction of specific stats")
                stats = self._extract_specific_stats()

            logger.info(f"Extracted total of {len(stats)} key stats")
            return stats

        except Exception as e:
            logger.warning(f"Failed to extract key stats: {str(e)}")
            return {}

    def _extract_stats_from_section(self, section) -> Dict[str, Any]:
        """Extract statistics from a section container."""
        stats = {}
        try:
            # Look for the stats with label and value structure
            # Try different selector patterns
            stat_items = section.find_elements(
                By.CSS_SELECTOR, "div.css-11m5q9m, div.css-1dvz8m0"
            )

            # Additional patterns shown in the images
            if not stat_items:
                # Try to find specific student stats format from images
                stat_items = section.find_elements(
                    By.XPATH, ".//div[contains(@class, 'css-')]"
                )

            for item in stat_items:
                try:
                    text = item.text.strip()
                    if "Student total" in text:
                        value_text = text.split("Student total")[1].strip()
                        stats["student_total"] = value_text.replace("\n", "")
                    elif "Student gender ratio" in text:
                        value_text = text.split("Student gender ratio")[1].strip()
                        stats["student_gender_ratio"] = value_text.replace("\n", "")
                    elif "International student percentage" in text:
                        value_text = text.split("International student percentage")[
                            1
                        ].strip()
                        stats["international_student_percentage"] = value_text.replace(
                            "\n", ""
                        )
                    elif "Students per staff" in text:
                        value_text = text.split("Students per staff")[1].strip()
                        stats["students_per_staff"] = value_text.replace("\n", "")
                    elif text and "\n" in text:
                        lines = text.split("\n")
                        if len(lines) >= 2:
                            stat_name = lines[0].lower().replace(" ", "_")
                            stat_value = lines[1]
                            stats[stat_name] = stat_value
                except Exception as e:
                    logger.debug(f"Failed to parse stat item: {str(e)}")

            return stats

        except Exception as e:
            logger.debug(f"Failed to extract stats from section: {str(e)}")
            return {}

    def _extract_specific_stats(self) -> Dict[str, Any]:
        """Extract specific statistics directly using precise selectors."""
        stats = {}

        try:
            # Try to find student total specifically using the pattern seen in the image
            student_total_xpath = (
                "//div[text()='Student total']/following-sibling::div[1]"
            )
            gender_ratio_xpath = (
                "//div[text()='Student gender ratio']/following-sibling::div[1]"
            )
            international_xpath = "//div[text()='International student percentage']/following-sibling::div[1]"
            students_per_staff_xpath = (
                "//div[text()='Students per staff']/following-sibling::div[1]"
            )

            try:
                student_total = self.driver.find_element(By.XPATH, student_total_xpath)
                stats["student_total"] = student_total.text.strip()
            except NoSuchElementException:
                pass

            try:
                gender_ratio = self.driver.find_element(By.XPATH, gender_ratio_xpath)
                stats["student_gender_ratio"] = gender_ratio.text.strip()
            except NoSuchElementException:
                pass

            try:
                international = self.driver.find_element(By.XPATH, international_xpath)
                stats["international_student_percentage"] = international.text.strip()
            except NoSuchElementException:
                pass

            try:
                students_staff = self.driver.find_element(
                    By.XPATH, students_per_staff_xpath
                )
                stats["students_per_staff"] = students_staff.text.strip()
            except NoSuchElementException:
                pass

        except Exception as e:
            logger.debug(f"Failed to extract specific stats: {str(e)}")

        return stats

    def _extract_subjects_data(self) -> List[Dict[str, Any]]:
        """Extract subject rankings and information."""
        subjects = []

        try:
            logger.info("Extracting subjects data")

            # Try to find the subjects section specifically using the title first
            subject_headings = self.driver.find_elements(
                By.XPATH, "//h2[contains(text(), 'Subjects Taught')]"
            )

            if subject_headings:
                logger.info("Found Subjects Taught heading")
                # Get the parent container of the subjects section
                subjects_section = None
                for heading in subject_headings:
                    try:
                        # Find the container div
                        subjects_section = heading.find_element(
                            By.XPATH,
                            "./ancestor::div[contains(@data-testid, 'profiles-section-wrapper')]",
                        )
                        break
                    except NoSuchElementException:
                        continue

                if subjects_section:
                    logger.info("Found subjects section container")
                    # Process the category headings and subjects
                    subjects = self._parse_subjects_from_section(subjects_section)

            # If still no subjects, try alternative selectors
            if not subjects:
                logger.info("Trying alternative subjects selectors")

                # Updated selectors for subjects section
                subjects_selectors = [
                    "div[data-testid='profiles-section-wrapper'][id='subjects']",
                    "div[data-testid='section-subjects']",
                    "div[data-testid='subjects']",
                ]

                for selector in subjects_selectors:
                    try:
                        subjects_container = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        subjects = self._parse_subjects_from_section(subjects_container)
                        if subjects:
                            logger.info(
                                f"Found {len(subjects)} subjects with selector {selector}"
                            )
                            break
                    except NoSuchElementException:
                        continue

            # Direct extraction approach as last resort
            if not subjects:
                logger.info("Attempting direct extraction of subject categories")
                subjects = self._extract_subjects_direct()

            logger.info(f"Extracted total of {len(subjects)} subjects")
            return subjects

        except Exception as e:
            logger.warning(f"Failed to extract subjects data: {str(e)}")
            return []

    def _parse_subjects_from_section(self, section) -> List[Dict[str, Any]]:
        """Parse subjects from a subjects section."""
        subjects = []

        try:
            # Get all category headings (h3 elements) within the section
            # The selector shown in the image is h3.css-1vd75my
            category_headings = section.find_elements(
                By.CSS_SELECTOR, "h3.css-1vd75my, h3"
            )

            if not category_headings:
                logger.debug("No category headings found, trying alternative selectors")
                # Try alternative heading selectors
                category_headings = section.find_elements(By.XPATH, ".//h3")

            logger.info(f"Found {len(category_headings)} subject categories")

            for heading in category_headings:
                try:
                    category_name = heading.text.strip()
                    if category_name:
                        # Find the list of subjects that follows this heading
                        # In the image, we see the list has class css-19cj1d2
                        try:
                            # First try with class selector
                            subject_list = heading.find_element(
                                By.XPATH, "./following-sibling::ul[1]"
                            )
                        except NoSuchElementException:
                            # Fallback to any ul that follows
                            try:
                                subject_list = heading.find_element(
                                    By.XPATH, "./following-sibling::ul"
                                )
                            except NoSuchElementException:
                                continue

                        # Find all li items in the subject list
                        subject_items = subject_list.find_elements(By.TAG_NAME, "li")

                        for item in subject_items:
                            subject_name = item.text.strip()
                            if subject_name:
                                subjects.append(
                                    {"category": category_name, "name": subject_name}
                                )
                except Exception as e:
                    logger.debug(f"Error processing subject category: {str(e)}")

            return subjects

        except Exception as e:
            logger.debug(f"Failed to parse subjects from section: {str(e)}")
            return []

    def _extract_subjects_direct(self) -> List[Dict[str, Any]]:
        """Extract subjects directly using precise XPath expressions."""
        subjects = []

        try:
            # Based on the image, the structure seems to be:
            # 1. Category header (e.g., "Arts and Humanities")
            # 2. List of subjects under that category

            # Try to get all category headers first
            category_headers = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@data-testid, 'subjects')]//h3[contains(@class, 'css-')]",
            )

            for header in category_headers:
                category_name = header.text.strip()
                if not category_name:
                    continue

                # Find all subject items under this category
                # We need to look at the next sibling ul after the h3
                try:
                    subject_list = self.driver.find_element(
                        By.XPATH,
                        f"//h3[contains(text(), '{category_name}')]/following-sibling::ul[1]",
                    )

                    if subject_list:
                        subject_items = subject_list.find_elements(By.TAG_NAME, "li")
                        for item in subject_items:
                            subject_name = item.text.strip()
                            if subject_name:
                                subjects.append(
                                    {"category": category_name, "name": subject_name}
                                )
                except NoSuchElementException:
                    logger.debug(
                        f"Could not find subjects list for category {category_name}"
                    )

        except Exception as e:
            logger.debug(f"Failed in direct subject extraction: {str(e)}")

        return subjects

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
