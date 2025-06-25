"""Scraping pipeline for university rankings data."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from .exceptions import ScraperException, ParserException
from ..scrapers.base_scraper import BaseScraper
from ..scrapers.selenium_rankings_scraper import SeleniumRankingsScraper
from ..scrapers.rankings_scraper import RankingsScraper
from ..parsers.rankings_parser import RankingsParser

logger = logging.getLogger(__name__)


class ScrapingPipeline:
    """Pipeline to orchestrate scraping, parsing, and data processing."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the scraping pipeline with configuration.

        Args:
            config: Dictionary containing configuration settings
        """
        self.config = config
        self.scraper = self._create_scraper()
        self.parser = self._create_parser()

        # 🔥 OBTENER LÍMITE DE CONFIGURACIÓN
        self.limit = config.get("scraper", {}).get("limit")

        # Create output directories
        output_dir = self.config.get("general", {}).get("output_dir", "data/raw")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _create_scraper(self) -> BaseScraper | SeleniumRankingsScraper:
        """Create and configure the appropriate scraper based on configuration.

        Returns:
            Configured scraper instance
        """
        scraper_config = self.config.get("scraper", {})
        scraper_type = scraper_config.get("type", "basic")

        if scraper_type == "selenium":
            logger.info("Creating Selenium-based scraper")

            # Combine scraper and selenium configs
            selenium_config = self.config.get("selenium", {})
            combined_config = {**scraper_config, **selenium_config}

            return SeleniumRankingsScraper(combined_config)
        else:
            logger.info("Creating standard HTTP scraper")
            return RankingsScraper(scraper_config)

    def _create_parser(self):
        """Create and configure the appropriate parser based on configuration.

        Returns:
            Configured parser instance
        """
        parser_config = self.config.get("parser", {})
        parser_type = parser_config.get("type", "rankings")

        if parser_type == "rankings":
            return RankingsParser()
        else:
            # Add other parser types if needed
            return RankingsParser()

    def run(self):
        """Run the complete scraping pipeline."""
        try:
            # Get scraping parameters
            rankings_config = self.config.get("scraper", {}).get("rankings", {})
            year = rankings_config.get("year", "2025")
            view = rankings_config.get("view", "reputation")

            logger.info(f"Starting scraping for year {year}, view {view}")
            if self.limit:
                logger.info(f"🎯 Limiting to {self.limit} universities")

            # For Selenium scraper, use the specific scrape_rankings method
            if isinstance(self.scraper, SeleniumRankingsScraper):
                html_content = self.scraper.scrape_rankings(year=year, view=view)
            else:
                # For basic scraper, construct URL and call make_request
                base_url = self.config.get("scraper", {}).get("base_url", "")
                url = f"{base_url}/{year}/world-ranking/results?view={view}"
                html_content = self.scraper._make_request(url)

            # Save raw HTML if configured to do so
            if self.config.get("selenium", {}).get("save_html", False):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_path = self.output_dir / f"rankings_{year}_{view}_{timestamp}.html"

                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved raw HTML to {html_path}")

            # Parse the data
            logger.info("Parsing scraped content")
            universities = self.parser.parse(html_content)

            # 🔥 APLICAR LÍMITE SI ESTÁ CONFIGURADO
            if self.limit and len(universities) > self.limit:
                universities = universities[: self.limit]
                logger.info(f"🎯 Limited results to {len(universities)} universities")

            # Save the parsed data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = self.output_dir / f"rankings_{year}_{view}_{timestamp}.json"

            # Import json in the method to avoid circular imports
            import json

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(universities, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Successfully scraped and saved data for {len(universities)} universities"
            )

            # 🔥 DEVOLVER DICCIONARIO CON DATOS Y RUTA DEL ARCHIVO
            return {
                "success": True,
                "data": universities,
                "output_file": str(json_path),
                "total_universities": len(universities),
                "year": year,
                "view": view,
            }

        except (ScraperException, ParserException) as e:
            logger.error(f"Error during scraping/parsing: {str(e)}")
            return {"success": False, "error": str(e), "output_file": None}
        except Exception as e:
            logger.exception(f"Unexpected error in pipeline: {str(e)}")
            return {"success": False, "error": str(e), "output_file": None}
