"""Main orchestrator for the World University Scraper system."""

import argparse
import logging
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

from .core.config import load_config
from .processors.data_processor import DataProcessor
from .exporters.exporter_factory import create_exporter
from .storage.file_storage import FileStorage


def setup_logging(log_level: str, log_file: str = "logs/main_orchestrator.log"):
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


def run_rankings_scraper(config_file: str, **kwargs) -> str:
    """Run the rankings scraper and return the output file path."""
    logger = logging.getLogger(__name__)
    logger.info("Starting rankings scraper...")

    # Build command
    cmd = [
        sys.executable,
        "scripts/scrape_rankings.py",
        "--config",
        config_file,
        "--process-data",
        "--save-pickle",
    ]

    # Add optional arguments
    if kwargs.get("year"):
        cmd.extend(["--year", kwargs["year"]])
    if kwargs.get("view"):
        cmd.extend(["--view", kwargs["view"]])
    if kwargs.get("log_level"):
        cmd.extend(["--log-level", kwargs["log_level"]])
    if kwargs.get("output_dir"):
        cmd.extend(["--output-dir", kwargs["output_dir"]])

    # Run subprocess
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Rankings scraper completed successfully")

        # Parse output to find the JSON file path
        output_lines = result.stdout.split("\n")
        json_file = None
        for line in output_lines:
            if "rankings_" in line and ".json" in line and "saved" in line.lower():
                # Extract file path from log message
                parts = line.split()
                for part in parts:
                    if part.endswith(".json") and "rankings_" in part:
                        json_file = part
                        break
                break

        return json_file

    except subprocess.CalledProcessError as e:
        logger.error(f"Rankings scraper failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise


def run_university_scraper(rankings_file: str, config_file: str, **kwargs) -> str:
    """Run the university detail scraper and return the output file path."""
    logger = logging.getLogger(__name__)
    logger.info("Starting university detail scraper...")

    # Build command
    cmd = [
        sys.executable,
        "scripts/scrape_universities.py",
        "--rankings-file",
        rankings_file,
        "--config",
        config_file,
    ]

    # Add optional arguments
    if kwargs.get("log_level"):
        cmd.extend(["--log-level", kwargs["log_level"]])
    if kwargs.get("batch_size"):
        cmd.extend(["--batch-size", str(kwargs["batch_size"])])
    if kwargs.get("limit"):
        cmd.extend(["--limit", str(kwargs["limit"])])
    if kwargs.get("output_dir"):
        cmd.extend(["--output-dir", kwargs["output_dir"]])

    # Run subprocess
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("University detail scraper completed successfully")

        # Parse output to find the JSON file path
        output_lines = result.stdout.split("\n")
        json_file = None
        for line in output_lines:
            if "universities_detail_" in line and ".json" in line:
                parts = line.split()
                for part in parts:
                    if part.endswith(".json") and "universities_detail_" in part:
                        json_file = part
                        break
                break

        return json_file

    except subprocess.CalledProcessError as e:
        logger.error(f"University detail scraper failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise


def run_full_pipeline(config: dict, **kwargs):
    """Run the complete scraping and processing pipeline."""
    logger = logging.getLogger(__name__)
    logger.info("Starting full pipeline execution...")

    results = {
        "start_time": datetime.now().isoformat(),
        "rankings_file": None,
        "universities_file": None,
        "processed_files": [],
        "exported_to": [],
        "errors": [],
    }

    try:
        # Step 1: Rankings scraping
        logger.info("Step 1/4: Scraping university rankings...")
        rankings_config = config.get("rankings_config", "config/default_selenium.yml")

        rankings_file = run_rankings_scraper(
            rankings_config,
            year=kwargs.get("year"),
            view=kwargs.get("view"),
            log_level=kwargs.get("log_level"),
            output_dir=kwargs.get("rankings_output_dir"),
        )

        if not rankings_file or not Path(rankings_file).exists():
            raise Exception("Rankings file not found after scraping")

        results["rankings_file"] = rankings_file
        logger.info(f"Rankings saved to: {rankings_file}")

        # Step 2: University details scraping
        if not kwargs.get("rankings_only", False):
            logger.info("Step 2/4: Scraping university details...")
            university_config = config.get(
                "university_config", "config/university_detail.yml"
            )

            universities_file = run_university_scraper(
                rankings_file,
                university_config,
                log_level=kwargs.get("log_level"),
                batch_size=kwargs.get("batch_size"),
                limit=kwargs.get("limit"),
                output_dir=kwargs.get("universities_output_dir"),
            )

            if universities_file:
                results["universities_file"] = universities_file
                logger.info(f"University details saved to: {universities_file}")

        # Step 3: Additional data processing
        if kwargs.get("process_data", True):
            logger.info("Step 3/4: Processing and combining data...")
            processed_files = process_combined_data(
                results["rankings_file"], results.get("universities_file"), config
            )
            results["processed_files"] = processed_files

        # Step 4: Export to external systems
        if kwargs.get("export_data", False):
            logger.info("Step 4/4: Exporting data...")
            exported = export_data(results["processed_files"], config)
            results["exported_to"] = exported

        results["end_time"] = datetime.now().isoformat()
        results["status"] = "completed"

        # Save pipeline results summary
        save_pipeline_summary(results, config)

        logger.info("Full pipeline completed successfully!")
        return results

    except Exception as e:
        results["errors"].append(str(e))
        results["status"] = "failed"
        results["end_time"] = datetime.now().isoformat()
        logger.error(f"Pipeline failed: {str(e)}")
        raise


def process_combined_data(
    rankings_file: str, universities_file: str, config: dict
) -> list:
    """Process and combine rankings and university data."""
    logger = logging.getLogger(__name__)
    processed_files = []

    try:
        # Load data
        with open(rankings_file, "r", encoding="utf-8") as f:
            rankings_data = json.load(f)

        universities_data = []
        if universities_file and Path(universities_file).exists():
            with open(universities_file, "r", encoding="utf-8") as f:
                universities_data = json.load(f)

        # Create combined dataset
        combined_data = combine_datasets(rankings_data, universities_data)

        # Process with DataProcessor
        processor = DataProcessor(config.get("processor", {}))
        processed_df = processor.process(combined_data)

        # Save processed data
        storage = FileStorage(config.get("storage", {}))
        processed_file = storage.save_processed_data(processed_df)
        processed_files.append(processed_file)

        logger.info(f"Combined data processed and saved to: {processed_file}")
        return processed_files

    except Exception as e:
        logger.error(f"Failed to process combined data: {str(e)}")
        return processed_files


def combine_datasets(rankings_data: list, universities_data: list) -> list:
    """Combine rankings and university detail data."""
    # Create lookup dictionary for university details
    uni_details = {}
    for uni in universities_data:
        url = uni.get("url", "")
        if url:
            uni_details[url] = uni

    # Combine data
    combined = []
    for ranking in rankings_data:
        # Start with ranking data
        combined_uni = ranking.copy()

        # Add university details if available
        uni_url = ranking.get("university_url")
        if uni_url and uni_url in uni_details:
            detail_data = uni_details[uni_url]

            # Add selected fields from university details
            combined_uni.update(
                {
                    "detailed_ranking_data": detail_data.get("ranking_data", {}),
                    "key_stats": detail_data.get("key_stats", {}),
                    "subjects": detail_data.get("subjects", []),
                    "additional_info": detail_data.get("additional_info", {}),
                }
            )

        combined.append(combined_uni)

    return combined


def export_data(processed_files: list, config: dict) -> list:
    """Export processed data to external systems."""
    logger = logging.getLogger(__name__)
    exported_to = []

    try:
        export_config = config.get("exporters", {})

        for file_path in processed_files:
            if not Path(file_path).exists():
                continue

            # Load processed data
            import pandas as pd

            if file_path.endswith(".pkl"):
                df = pd.read_pickle(file_path)
            else:
                continue

            # Export to configured destinations
            for export_type, export_settings in export_config.items():
                if export_settings.get("enabled", False):
                    try:
                        exporter = create_exporter(export_type, export_settings)
                        result = exporter.export(df)
                        exported_to.append(f"{export_type}: {result}")
                        logger.info(f"Data exported to {export_type}: {result}")
                    except Exception as e:
                        logger.error(f"Failed to export to {export_type}: {str(e)}")

        return exported_to

    except Exception as e:
        logger.error(f"Export process failed: {str(e)}")
        return exported_to


def save_pipeline_summary(results: dict, config: dict):
    """Save pipeline execution summary."""
    output_dir = config.get("general", {}).get("output_dir", "data/pipeline_results")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = Path(output_dir) / f"pipeline_summary_{timestamp}.json"

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logging.info(f"Pipeline summary saved to: {summary_file}")


def main():
    """Main orchestrator entry point."""
    parser = argparse.ArgumentParser(
        description="World University Scraper - Main Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  rankings-only    : Scrape only university rankings
  universities-only: Scrape only university details (requires rankings file)
  full-pipeline    : Complete scraping, processing, and export pipeline
  process-only     : Only process existing data files
  export-only      : Only export processed data

EXAMPLES:
  # Scrape only rankings
  python -m src --mode rankings-only --config config/default_selenium.yml
  
  # Full pipeline with export to PostgreSQL
  python -m src --mode full-pipeline --export-data --config config/full_pipeline.yml
  
  # University details only using existing rankings
  python -m src --mode universities-only --rankings-file data/raw/rankings.json
  
  # Process and export existing data
  python -m src --mode export-only --processed-file data/processed/rankings.pkl
        """,
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        type=str,
        choices=[
            "rankings-only",
            "universities-only",
            "full-pipeline",
            "process-only",
            "export-only",
        ],
        default="full-pipeline",
        help="Execution mode",
    )

    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file (auto-selected based on mode if not specified)",
    )
    parser.add_argument(
        "--rankings-config",
        type=str,
        help="Rankings scraper configuration (overrides config file)",
    )
    parser.add_argument(
        "--university-config",
        type=str,
        help="University scraper configuration (overrides config file)",
    )

    # Input files (for specific modes)
    parser.add_argument(
        "--rankings-file",
        type=str,
        help="Existing rankings JSON file (for universities-only mode)",
    )
    parser.add_argument(
        "--processed-file", type=str, help="Processed data file (for export-only mode)"
    )

    # Scraping parameters
    parser.add_argument("--year", type=str, help="Ranking year to scrape")
    parser.add_argument("--view", type=str, help="Ranking view to scrape")
    parser.add_argument(
        "--limit", type=int, help="Limit number of universities (for testing)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Batch size for university scraping"
    )

    # Processing and export options
    parser.add_argument(
        "--process-data", action="store_true", default=True, help="Process scraped data"
    )
    parser.add_argument(
        "--export-data",
        action="store_true",
        help="Export data to configured destinations",
    )
    parser.add_argument(
        "--rankings-only-flag",
        action="store_true",
        help="In full pipeline, scrape only rankings",
    )

    # Output options
    parser.add_argument("--output-dir", type=str, help="Base output directory")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Determine appropriate config file based on mode
        if args.config:
            config_path = Path(args.config)
        else:
            # Auto-select config based on mode
            if args.mode == "rankings-only":
                config_path = Path("config/default_selenium.yml")
            elif args.mode == "universities-only":
                config_path = Path("config/university_detail.yml")
            else:
                config_path = Path("config/full_pipeline.yml")

            logger.info(f"Auto-selected config for mode '{args.mode}': {config_path}")

        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

        config = load_config(config_path)

        # Override config with command line arguments
        if args.rankings_config:
            config["rankings_config"] = args.rankings_config
        if args.university_config:
            config["university_config"] = args.university_config
        if args.output_dir:
            config.setdefault("general", {})["output_dir"] = args.output_dir

        # Execute based on mode
        if args.mode == "rankings-only":
            logger.info("Mode: Rankings-only scraping")

            # For rankings-only, use rankings-specific config if not specified
            if not args.rankings_config:
                rankings_config = config.get("rankings_config", str(config_path))
            else:
                rankings_config = args.rankings_config

            rankings_file = run_rankings_scraper(
                rankings_config,
                year=args.year,
                view=args.view,
                log_level=args.log_level,
                output_dir=args.output_dir,
            )
            print(f"Rankings saved to: {rankings_file}")

        elif args.mode == "universities-only":
            logger.info("Mode: Universities-only scraping")
            if not args.rankings_file:
                logger.error("--rankings-file is required for universities-only mode")
                sys.exit(1)

            university_config = config.get(
                "university_config", "config/university_detail.yml"
            )
            universities_file = run_university_scraper(
                args.rankings_file,
                university_config,
                log_level=args.log_level,
                batch_size=args.batch_size,
                limit=args.limit,
                output_dir=args.output_dir,
            )
            print(f"University details saved to: {universities_file}")

        elif args.mode == "full-pipeline":
            logger.info("Mode: Full pipeline execution")
            results = run_full_pipeline(
                config,
                year=args.year,
                view=args.view,
                log_level=args.log_level,
                batch_size=args.batch_size,
                limit=args.limit,
                rankings_only=args.rankings_only_flag,
                process_data=args.process_data,
                export_data=args.export_data,
                rankings_output_dir=args.output_dir,
                universities_output_dir=args.output_dir,
            )
            print(f"Pipeline completed: {results['status']}")

        elif args.mode == "process-only":
            logger.info("Mode: Process existing data only")
            # Implementation for processing existing files
            logger.error("Process-only mode not yet implemented")

        elif args.mode == "export-only":
            logger.info("Mode: Export processed data only")
            if not args.processed_file:
                logger.error("--processed-file is required for export-only mode")
                sys.exit(1)

            exported = export_data([args.processed_file], config)
            print(f"Data exported to: {exported}")

        logger.info("Orchestrator completed successfully")

    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Orchestrator failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
