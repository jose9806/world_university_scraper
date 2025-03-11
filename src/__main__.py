"""Command-line interface for university rankings scraper."""

import argparse
import logging
import sys
from pathlib import Path

from core.config import load_config
from core.pipeline import ScrapingPipeline


def main():
    """Run the university rankings scraper."""
    parser = argparse.ArgumentParser(description="University Rankings Scraper")
    parser.add_argument(
        "--config",
        type=str,
        default="config/default.yml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/scraper.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting university rankings scraper with config: {args.config}")

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)

    config = load_config(config_path)

    # Run pipeline
    pipeline = ScrapingPipeline(config)
    pipeline.run()

    logger.info("Scraping completed successfully")


if __name__ == "__main__":
    main()
