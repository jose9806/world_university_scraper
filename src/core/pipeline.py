# src/university_rankings/core/pipeline.py
"""Core pipeline for the scraping process."""

import logging
import os
from typing import Dict, Any

from scrapers.rankings_scraper import RankingsScraper
from parsers.rankings_parser import RankingsParser
from processors.data_processor import DataProcessor
from exporters.exporter_factory import create_exporter
from storage.file_storage import FileStorage
from utils.exceptions import ExporterException

logger = logging.getLogger(__name__)


class ScrapingPipeline:
    """Orchestrates the scraping, parsing, processing, and database export process."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the pipeline with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.scraper = RankingsScraper(config["scraper"])
        self.parser = RankingsParser()
        self.processor = DataProcessor(config.get("processor", {}))
        self.storage = FileStorage(config["storage"])

        # Initialize database exporter if enabled
        self.db_exporter = None
        if config.get("database", {}).get("enabled", False):
            self._setup_database_exporter()

    def _setup_database_exporter(self):
        """Set up the database exporter based on configuration."""
        db_config = self.config.get("database", {})
        exporter_type = db_config.get("exporter_type", "postgres")

        try:
            logger.info(f"Setting up {exporter_type} exporter")
            self.db_exporter = create_exporter(exporter_type, self.config)
        except ExporterException as e:
            logger.error(f"Failed to initialize database exporter: {e}")
            self.db_exporter = None

    def run(self):
        """Execute the complete pipeline."""
        logger.info("Starting scraping pipeline")

        # 1. Scrape the data
        raw_data = self.scraper.scrape()

        # Save raw data if configured
        if self.config.get("storage", {}).get("save_raw_data", True):
            self.storage.save_raw_data(raw_data)

        # 2. Parse the data
        parsed_data = self.parser.parse(raw_data)

        # 3. Process the data
        processed_data = self.processor.process(parsed_data)

        # Save processed data if configured
        if self.config.get("storage", {}).get("save_processed_data", True):
            self.storage.save_processed_data(processed_data)

        # 4. Export data to database if enabled
        if self.db_exporter:
            try:
                success = self.db_exporter.export(processed_data)
                if success:
                    logger.info("Data successfully exported to database")
                else:
                    logger.warning("Database export completed with warnings")
            except Exception as e:
                logger.error(f"Failed to export data to database: {e}")

        logger.info("Pipeline completed successfully")
