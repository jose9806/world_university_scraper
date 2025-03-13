"""Parser for THE World University Rankings data."""

import logging
import re
from typing import Dict, Any, List

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
            # Don't raise exception immediately, try to find it another way
            # Look for any table that might contain university rankings
            tables = soup.find_all("table")
            logger.info(f"Found {len(tables)} tables")

            if tables:
                # Try using the first table
                table = tables[0]
                logger.info(f"Using first table with ID: {table.get('id', 'no-id')}")

        if not table:
            raise ParserException("Could not find rankings table in HTML")

        rows = table.find_all("tr")
        logger.info(f"Found {len(rows)} rows in table")

        # Skip header row
        for i, row in enumerate(rows[1:], 1):
            try:
                university = self._parse_university_row(row)
                universities.append(university)
                # Log every 10th university for debugging
                if i % 10 == 0:
                    logger.info(f"Parsed {i} universities so far")
            except Exception as e:
                logger.warning(f"Failed to parse row {i}: {str(e)}")
                # Add this to see the detailed error
                import traceback

                logger.warning(traceback.format_exc())

        logger.info(f"Successfully parsed {len(universities)} universities")
        return universities

    def _parse_university_row(self, row) -> Dict[str, Any]:
        """Parse a single university row from the rankings table.

        Args:
            row: BeautifulSoup element representing a table row

        Returns:
            Dictionary containing university data
        """
        cols = row.find_all("td")

        # Extract rank
        rank_text = cols[0].text.strip()
        rank = self._extract_rank(rank_text)

        # Extract name and country from the second column
        name_col = cols[1]
        name = name_col.find("a", class_="ranking-institution-title").text.strip()

        # Find country - it's in a div with class "location"
        location_div = name_col.find("div", class_="location")
        country = ""
        if location_div:
            country_link = location_div.find("a")
            if country_link:
                country = country_link.text.strip()

        # Extract scores from remaining columns
        return {
            "rank": rank,
            "name": name,
            "country": country,
            "overall_score": self._extract_score(cols[2].text.strip()) if len(cols) > 2 else None,
            "teaching_score": self._extract_score(cols[3].text.strip()) if len(cols) > 3 else None,
            "research_score": self._extract_score(cols[4].text.strip()) if len(cols) > 4 else None,
            "citations_score": self._extract_score(cols[5].text.strip()) if len(cols) > 5 else None,
            "industry_income_score": self._extract_score(cols[6].text.strip()) if len(cols) > 6 else None,
            "international_outlook_score": self._extract_score(cols[7].text.strip()) if len(cols) > 7 else None,
        }

    def _extract_rank(self, rank_text: str) -> int | None:
        """Extract numerical rank from rank text.

        Args:
            rank_text: Text containing rank information

        Returns:
            Numerical rank value
        """
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

        try:
            return int(rank_text)
        except ValueError:
            logger.warning(f"Could not parse rank: {rank_text}")
            return None

    def _extract_score(self, score_text: str) -> float | None:
        """Extract numerical score from score text.

        Args:
            score_text: Text containing score information

        Returns:
            Numerical score value or None if not available
        """
        if score_text in ["n/a", "–", ""]:
            return None

        try:
            return float(score_text)
        except ValueError:
            logger.warning(f"Could not parse score: {score_text}")
            return None
