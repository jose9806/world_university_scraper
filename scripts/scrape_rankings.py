#!/usr/bin/env python3
"""Script to scrape THE World University Rankings."""

import argparse
import logging
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import load_config
from src.core.pipeline import ScrapingPipeline
from src.processors.data_processor import DataProcessor
from src.storage.file_storage import FileStorage


def setup_logging(log_level: str, log_file: str = "logs/rankings_scraper.log"):
    """Set up logging configuration."""
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def save_rankings_summary(data: list, output_dir: str):
    """Save a summary of the rankings data."""
    if not data:
        return

    summary = {
        "total_universities": len(data),
        "countries": len(
            set(uni.get("country", "") for uni in data if uni.get("country"))
        ),
        "with_urls": len([uni for uni in data if uni.get("university_url")]),
        "top_10": data[:10] if len(data) >= 10 else data,
        "score_ranges": {
            "overall_score": {
                "min": min(
                    (uni.get("overall_score", 0) or 0 for uni in data), default=0
                ),
                "max": max(
                    (uni.get("overall_score", 0) or 0 for uni in data), default=0
                ),
            }
        },
        "scrape_timestamp": datetime.now().isoformat(),
    }

    summary_file = Path(output_dir) / "rankings_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logging.info(f"Rankings summary saved to {summary_file}")

    # Print summary to console
    print("\n" + "=" * 50)
    print("RANKINGS SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total universities: {summary['total_universities']}")
    print(f"Countries represented: {summary['countries']}")
    print(f"Universities with detail URLs: {summary['with_urls']}")
    print(
        f"Success rate: {(summary['with_urls']/summary['total_universities']*100):.1f}%"
    )
    print("=" * 50)


def main():
    """Run the rankings scraper."""
    parser = argparse.ArgumentParser(
        description="THE World University Rankings Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scraping with default config
  python scripts/scrape_rankings.py
  
  # Custom configuration and year
  python scripts/scrape_rankings.py --config config/custom.yml --year 2025 --view reputation
  
  # Include data processing
  python scripts/scrape_rankings.py --process-data --save-pickle
  
  # Debug mode with detailed logging
  python scripts/scrape_rankings.py --log-level DEBUG --save-html
        """,
    )

    # Configuration arguments
    parser.add_argument(
        "--config",
        type=str,
        default="config/default_selenium.yml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Scraping parameters
    parser.add_argument(
        "--year", type=str, help="Ranking year to scrape (overrides config)"
    )
    parser.add_argument(
        "--view", type=str, help="Ranking view to scrape (overrides config)"
    )

    # Output options
    parser.add_argument(
        "--output-dir", type=str, help="Output directory (overrides config)"
    )
    parser.add_argument(
        "--save-html", action="store_true", help="Save raw HTML content"
    )
    parser.add_argument(
        "--no-json", action="store_true", help="Skip saving JSON output"
    )

    # Processing options
    parser.add_argument(
        "--process-data",
        action="store_true",
        help="Process the scraped data with DataProcessor",
    )
    parser.add_argument(
        "--save-pickle", action="store_true", help="Save processed data as pickle file"
    )

    # Testing options
    parser.add_argument(
        "--dry-run", action="store_true", help="Show configuration without scraping"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {args.config}")
            sys.exit(1)

        config = load_config(config_path)

        # Override config parameters if provided
        if args.year or args.view:
            rankings_config = config.setdefault("scraper", {}).setdefault(
                "rankings", {}
            )
            if args.year:
                rankings_config["year"] = args.year
            if args.view:
                rankings_config["view"] = args.view

        if args.output_dir:
            config.setdefault("general", {})["output_dir"] = args.output_dir

        if args.save_html:
            config.setdefault("selenium", {})["save_html"] = True

        # Show configuration in dry run mode
        if args.dry_run:
            print("Configuration:")
            print(json.dumps(config, indent=2))
            print("\nWould scrape:")
            rankings_config = config.get("scraper", {}).get("rankings", {})
            print(f"  Year: {rankings_config.get('year', '2025')}")
            print(f"  View: {rankings_config.get('view', 'reputation')}")
            print(
                f"  Output: {config.get('general', {}).get('output_dir', 'data/raw')}"
            )
            return

        # Initialize pipeline
        pipeline = ScrapingPipeline(config)

        # Run scraping
        logger.info("Starting rankings scraping...")
        universities = pipeline.run()

        if not universities:
            logger.error("No data was scraped")
            sys.exit(1)

        logger.info(f"Successfully scraped {len(universities)} universities")

        # Save JSON (unless disabled)
        if not args.no_json:
            output_dir = config.get("general", {}).get("output_dir", "data/raw")
            save_rankings_summary(universities, output_dir)

        # Process data if requested
        if args.process_data:
            logger.info("Processing scraped data...")
            processor = DataProcessor(config.get("processor", {}))
            processed_df = processor.process(universities)

            logger.info(f"Processed data shape: {processed_df.shape}")

            # Save processed data
            if args.save_pickle:
                storage = FileStorage(config.get("storage", {}))
                processed_file = storage.save_processed_data(processed_df)
                logger.info(f"Processed data saved to: {processed_file}")

        logger.info("Rankings scraping completed successfully")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
