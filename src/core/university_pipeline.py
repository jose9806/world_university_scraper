"""Pipeline for scraping individual university details."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


from ..scrapers.university_detail_scraper import UniversityDetailScraper
from ..parsers.university_detail_parser import UniversityDetailParser

logger = logging.getLogger(__name__)


class UniversityDetailPipeline:
    """Pipeline for scraping individual university details."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the university detail pipeline.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.scraper = UniversityDetailScraper(config.get("scraper", {}))
        self.parser = UniversityDetailParser()

        # Create output directories
        output_dir = config.get("general", {}).get("output_dir", "data/universities")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_from_rankings_data(self, rankings_file: str) -> List[Dict[str, Any]]:
        """Run pipeline using URLs from rankings data.

        Args:
            rankings_file: Path to JSON file containing rankings data with URLs

        Returns:
            List of university detail dictionaries
        """
        # Load rankings data
        university_urls = self._extract_urls_from_rankings(rankings_file)

        if not university_urls:
            logger.warning("No university URLs found in rankings data")
            return []

        logger.info(f"Found {len(university_urls)} university URLs to scrape")
        return self.run(university_urls)

    def run(self, university_urls: List[str]) -> List[Dict[str, Any]]:
        """Run the university detail pipeline.

        Args:
            university_urls: List of university detail page URLs

        Returns:
            List of university detail dictionaries
        """
        try:
            logger.info(
                f"Starting university detail scraping for {len(university_urls)} URLs"
            )

            # Filter and validate URLs
            valid_urls = self._validate_urls(university_urls)
            logger.info(
                f"Validated {len(valid_urls)} URLs out of {len(university_urls)}"
            )

            if not valid_urls:
                logger.warning("No valid URLs to process")
                return []

            # Scrape raw HTML and extract structured data for all universities
            scraped_data = self.scraper.scrape_university_details(valid_urls)

            # Process and clean the scraped data
            processed_universities = []
            for uni_data in scraped_data:
                if self._is_valid_university_data(uni_data):
                    # Apply additional parsing/cleaning if needed
                    cleaned_data = self._clean_university_data(uni_data)
                    processed_universities.append(cleaned_data)
                else:
                    logger.warning(
                        f"Invalid data for university: {uni_data.get('url', 'Unknown')}"
                    )

            # Save results
            if processed_universities:
                output_file = self._save_results(processed_universities)
                logger.info(
                    f"Successfully saved {len(processed_universities)} university details to {output_file}"
                )
            else:
                logger.warning("No valid university data to save")

            return processed_universities

        except Exception as e:
            logger.error(f"Error in university detail pipeline: {str(e)}")
            raise

    def run_batch(
        self, university_urls: List[str], batch_size: int = 50
    ) -> List[Dict[str, Any]]:
        """Run the pipeline in batches for large datasets.

        Args:
            university_urls: List of university URLs
            batch_size: Number of universities to process per batch

        Returns:
            List of all university detail dictionaries
        """
        all_results = []
        total_urls = len(university_urls)

        for i in range(0, total_urls, batch_size):
            batch_urls = university_urls[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_urls + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} URLs)"
            )

            try:
                batch_results = self.run(batch_urls)
                all_results.extend(batch_results)

                # Save intermediate results for each batch
                if batch_results:
                    self._save_batch_results(batch_results, batch_num)

            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}")
                continue

        logger.info(
            f"Completed batch processing: {len(all_results)} total universities"
        )
        return all_results

    def _extract_urls_from_rankings(self, rankings_file: str) -> List[str]:
        """Extract university URLs from rankings JSON file.

        Args:
            rankings_file: Path to rankings JSON file

        Returns:
            List of university URLs
        """
        try:
            rankings_path = Path(rankings_file)
            if not rankings_path.exists():
                logger.error(f"Rankings file not found: {rankings_file}")
                return []

            with open(rankings_path, "r", encoding="utf-8") as f:
                rankings_data = json.load(f)

            if not isinstance(rankings_data, list):
                logger.error("Rankings data should be a list of universities")
                return []

            urls = []
            for university in rankings_data:
                if not isinstance(university, dict):
                    continue

                url = university.get("university_url")
                if url and isinstance(url, str) and url.startswith("http"):
                    urls.append(url)

            logger.info(
                f"Extracted {len(urls)} valid URLs from {len(rankings_data)} rankings entries"
            )
            return urls

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rankings file: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Failed to extract URLs from rankings file: {str(e)}")
            return []

    def _validate_urls(self, urls: List[str]) -> List[str]:
        """Validate and filter university URLs.

        Args:
            urls: List of URLs to validate

        Returns:
            List of valid URLs
        """
        valid_urls = []

        for url in urls:
            if not isinstance(url, str):
                continue

            url = url.strip()

            # Basic URL validation
            if not url.startswith("http"):
                logger.debug(f"Invalid URL format: {url}")
                continue

            # Check if it's a THE university page
            if "timeshighereducation.com" not in url:
                logger.debug(f"Not a THE URL: {url}")
                continue

            # Check if it looks like a university detail page
            if "/world-university-rankings/" not in url:
                logger.debug(f"Not a university detail URL: {url}")
                continue

            valid_urls.append(url)

        return valid_urls

    def _is_valid_university_data(self, uni_data: Dict[str, Any]) -> bool:
        """Check if university data is valid and complete enough.

        Args:
            uni_data: University data dictionary

        Returns:
            True if data is valid, False otherwise
        """
        if not isinstance(uni_data, dict):
            return False

        # Check for error indicator
        if "error" in uni_data:
            return False

        # Check for required fields
        required_fields = ["url", "name"]
        for field in required_fields:
            if not uni_data.get(field):
                logger.debug(f"Missing required field '{field}' in university data")
                return False

        return True

    def _clean_university_data(self, uni_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize university data.

        Args:
            uni_data: Raw university data

        Returns:
            Cleaned university data
        """
        cleaned_data = uni_data.copy()

        # Ensure name is cleaned
        if "name" in cleaned_data:
            cleaned_data["name"] = cleaned_data["name"].strip()

        # Ensure URL is cleaned
        if "url" in cleaned_data:
            cleaned_data["url"] = cleaned_data["url"].strip()

        # Clean ranking data
        if "ranking_data" in cleaned_data and isinstance(
            cleaned_data["ranking_data"], dict
        ):
            cleaned_ranking = {}
            for key, value in cleaned_data["ranking_data"].items():
                if value is not None and str(value).strip():
                    cleaned_ranking[key] = str(value).strip()
            cleaned_data["ranking_data"] = cleaned_ranking

        # Clean key stats
        if "key_stats" in cleaned_data and isinstance(cleaned_data["key_stats"], dict):
            cleaned_stats = {}
            for key, value in cleaned_data["key_stats"].items():
                if value is not None and str(value).strip():
                    cleaned_stats[key] = str(value).strip()
            cleaned_data["key_stats"] = cleaned_stats

        # Clean subjects data
        if "subjects" in cleaned_data and isinstance(cleaned_data["subjects"], list):
            cleaned_subjects = []
            for subject in cleaned_data["subjects"]:
                if isinstance(subject, dict) and subject.get("name"):
                    cleaned_subjects.append(subject)
            cleaned_data["subjects"] = cleaned_subjects

        return cleaned_data

    def _save_results(self, universities: List[Dict[str, Any]]) -> Path:
        """Save university results to JSON file.

        Args:
            universities: List of university data dictionaries

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"universities_detail_{timestamp}.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(universities, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(universities)} universities to {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise

    def _save_batch_results(
        self, universities: List[Dict[str, Any]], batch_num: int
    ) -> Path:
        """Save batch results to JSON file.

        Args:
            universities: List of university data dictionaries
            batch_num: Batch number

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = (
            self.output_dir / f"universities_batch_{batch_num}_{timestamp}.json"
        )

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(universities, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Saved batch {batch_num} with {len(universities)} universities to {output_file}"
            )
            return output_file

        except Exception as e:
            logger.error(f"Failed to save batch results: {str(e)}")
            raise

    def get_summary_stats(self, universities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for scraped universities.

        Args:
            universities: List of university data dictionaries

        Returns:
            Dictionary containing summary statistics
        """
        if not universities:
            return {"total": 0}

        stats = {
            "total": len(universities),
            "with_ranking_data": 0,
            "with_key_stats": 0,
            "with_subjects": 0,
            "countries": set(),
            "subjects_covered": set(),
        }

        for uni in universities:
            if uni.get("ranking_data"):
                stats["with_ranking_data"] += 1

            if uni.get("key_stats"):
                stats["with_key_stats"] += 1

            if uni.get("subjects"):
                stats["with_subjects"] += 1
                for subject in uni["subjects"]:
                    if subject.get("name"):
                        stats["subjects_covered"].add(subject["name"])

            # Extract country from additional_info if available
            additional_info = uni.get("additional_info", {})
            location = additional_info.get("location", "")
            if location:
                # Simple heuristic to extract country (last part after comma)
                country = location.split(",")[-1].strip()
                if country:
                    stats["countries"].add(country)

        # Convert sets to counts for JSON serialization
        stats["unique_countries"] = len(stats["countries"])
        stats["unique_subjects"] = len(stats["subjects_covered"])
        del stats["countries"]
        del stats["subjects_covered"]

        return stats
