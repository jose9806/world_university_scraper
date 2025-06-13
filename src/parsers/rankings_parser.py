"""Parser for THE World University Rankings data."""

import logging
import re
from typing import Dict, Any, List, Optional

from .base_parser import BaseParser
from ..utils.exceptions import ParserException

logger = logging.getLogger(__name__)


class RankingsParser(BaseParser):
    """Parser for THE World University Rankings HTML content."""

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse rankings HTML into structured data."""
        logger.info("Parsing rankings data")

        soup = self._create_soup(content)
        universities = []

        # Debug - check if we can find the table
        table = soup.find("table", id="datatable-1")
        if not table:
            logger.warning("Could not find table with id 'datatable-1'")
            # Try alternative selectors
            table = soup.find("table", class_="rankings-table") or soup.find(
                "table", class_="data-table"
            )

        if not table:
            # Try to find any table that might contain university rankings
            tables = soup.find_all("table")
            logger.info(f"Found {len(tables)} tables")

            if tables:
                # Try using the first table that has substantial content
                for t in tables:
                    rows = t.find_all("tr")
                    if len(rows) > 10:  # Assume rankings table has many rows
                        table = t
                        logger.info(f"Using table with {len(rows)} rows")
                        break

        if not table:
            raise ParserException("Could not find rankings table in HTML")

        rows = table.find_all("tr")
        logger.info(f"Found {len(rows)} rows in table")

        # Skip header row
        for i, row in enumerate(rows[1:], 1):
            try:
                university = self._parse_university_row(row, i)
                if university:  # Only add if parsing was successful
                    universities.append(university)

                # Log progress every 50 universities
                if i % 50 == 0:
                    logger.info(
                        f"Parsed {len(universities)} universities successfully from {i} rows"
                    )

            except Exception as e:
                logger.warning(f"Failed to parse row {i}: {str(e)}")
                logger.debug(f"Row {i} HTML: {row.prettify()[:200]}...")

        logger.info(f"Successfully parsed {len(universities)} universities")
        return universities

    def _parse_university_row(self, row, row_number: int) -> Optional[Dict[str, Any]]:
        """Parse a single university row from the rankings table.

        Args:
            row: BeautifulSoup element representing a table row
            row_number: Row number for better error reporting

        Returns:
            Dictionary containing university data or None if parsing fails
        """
        try:
            cols = row.find_all("td")

            if len(cols) < 2:
                logger.debug(f"Row {row_number}: Insufficient columns ({len(cols)})")
                return None

            # Extract rank
            rank_text = cols[0].text.strip() if cols[0] else ""
            rank = self._extract_rank(rank_text)

            # Extract name, country, and URL from the second column
            name_col = cols[1]

            # Try multiple strategies to find the university name and link
            name, university_url = self._extract_name_and_url(name_col, row_number)

            if not name:
                logger.warning(f"Row {row_number}: Could not extract university name")
                return None

            # Find country - try multiple selectors
            country = self._extract_country(name_col, row_number)

            # Extract scores from remaining columns with better error handling
            result = {
                "rank": rank,
                "name": name,
                "country": country,
                "university_url": university_url,
                "overall_score": self._extract_score_safe(cols, 2, "overall"),
                "teaching_score": self._extract_score_safe(cols, 3, "teaching"),
                "research_score": self._extract_score_safe(cols, 4, "research"),
                "citations_score": self._extract_score_safe(cols, 5, "citations"),
                "industry_income_score": self._extract_score_safe(
                    cols, 6, "industry_income"
                ),
                "international_outlook_score": self._extract_score_safe(
                    cols, 7, "international_outlook"
                ),
            }

            return result

        except Exception as e:
            logger.error(
                f"Row {row_number}: Unexpected error in _parse_university_row: {str(e)}"
            )
            return None

    def _extract_name_and_url(
        self, name_col, row_number: int
    ) -> tuple[str, Optional[str]]:
        """Extract university name and URL with multiple fallback strategies.

        Args:
            name_col: BeautifulSoup element containing name information
            row_number: Row number for error reporting

        Returns:
            Tuple of (name, university_url)
        """
        name = ""
        university_url = None

        # Strategy 1: Look for the specific class "ranking-institution-title"
        link_element = name_col.find("a", class_="ranking-institution-title")

        if link_element:
            name = link_element.text.strip()
            university_url = link_element.get("href")
        else:
            # Strategy 2: Look for any anchor tag in the name column
            link_element = name_col.find("a")
            if link_element:
                name = link_element.text.strip()
                university_url = link_element.get("href")
            else:
                # Strategy 3: Look for text content directly in the column
                name = name_col.text.strip()
                logger.debug(
                    f"Row {row_number}: No link found, extracted text: '{name[:50]}...'"
                )

        # Clean up the URL if found
        if university_url:
            # Ensure the URL is complete
            if university_url.startswith("/"):
                university_url = "https://www.timeshighereducation.com" + university_url
            elif not university_url.startswith("http"):
                university_url = (
                    "https://www.timeshighereducation.com/" + university_url
                )

        return name, university_url

    def _extract_country(self, name_col, row_number: int) -> str:
        """Extract country information with multiple fallback strategies.

        Args:
            name_col: BeautifulSoup element containing location information
            row_number: Row number for error reporting

        Returns:
            Country name or empty string
        """
        country = ""

        # Strategy 1: Look for location div
        location_div = name_col.find("div", class_="location")
        if location_div:
            country_link = location_div.find("a")
            if country_link:
                country = country_link.text.strip()
            else:
                country = location_div.text.strip()

        # Strategy 2: Look for any element that might contain country info
        if not country:
            # Look for patterns like "United States" or "United Kingdom"
            text_content = name_col.text
            # This is a simple heuristic - could be improved with more sophisticated logic
            lines = [line.strip() for line in text_content.split("\n") if line.strip()]
            if len(lines) > 1:
                # Usually country is in the second line after university name
                country = lines[1]

        return country

    def _extract_score_safe(
        self, cols: list, index: int, score_type: str
    ) -> Optional[float]:
        """Safely extract score from column with better error handling.

        Args:
            cols: List of column elements
            index: Column index to extract from
            score_type: Type of score for logging purposes

        Returns:
            Score value or None if extraction fails
        """
        try:
            if index >= len(cols):
                return None

            score_text = cols[index].text.strip() if cols[index] else ""
            score = self._extract_score(score_text)

            return score

        except Exception as e:
            logger.debug(
                f"Failed to extract {score_type} score from index {index}: {str(e)}"
            )
            return None

    def _extract_rank(self, rank_text: str) -> Optional[int]:
        """Extract numerical rank from rank text.

        Args:
            rank_text: Text containing rank information

        Returns:
            Numerical rank value or None if extraction fails
        """
        if not rank_text:
            return None

        try:
            # Handle ranges like "=401-500"
            if "-" in rank_text:
                # Take the lower bound for ranges
                match = re.search(r"=?(\d+)", rank_text)
                if match:
                    return int(match.group(1))
                return None

            # Handle equals sign for tied ranks
            if rank_text.startswith("="):
                return int(rank_text[1:])

            # Handle normal ranks
            return int(rank_text)

        except ValueError:
            logger.warning(f"Could not parse rank: '{rank_text}'")
            return None

    def _extract_score(self, score_text: str) -> Optional[float]:
        """Extract numerical score from score text.

        Args:
            score_text: Text containing score information

        Returns:
            Numerical score value or None if not available
        """
        if not score_text or score_text in ["n/a", "–", "", "N/A", "-"]:
            return None

        try:
            # Remove any non-numeric characters except decimal point
            cleaned_score = re.sub(r"[^\d.]", "", score_text)
            if cleaned_score:
                return float(cleaned_score)
            return None
        except ValueError:
            logger.warning(f"Could not parse score: '{score_text}'")
            return None
