#!/usr/bin/env python3
"""Script to scrape individual university details."""

import argparse
import logging
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import load_config
from src.core.university_pipeline import UniversityDetailPipeline


def setup_logging(log_level: str, log_file: str = "logs/university_scraper.log"):
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_urls_from_file(file_path: str) -> list[str]:
    """Load URLs from a text file (one URL per line)."""
    urls = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url and not url.startswith("#"):  # Skip empty lines and comments
                    urls.append(url)
        return urls
    except Exception as e:
        logging.error(f"Failed to load URLs from file {file_path}: {str(e)}")
        return []


def save_summary_report(universities: list, output_dir: str):
    """Save a summary report of the scraping results."""
    if not universities:
        return

    pipeline = UniversityDetailPipeline({})  # Dummy pipeline for stats
    stats = pipeline.get_summary_stats(universities)

    # Create summary report
    report = {
        "scraping_summary": stats,
        "sample_universities": universities[:3],  # First 3 as examples
        "universities_with_errors": [uni for uni in universities if "error" in uni][
            :5
        ],  # First 5 errors
    }

    report_file = Path(output_dir) / "scraping_summary.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logging.info(f"Summary report saved to {report_file}")

    # Print summary to console
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total universities processed: {stats['total']}")
    print(f"With ranking data: {stats['with_ranking_data']}")
    print(f"With key statistics: {stats['with_key_stats']}")
    print(f"With subject data: {stats['with_subjects']}")
    print(f"Unique countries: {stats['unique_countries']}")
    print(f"Unique subjects: {stats['unique_subjects']}")
    print("=" * 50)


def main():
    """Run university detail scraping."""
    parser = argparse.ArgumentParser(
        description="University Detail Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape from rankings file
  python scripts/scrape_universities.py --rankings-file data/raw/rankings_2025_reputation.json
  
  # Scrape from URL list file
  python scripts/scrape_universities.py --urls-file university_urls.txt
  
  # Scrape specific URLs with batch processing
  python scripts/scrape_universities.py --urls-file urls.txt --batch-size 25
  
  # Test with limited universities
  python scripts/scrape_universities.py --rankings-file rankings.json --limit 10
        """,
    )

    # Input source arguments (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--rankings-file",
        type=str,
        help="Path to rankings JSON file containing university URLs",
    )
    source_group.add_argument(
        "--urls-file",
        type=str,
        help="Path to text file containing university URLs (one per line)",
    )

    # Configuration arguments
    parser.add_argument(
        "--config",
        type=str,
        default="config/university_detail.yml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Processing options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of universities to process per batch (0 = no batching)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of universities to process (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without actually scraping",
    )
    parser.add_argument(
        "--output-dir", type=str, help="Override output directory from config"
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

        # Override output directory if specified
        if args.output_dir:
            config.setdefault("general", {})["output_dir"] = args.output_dir

        # Initialize pipeline
        pipeline = UniversityDetailPipeline(config)

        # Determine source of URLs
        # Determine source of URLs
        urls = []
        if args.rankings_file:
            logger.info(f"Loading URLs from rankings file: {args.rankings_file}")
            urls = pipeline._extract_urls_from_rankings(args.rankings_file)
        elif args.urls_file:
            logger.info(f"Loading URLs from file: {args.urls_file}")
            urls = load_urls_from_file(args.urls_file)

        if not urls:
            logger.error("No URLs found to process")
            if args.rankings_file:
                logger.error(
                    f"Check that {args.rankings_file} contains valid university URLs"
                )
            sys.exit(1)

        # Apply limit if specified
        if args.limit:
            urls = urls[: args.limit]
            logger.info(f"Limited to first {len(urls)} universities")

        logger.info(f"Found {len(urls)} universities to process")

        # Dry run - just show what would be processed
        if args.dry_run:
            print(f"\nDRY RUN - Would process {len(urls)} universities:")
            for i, url in enumerate(urls[:10], 1):  # Show first 10
                print(f"  {i}. {url}")
            if len(urls) > 10:
                print(f"  ... and {len(urls) - 10} more")
            return

        # Run scraping
        if args.batch_size > 0 and len(urls) > args.batch_size:
            logger.info(f"Using batch processing with batch size: {args.batch_size}")
            results = pipeline.run_batch(urls, args.batch_size)
        else:
            logger.info("Processing all URLs in a single batch")
            results = pipeline.run(urls)

        # Generate summary report
        output_dir = config.get("general", {}).get("output_dir", "data/universities")
        save_summary_report(results, output_dir)

        logger.info(
            f"Scraping completed successfully: {len(results)} universities processed"
        )

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
