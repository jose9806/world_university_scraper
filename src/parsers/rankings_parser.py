"""Parser for THE World University Rankings data."""

import logging
import re
from typing import Dict, Any, List

from parsers.base_parser import BaseParser
from utils.exceptions import ParserException

logger = logging.getLogger(__name__)


class RankingsParser(BaseParser):
    """Parser for THE World University Rankings HTML content."""

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse rankings HTML into structured data.

        Args:
            content: Raw HTML content from rankings page

        Returns:
            List of dictionaries containing university ranking data
        """
        logger.info("Parsing rankings data")

        soup = self._create_soup(content)
        universities = []

        table = soup.find("table", id="datatable-1")
        if not table:
            raise ParserException("Could not find rankings table in HTML")

        rows = table.find_all("tr")  # type: ignore

        # Skip header row
        for row in rows[1:]:
            try:
                university = self._parse_university_row(row)
                universities.append(university)
            except Exception as e:
                logger.warning(f"Failed to parse university row: {e}")

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

        # Extract university data from columns
        # This would need to be adapted based on the actual structure
        rank_text = cols[0].text.strip()
        rank = self._extract_rank(rank_text)

        return {
            "rank": rank,
            "name": cols[1].text.strip(),
            "country": cols[2].text.strip(),
            "overall_score": self._extract_score(cols[3].text.strip()),
            "teaching_score": self._extract_score(cols[4].text.strip()),
            "research_score": self._extract_score(cols[5].text.strip()),
            "citations_score": self._extract_score(cols[6].text.strip()),
            "industry_income_score": self._extract_score(cols[7].text.strip()),
            "international_outlook_score": self._extract_score(cols[8].text.strip()),
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
