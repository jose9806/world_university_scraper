"""Parser for individual university detail pages from THE."""

import logging
import re
from typing import Dict, Any, List, Optional

from .base_parser import BaseParser
from ..utils.exceptions import ParserException

logger = logging.getLogger(__name__)


class UniversityDetailParser(BaseParser):
    """Parser for individual university detail page HTML content."""

    def parse(self, content: str, url: str = "") -> Dict[str, Any]:
        """Parse university detail HTML into structured data.

        Args:
            content: HTML content of the university page
            url: Original URL for reference

        Returns:
            Dictionary containing structured university data
        """
        logger.info(f"Parsing university details for URL: {url}")

        soup = self._create_soup(content)

        try:
            university_data = {
                "url": url,
                "name": self._extract_university_name(soup),
                "ranking_data": self._extract_ranking_data(soup),
                "key_stats": self._extract_key_stats(soup),
                "subjects": self._extract_subjects_data(soup),
                "additional_info": self._extract_additional_info(soup),
            }

            logger.info(
                f"Successfully parsed university: {university_data.get('name', 'Unknown')}"
            )
            return university_data

        except Exception as e:
            logger.error(f"Failed to parse university page {url}: {str(e)}")
            return {"url": url, "error": str(e)}

    def _extract_university_name(self, soup) -> str:
        """Extract university name from the page."""
        try:
            # Try multiple selectors for the university name in order of preference
            selectors = [
                "h1.profile-header__title",
                "h1.hero-title",
                ".profile-header h1",
                ".university-name",
                ".institution-name",
                "h1",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element and element.text.strip():
                    return element.text.strip()

            logger.warning("Could not find university name")
            return "Unknown"

        except Exception as e:
            logger.warning(f"Failed to extract university name: {str(e)}")
            return "Unknown"

    def _extract_ranking_data(self, soup) -> Dict[str, Any]:
        """Extract ranking information from the page."""
        ranking_data = {}

        try:
            # Strategy 1: Look for ranking cards or containers
            ranking_containers = soup.select(
                ".ranking-card, .rank-card, .profile-ranking, .university-ranking"
            )

            for container in ranking_containers:
                rank_info = self._parse_ranking_container(container)
                ranking_data.update(rank_info)

            # Strategy 2: Look for individual ranking elements
            if not ranking_data:
                ranking_data = self._extract_individual_rankings(soup)

            # Strategy 3: Look for ranking in page title or meta
            if not ranking_data:
                ranking_data = self._extract_ranking_from_meta(soup)

        except Exception as e:
            logger.warning(f"Failed to extract ranking data: {str(e)}")

        return ranking_data

    def _parse_ranking_container(self, container) -> Dict[str, Any]:
        """Parse ranking information from a container element."""
        rank_data = {}

        try:
            # Extract ranking title/type
            title_elem = container.select_one(
                ".card-title, h3, h4, .ranking-title, .title"
            )
            title = title_elem.text.strip() if title_elem else "general"

            # Clean up title for use as key
            title_key = re.sub(r"[^a-zA-Z0-9\s]", "", title.lower()).replace(" ", "_")

            # Extract rank number
            rank_elem = container.select_one(
                ".rank, .ranking-number, .position, .rank-position"
            )
            if rank_elem:
                rank_text = rank_elem.text.strip()
                rank_data[f"{title_key}_rank"] = self._clean_rank_text(rank_text)

            # Extract score if available
            score_elem = container.select_one(".score, .ranking-score, .points")
            if score_elem:
                score_text = score_elem.text.strip()
                rank_data[f"{title_key}_score"] = self._clean_score_text(score_text)

            # Extract year if available
            year_elem = container.select_one(".year, .ranking-year, .period")
            if year_elem:
                rank_data[f"{title_key}_year"] = year_elem.text.strip()

        except Exception as e:
            logger.debug(f"Failed to parse ranking container: {str(e)}")

        return rank_data

    def _extract_individual_rankings(self, soup) -> Dict[str, Any]:
        """Extract ranking data from individual elements."""
        ranking_data = {}

        try:
            # Common patterns for ranking information
            rank_patterns = [
                {"selector": ".world-rank", "key": "world_rank"},
                {"selector": ".overall-rank", "key": "overall_rank"},
                {"selector": ".reputation-rank", "key": "reputation_rank"},
                {"selector": ".global-rank", "key": "global_rank"},
            ]

            for pattern in rank_patterns:
                element = soup.select_one(pattern["selector"])
                if element:
                    rank_text = element.text.strip()
                    ranking_data[pattern["key"]] = self._clean_rank_text(rank_text)

        except Exception as e:
            logger.debug(f"No individual rankings found: {str(e)}")

        return ranking_data

    def _extract_ranking_from_meta(self, soup) -> Dict[str, Any]:
        """Extract ranking information from page title or meta tags."""
        ranking_data = {}

        try:
            # Check page title for ranking information
            title_elem = soup.find("title")
            if title_elem:
                title_text = title_elem.text
                # Look for patterns like "Ranked 5th" or "#5" in title
                rank_match = re.search(
                    r"(?:ranked?\s*)?(?:#|no\.?\s*)?(\d+)(?:st|nd|rd|th)?",
                    title_text,
                    re.IGNORECASE,
                )
                if rank_match:
                    ranking_data["meta_rank"] = rank_match.group(1)

        except Exception as e:
            logger.debug(f"No ranking found in meta: {str(e)}")

        return ranking_data

    def _extract_key_stats(self, soup) -> Dict[str, Any]:
        """Extract key statistics from the university page."""
        stats = {}

        try:
            # Strategy 1: Look for dedicated stats sections
            stats_containers = soup.select(
                ".key-stats, .university-stats, .profile-stats, .stats-container, .facts-figures"
            )

            for container in stats_containers:
                container_stats = self._parse_stats_container(container)
                stats.update(container_stats)

            # Strategy 2: Look for definition lists (common pattern)
            dl_elements = soup.select("dl")
            for dl in dl_elements:
                dl_stats = self._parse_definition_list(dl)
                stats.update(dl_stats)

            # Strategy 3: Look for individual stat elements
            if not stats:
                stats = self._extract_individual_stats(soup)

        except Exception as e:
            logger.warning(f"Failed to extract key stats: {str(e)}")

        return stats

    def _parse_stats_container(self, container) -> Dict[str, Any]:
        """Parse statistics from a stats container element."""
        stats = {}

        try:
            # Look for stat items within the container
            stat_items = container.select(".stat-item, .key-stat, .metric, .fact")

            for item in stat_items:
                stat_name, stat_value = self._parse_stat_item(item)
                if stat_name and stat_value:
                    # Clean up stat name for use as key
                    stat_key = re.sub(r"[^a-zA-Z0-9\s]", "", stat_name.lower()).replace(
                        " ", "_"
                    )
                    stats[stat_key] = stat_value

        except Exception as e:
            logger.debug(f"Failed to parse stats container: {str(e)}")

        return stats

    def _parse_definition_list(self, dl_element) -> Dict[str, Any]:
        """Parse statistics from a definition list (dl/dt/dd structure)."""
        stats = {}

        try:
            dts = dl_element.select("dt")
            dds = dl_element.select("dd")

            # Match dt and dd elements
            for dt, dd in zip(dts, dds):
                if dt and dd:
                    stat_name = dt.text.strip()
                    stat_value = dd.text.strip()

                    if stat_name and stat_value:
                        stat_key = re.sub(
                            r"[^a-zA-Z0-9\s]", "", stat_name.lower()
                        ).replace(" ", "_")
                        stats[stat_key] = stat_value

        except Exception as e:
            logger.debug(f"Failed to parse definition list: {str(e)}")

        return stats

    def _parse_stat_item(self, item) -> tuple[str, str]:
        """Parse an individual statistic item."""
        try:
            # Pattern 1: Separate name and value elements
            name_elem = item.select_one(".stat-name, .label, .key, .metric-name")
            value_elem = item.select_one(".stat-value, .value, .metric-value")

            if name_elem and value_elem:
                return name_elem.text.strip(), value_elem.text.strip()

            # Pattern 2: Combined text that needs to be split
            text = item.text.strip()
            if ":" in text:
                parts = text.split(":", 1)
                return parts[0].strip(), parts[1].strip()
            elif "\n" in text:
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if len(lines) >= 2:
                    return lines[0], lines[1]

            return "", ""

        except Exception:
            return "", ""

    def _extract_individual_stats(self, soup) -> Dict[str, Any]:
        """Extract stats from individual elements."""
        stats = {}

        try:
            # Common stat patterns with their likely keys
            stat_patterns = [
                {"selector": ".student-count, .students", "key": "total_students"},
                {"selector": ".faculty-count, .staff", "key": "faculty_count"},
                {
                    "selector": ".established, .founded, .year-established",
                    "key": "established",
                },
                {"selector": ".campus-size, .campus", "key": "campus_size"},
                {
                    "selector": ".international-students",
                    "key": "international_students",
                },
                {"selector": ".student-faculty-ratio", "key": "student_faculty_ratio"},
            ]

            for pattern in stat_patterns:
                element = soup.select_one(pattern["selector"])
                if element:
                    text = element.text.strip()
                    # Clean the text to extract just the numerical/relevant part
                    cleaned_value = self._clean_stat_value(text)
                    if cleaned_value:
                        stats[pattern["key"]] = cleaned_value

        except Exception as e:
            logger.debug(f"No individual stats found: {str(e)}")

        return stats

    def _extract_subjects_data(self, soup) -> List[Dict[str, Any]]:
        """Extract subject rankings and information."""
        subjects = []

        try:
            # Look for subjects sections
            subjects_containers = soup.select(
                ".subjects-section, .subject-rankings, .disciplines, .academic-areas, .subject-area"
            )

            for container in subjects_containers:
                container_subjects = self._parse_subjects_container(container)
                subjects.extend(container_subjects)

            # Remove duplicates based on subject name
            seen_subjects = set()
            unique_subjects = []
            for subject in subjects:
                subject_name = subject.get("name", "").lower()
                if subject_name and subject_name not in seen_subjects:
                    seen_subjects.add(subject_name)
                    unique_subjects.append(subject)

            subjects = unique_subjects

        except Exception as e:
            logger.warning(f"Failed to extract subjects data: {str(e)}")

        return subjects

    def _parse_subjects_container(self, container) -> List[Dict[str, Any]]:
        """Parse subjects from a subjects container."""
        subjects = []

        try:
            # Look for individual subject items
            subject_items = container.select(
                ".subject-item, .discipline, .subject-rank, .subject"
            )

            for item in subject_items:
                subject_data = self._parse_subject_item(item)
                if subject_data and subject_data.get("name"):
                    subjects.append(subject_data)

        except Exception as e:
            logger.debug(f"Failed to parse subjects container: {str(e)}")

        return subjects

    def _parse_subject_item(self, item) -> Dict[str, Any]:
        """Parse an individual subject item."""
        try:
            subject_data = {}

            # Extract subject name
            name_elem = item.select_one(
                ".subject-name, .discipline-name, h3, h4, .name"
            )
            if name_elem:
                subject_data["name"] = name_elem.text.strip()
            else:
                # Try to get name from the item text directly
                text = item.text.strip()
                if text:
                    # If it's just text, use the first line as name
                    lines = text.split("\n")
                    subject_data["name"] = lines[0].strip()

            # Extract subject rank
            rank_elem = item.select_one(".subject-rank, .rank, .position")
            if rank_elem:
                rank_text = rank_elem.text.strip()
                subject_data["rank"] = self._clean_rank_text(rank_text)

            # Extract subject score if available
            score_elem = item.select_one(".subject-score, .score")
            if score_elem:
                score_text = score_elem.text.strip()
                subject_data["score"] = self._clean_score_text(score_text)

            return subject_data

        except Exception as e:
            logger.debug(f"Failed to parse subject item: {str(e)}")
            return {}

    def _extract_additional_info(self, soup) -> Dict[str, Any]:
        """Extract additional information that might be useful."""
        additional_info = {}

        try:
            # Extract location information
            location_elem = soup.select_one(".location, .address, .country")
            if location_elem:
                additional_info["location"] = location_elem.text.strip()

            # Extract website URL
            website_elem = soup.select_one(
                "a[href*='www.']:not([href*='timeshighereducation'])"
            )
            if website_elem:
                additional_info["website"] = website_elem.get("href")

            # Extract any prominent description
            desc_elem = soup.select_one(".description, .about, .overview")
            if desc_elem:
                desc_text = desc_elem.text.strip()
                if len(desc_text) > 50:  # Only include substantial descriptions
                    additional_info["description"] = (
                        desc_text[:500] + "..." if len(desc_text) > 500 else desc_text
                    )

        except Exception as e:
            logger.debug(f"Failed to extract additional info: {str(e)}")

        return additional_info

    def _clean_rank_text(self, rank_text: str) -> Optional[str]:
        """Clean and standardize rank text."""
        if not rank_text:
            return None

        # Remove common prefixes and suffixes
        cleaned = re.sub(
            r"^(rank|position|#|no\.?)\s*", "", rank_text, flags=re.IGNORECASE
        )
        cleaned = re.sub(r"(st|nd|rd|th)$", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip() if cleaned.strip() else None

    def _clean_score_text(self, score_text: str) -> Optional[str]:
        """Clean and standardize score text."""
        if not score_text or score_text.lower() in ["n/a", "na", "-", "–"]:
            return None

        # Extract numerical score
        score_match = re.search(r"(\d+\.?\d*)", score_text)
        if score_match:
            return score_match.group(1)

        return score_text.strip()

    def _clean_stat_value(self, stat_text: str) -> Optional[str]:
        """Clean and standardize statistic values."""
        if not stat_text:
            return None

        # Remove common prefixes
        cleaned = re.sub(
            r"^(approx\.?|about|around|~)\s*", "", stat_text, flags=re.IGNORECASE
        )

        return cleaned.strip() if cleaned.strip() else None
