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
            # Updated selectors for university name
            selectors = [
                "h1.css-y89yc2",  # Primary selector based on images
                "[data-testid='institution-title']",
                "[data-testid='institution-page-header'] h1",
                "div.css-ejuz3m h1",
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
        """Extract comprehensive ranking information from the page."""
        ranking_data = {}

        try:
            # 1. Extract main rankings with scores (like Overall, Teaching, etc.)
            main_rankings = self._extract_main_rankings(soup)
            ranking_data.update(main_rankings)

            # 2. Extract ranking position cards (1st, 2nd, 3rd positions)
            position_rankings = self._extract_ranking_positions(soup)
            ranking_data.update(position_rankings)

            # 3. Extract any rankings from specific sections
            section_rankings = self._extract_section_rankings(soup)
            ranking_data.update(section_rankings)

            # 4. Extract individual ranking elements if we missed anything
            if not ranking_data:
                individual_rankings = self._extract_individual_rankings(soup)
                ranking_data.update(individual_rankings)

            logger.info(f"Extracted {len(ranking_data)} ranking metrics")
            return ranking_data

        except Exception as e:
            logger.warning(f"Failed to extract ranking data: {str(e)}")
            return {}

    def _extract_main_rankings(self, soup) -> Dict[str, Any]:
        """Extract main ranking scores from the chart section."""
        rankings = {}

        try:
            # Look for the main ranking chart
            chart_containers = soup.select(
                "div[data-testid='RankingOverviewChart'], div.css-1heidyz"
            )

            for container in chart_containers:
                # Look for ranking rows with labels and scores
                # Based on the image, these might be structured in different ways

                # Approach 1: Look for pairs of label and score elements
                label_elements = container.select(
                    ".barlabel-text, div[role='rowheader'], div.css-1kroxql"
                )
                score_elements = container.select(".barlabel-score, div[role='cell']")

                for i, label_elem in enumerate(label_elements):
                    if i < len(score_elements):
                        label = label_elem.text.strip()
                        score = score_elements[i].text.strip()

                        if label and score:
                            key = self._clean_ranking_key(label)
                            rankings[f"{key}_score"] = score

                # Approach 2: Look for div elements containing both label and score
                if not rankings:
                    ranking_rows = container.select("div > div")

                    for row in ranking_rows:
                        text = row.get_text(strip=True, separator="\n")
                        lines = [
                            line.strip() for line in text.split("\n") if line.strip()
                        ]

                        if len(lines) >= 2:
                            label = lines[0]
                            score = lines[1]

                            if label and score and re.match(r"^[\d\.]+$", score):
                                key = self._clean_ranking_key(label)
                                rankings[f"{key}_score"] = score

                # Approach 3: Try to extract from the whole text
                if not rankings:
                    chart_text = container.get_text(strip=True)

                    # Common ranking patterns to look for
                    patterns = [
                        (r"Overall\s+(\d+\.?\d*)", "overall"),
                        (r"Teaching\s+(\d+\.?\d*)", "teaching"),
                        (r"Research Environment\s+(\d+\.?\d*)", "research_environment"),
                        (r"Research Quality\s+(\d+\.?\d*)", "research_quality"),
                        (r"Industry\s+(\d+\.?\d*)", "industry"),
                        (
                            r"International Outlook\s+(\d+\.?\d*)",
                            "international_outlook",
                        ),
                    ]

                    for pattern, key in patterns:
                        match = re.search(pattern, chart_text)
                        if match:
                            rankings[f"{key}_score"] = match.group(1)

            return rankings

        except Exception as e:
            logger.debug(f"Failed to extract main rankings: {str(e)}")
            return {}

    def _extract_ranking_positions(self, soup) -> Dict[str, Any]:
        """Extract ranking positions from cards/tabs."""
        rankings = {}

        try:
            # Based on the image, look for the ranking cards shown with positions (1st, 2nd, 3rd)
            position_cards = soup.select(
                "div.css-q24je2, div.css-ze6z4k, div.css-ivje2h, div[role='tab'], div.chakra-card"
            )

            for card in position_cards:
                try:
                    card_text = card.get_text(strip=True, separator="\n")
                    lines = [
                        line.strip() for line in card_text.split("\n") if line.strip()
                    ]

                    if len(lines) >= 2:
                        category = lines[0]
                        position = None

                        # Look for a position indicator like 1st, 2nd, etc.
                        for line in lines[1:]:
                            position_match = re.search(r"(\d+(?:st|nd|rd|th))", line)
                            if position_match:
                                position = position_match.group(1)
                                break

                        if category and position:
                            key = self._clean_ranking_key(category)
                            # Clean position to just the number
                            clean_position = re.sub(r"(st|nd|rd|th)$", "", position)
                            rankings[f"{key}_rank"] = clean_position
                except Exception:
                    continue

            return rankings

        except Exception as e:
            logger.debug(f"Failed to extract ranking positions: {str(e)}")
            return {}

    def _extract_section_rankings(self, soup) -> Dict[str, Any]:
        """Extract rankings from specific sections of the page."""
        rankings = {}

        try:
            # Look for the ranking section specifically
            # Based on the image, there are multiple ranking sections
            ranking_sections = soup.select(
                "div.rankings-section, div.css-ejuz3m > div:nth-child(1), section:has(h2:contains('Rankings'))"
            )

            for section in ranking_sections:
                # Extract section text to analyze
                section_text = section.get_text(strip=True, separator="\n")

                # Skip sections without ranking data
                if not re.search(
                    r"rank|position|#|\d+(?:st|nd|rd|th)", section_text, re.IGNORECASE
                ):
                    continue

                # Look for structured data elements
                rank_items = section.select("div.css-11m5q9m, div.css-1dvz8m0")

                for item in rank_items:
                    text = item.get_text(strip=True, separator="\n")
                    lines = [line.strip() for line in text.split("\n") if line.strip()]

                    if len(lines) >= 2:
                        label = lines[0]
                        value = lines[1]

                        key = self._clean_ranking_key(label)

                        # Determine if this is a score or a rank
                        if (
                            re.match(r"^[\d\.]+$", value)
                            and float(value) > 0
                            and float(value) <= 100
                        ):
                            rankings[f"{key}_score"] = value
                        else:
                            # Clean position suffix (st, nd, rd, th)
                            clean_value = re.sub(r"(st|nd|rd|th)$", "", value)
                            rankings[f"{key}_rank"] = clean_value

            return rankings

        except Exception as e:
            logger.debug(f"Failed to extract section rankings: {str(e)}")
            return {}

    def _parse_ranking_container(self, container) -> Dict[str, Any]:
        """Parse ranking information from a container element."""
        rank_data = {}

        try:
            # Extract all potential ranking data from the container

            # 1. Look for structured ranking items
            rank_items = container.select("div.css-11m5q9m, div.css-1dvz8m0")

            for item in rank_items:
                text = item.get_text(strip=True, separator="\n")
                lines = [line.strip() for line in text.split("\n") if line.strip()]

                if len(lines) >= 2:
                    label = lines[0]
                    value = lines[1]

                    # Extract ranking data if this looks like ranking information
                    if (
                        "rank" in label.lower()
                        or "position" in label.lower()
                        or re.match(r"\d+(?:st|nd|rd|th)", value)
                    ):
                        key = self._clean_ranking_key(label)

                        # Determine if score or rank
                        if (
                            re.match(r"^[\d\.]+$", value)
                            and float(value) > 0
                            and float(value) <= 100
                        ):
                            rank_data[f"{key}_score"] = value
                        else:
                            # Clean position suffix (st, nd, rd, th)
                            clean_value = re.sub(r"(st|nd|rd|th)$", "", value)
                            rank_data[f"{key}_rank"] = clean_value

            # 2. If no structured data found, try extracting from container text
            if not rank_data:
                container_text = container.get_text(strip=True, separator="\n")

                # Look for common ranking patterns
                patterns = [
                    # Find "Label: Value" patterns
                    (
                        r"([^:\n]+):\s*([^\n]+)",
                        lambda m: (m.group(1).strip(), m.group(2).strip()),
                    ),
                    # Find "Label = Value" patterns
                    (
                        r"([^=\n]+)=\s*([^\n]+)",
                        lambda m: (m.group(1).strip(), m.group(2).strip()),
                    ),
                ]

                for pattern, extract in patterns:
                    matches = re.finditer(pattern, container_text)
                    for match in matches:
                        label, value = extract(match)

                        if "rank" in label.lower() or "position" in label.lower():
                            key = self._clean_ranking_key(label)

                            # Determine if score or rank
                            if (
                                re.match(r"^[\d\.]+$", value)
                                and float(value) > 0
                                and float(value) <= 100
                            ):
                                rank_data[f"{key}_score"] = value
                            else:
                                # Clean position suffix
                                clean_value = re.sub(r"(st|nd|rd|th)$", "", value)
                                rank_data[f"{key}_rank"] = clean_value

        except Exception as e:
            logger.debug(f"Failed to parse ranking container: {str(e)}")

        return rank_data

    def _extract_individual_rankings(self, soup) -> Dict[str, Any]:
        """Extract ranking data from individual elements."""
        ranking_data = {}

        try:
            # 1. Extract from span elements with ranking information
            rank_elements = soup.select("span.barlabel-text, span.barlabel-score")

            for element in rank_elements:
                text = element.get_text(strip=True)
                is_score = "score" in element.get("class", [])

                # Handle different text formats
                if "=" in text:
                    parts = text.split("=", 1)
                    label = parts[0].strip()
                    value = parts[1].strip()

                    key = self._clean_ranking_key(label)
                    suffix = "score" if is_score else "rank"
                    ranking_data[f"{key}_{suffix}"] = value
                else:
                    # If just a number, classify based on the element class
                    if re.match(r"^[\d\.]+$", text):
                        key = "overall" if is_score else "rank"
                        suffix = "score" if is_score else "rank"
                        ranking_data[f"{key}_{suffix}"] = text

            # 2. Look for structured ranking data in the entire page
            # Focus on elements that are likely to contain ranking information
            potential_elements = soup.select(
                "div.css-11m5q9m, div.css-1dvz8m0, div[role='row'], tr:has(td.ranking-label)"
            )

            for element in potential_elements:
                text = element.get_text(strip=True, separator="\n")
                lines = [line.strip() for line in text.split("\n") if line.strip()]

                if len(lines) >= 2:
                    label = lines[0]
                    value = lines[1]

                    # Filter for ranking-related information
                    if "rank" in label.lower() or re.match(
                        r"\d+(?:st|nd|rd|th)", value
                    ):
                        key = self._clean_ranking_key(label)

                        # Determine if score or rank
                        if (
                            re.match(r"^[\d\.]+$", value)
                            and float(value) > 0
                            and float(value) <= 100
                        ):
                            ranking_data[f"{key}_score"] = value
                        else:
                            # Clean position suffix
                            clean_value = re.sub(r"(st|nd|rd|th)$", "", value)
                            ranking_data[f"{key}_rank"] = clean_value

        except Exception as e:
            logger.debug(f"No individual rankings found: {str(e)}")

        return ranking_data

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

    def _extract_key_stats(self, soup) -> Dict[str, Any]:
        """Extract key statistics from the university page."""
        stats = {}

        try:
            # First look for a stats section with heading
            key_stats_section = soup.find(
                string=re.compile("Key Student Statistics", re.IGNORECASE)
            )
            if key_stats_section:
                # Find the container that holds this section
                stats_container = key_stats_section.find_parent(
                    "div", {"data-testid": re.compile("profiles-section-wrapper")}
                )
                if stats_container:
                    logger.info("Found key stats section by heading")
                    stats.update(self._extract_stats_from_container(stats_container))

            # If no stats found by heading, try direct extraction based on the images
            if not stats:
                # Match the exact structure seen in the images
                # Find student total, gender ratio, etc.

                # Student total
                student_total_elem = soup.find(string=re.compile("Student total"))
                if student_total_elem:
                    student_total_value = student_total_elem.find_next("div")
                    if student_total_value:
                        stats["student_total"] = student_total_value.text.strip()

                # Gender ratio
                gender_ratio_elem = soup.find(string=re.compile("Student gender ratio"))
                if gender_ratio_elem:
                    gender_ratio_value = gender_ratio_elem.find_next("div")
                    if gender_ratio_value:
                        stats["student_gender_ratio"] = gender_ratio_value.text.strip()

                # International students
                intl_students_elem = soup.find(
                    string=re.compile("International student percentage")
                )
                if intl_students_elem:
                    intl_students_value = intl_students_elem.find_next("div")
                    if intl_students_value:
                        stats["international_student_percentage"] = (
                            intl_students_value.text.strip()
                        )

                # Students per staff
                students_staff_elem = soup.find(string=re.compile("Students per staff"))
                if students_staff_elem:
                    students_staff_value = students_staff_elem.find_next("div")
                    if students_staff_value:
                        stats["students_per_staff"] = students_staff_value.text.strip()

            # Additional backup approach - find all the div elements with stats
            if not stats:
                # Try the updated selectors for stats containers
                stats_containers = soup.select(
                    "div[data-testid='keyStats'], div[id='keyStats'], div[data-testid='profiles-section-wrapper']"
                )

                for container in stats_containers:
                    stats.update(self._extract_stats_from_container(container))

            logger.info(f"Extracted {len(stats)} key stats")
            return stats

        except Exception as e:
            logger.warning(f"Failed to extract key stats: {str(e)}")
            return {}

    def _extract_stats_from_container(self, container) -> Dict[str, Any]:
        """Extract statistics from a container element."""
        stats = {}

        try:
            # Pattern matching the stats layout in the images
            # Look for div pairs where first contains label and second contains value

            # First try with specific class names seen in images
            div_pairs = container.select("div.css-11m5q9m, div.css-1dvz8m0")

            for div in div_pairs:
                text = div.get_text(strip=True, separator="\n")
                lines = [line.strip() for line in text.split("\n") if line.strip()]

                if len(lines) >= 2:
                    key = re.sub(r"[^a-zA-Z0-9\s]", "", lines[0].lower()).replace(
                        " ", "_"
                    )
                    value = lines[1]
                    stats[key] = value

            # If no stats found with class selectors, try a more general approach
            if not stats:
                # Get all direct text nodes with specific formats "Label Value" patterns
                for div in container.find_all("div"):
                    text = div.get_text(strip=True)

                    if "Student total" in text:
                        match = re.search(r"Student total\s*([\d,]+)", text)
                        if match:
                            stats["student_total"] = match.group(1)

                    elif "gender ratio" in text.lower():
                        match = re.search(
                            r"gender ratio\s*([^\n]+)", text, re.IGNORECASE
                        )
                        if match:
                            stats["student_gender_ratio"] = match.group(1)

                    elif "International student" in text:
                        match = re.search(
                            r"International student percentage\s*(\d+%)", text
                        )
                        if match:
                            stats["international_student_percentage"] = match.group(1)

        except Exception as e:
            logger.debug(f"Failed to extract stats from container: {str(e)}")

        return stats

    def _extract_subjects_data(self, soup) -> List[Dict[str, Any]]:
        """Extract subject rankings and information."""
        subjects = []

        try:
            # First look for the subjects section by heading
            subjects_heading = soup.find(
                string=re.compile("Subjects Taught", re.IGNORECASE)
            )
            subjects_container = None

            if subjects_heading:
                # Find the container that holds all the subjects
                subjects_container = subjects_heading.find_parent(
                    "div", {"data-testid": re.compile("profiles-section-wrapper")}
                )

            # If no container found by heading, try direct selectors
            if not subjects_container:
                subjects_container = soup.select_one(
                    "div[data-testid='profiles-section-wrapper'][id='subjects'], div[data-testid='subjects']"
                )

            # Process the container if found
            if subjects_container:
                logger.info("Found subjects container")

                # Find all category headings (h3 elements) within the container
                # Based on the images, they have class css-1vd75my
                category_headers = subjects_container.select("h3.css-1vd75my, h3")

                for header in category_headers:
                    category_name = header.text.strip()
                    if category_name:
                        # Find the list that follows this heading
                        # In the image, we see ul with class css-19cj1d2
                        subject_list = header.find_next("ul", class_="css-19cj1d2")

                        # If class-specific search fails, try any ul
                        if not subject_list:
                            subject_list = header.find_next("ul")

                        if subject_list:
                            # Get all list items
                            for item in subject_list.select("li"):
                                subject_name = item.text.strip()
                                if subject_name:
                                    subjects.append(
                                        {
                                            "category": category_name,
                                            "name": subject_name,
                                        }
                                    )

            # If still no subjects, try an alternative approach
            if not subjects:
                # Direct extraction based on the image structure
                # Get the potential subjects section by direct selectors
                subject_sections = soup.select("div.css-ejuz3m")

                for section in subject_sections:
                    # Look for h3 headings (these are the categories in the image)
                    headers = section.select("h3")

                for header in headers:
                    category = header.text.strip()
                    if category:
                        # Get the next ul after this h3
                        ul = header.find_next_sibling("ul")
                        if ul:
                            # Process all li elements
                            for li in ul.select("li"):
                                subject = li.text.strip()
                                if subject:
                                    subjects.append(
                                        {"category": category, "name": subject}
                                    )

            logger.info(f"Extracted {len(subjects)} subjects")
            return subjects

        except Exception as e:
            logger.warning(f"Failed to extract subjects data: {str(e)}")
            return []


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
