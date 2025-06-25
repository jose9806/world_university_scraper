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

    # 🔥 ARREGLAR: Verificar que data es una lista
    if isinstance(data, dict):
        # Si data es un diccionario (como el resultado del pipeline), extraer la lista real
        if "data" in data:
            actual_data = data["data"]
        elif isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            # Si es un diccionario de universidades, convertir a lista
            actual_data = list(data.values())
        else:
            # Si es un solo elemento, convertir a lista
            actual_data = [data]
    else:
        actual_data = data

    # 🔥 VERIFICAR QUE CADA ELEMENTO ES UN DICCIONARIO
    universities_data = []
    for item in actual_data:
        if isinstance(item, dict):
            universities_data.append(item)
        elif isinstance(item, str):
            # Si es un string, ignorar (posiblemente un mensaje de error)
            print(f"Ignorando elemento string en datos: {item[:100]}...")
            continue
        else:
            print(f"Ignorando elemento de tipo {type(item)}: {str(item)[:100]}...")
            continue

    if not universities_data:
        print("⚠️ No hay datos válidos de universidades para generar resumen")
        return

    try:
        summary = {
            "total_universities": len(universities_data),
            "countries": len(
                set(
                    uni.get("country", "")
                    for uni in universities_data
                    if uni.get("country")
                )
            ),
            "with_urls": len(
                [uni for uni in universities_data if uni.get("university_url")]
            ),
            "top_10": (
                universities_data[:10]
                if len(universities_data) >= 10
                else universities_data
            ),
            "score_ranges": {
                "overall_score": {
                    "min": min(
                        (uni.get("overall_score", 0) or 0 for uni in universities_data),
                        default=0,
                    ),
                    "max": max(
                        (uni.get("overall_score", 0) or 0 for uni in universities_data),
                        default=0,
                    ),
                }
            },
            "scrape_timestamp": datetime.now(),
        }

        summary_file = Path(output_dir) / "rankings_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        logging.info(f"Rankings summary saved to {summary_file}")

        # Print summary to console
        print("\n" + "=" * 50)
        print("RANKINGS SCRAPING SUMMARY")
        print("=" * 50)
        print(f"Total universities: {summary['total_universities']}")
        print(f"Countries represented: {summary['countries']}")
        print(f"Universities with detail URLs: {summary['with_urls']}")
        if summary["total_universities"] > 0:
            success_rate = summary["with_urls"] / summary["total_universities"] * 100
            print(f"Success rate: {success_rate:.1f}%")
        print("=" * 50)

    except Exception as e:
        print(f"⚠️ Error generando resumen (no crítico): {e}")
        logging.warning(f"Error en save_rankings_summary: {e}")


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
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of universities to scrape (for testing)",
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

        # 🔥 CONFIGURAR LÍMITE EN EL PIPELINE
        if args.limit:
            config.setdefault("scraper", {})["limit"] = args.limit
            logger.info(f"🎯 Limitando scraping a {args.limit} universidades")

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

        # 🔥 GUARDAR JSON Y DEVOLVER RUTA DEL ARCHIVO
        output_dir = config.get("general", {}).get("output_dir", "data/raw")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Crear nombre de archivo con timestamp
        rankings_config = config.get("scraper", {}).get("rankings", {})
        year = rankings_config.get("year", "2025")
        view = rankings_config.get("view", "reputation")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_filename = f"rankings_{year}_{view}_{timestamp}.json"
        json_file_path = output_path / json_filename

        # Guardar archivo JSON
        if not args.no_json:
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(universities, f, indent=2, ensure_ascii=False)

            logger.info(f"Rankings JSON saved to: {json_file_path}")

            # 🔥 IMPRIMIR LA RUTA PARA QUE EL ORQUESTADOR LA CAPTURE
            print(f"JSON_FILE_PATH: {json_file_path}")

            # Save summary
            if isinstance(universities, dict) and "data" in universities:
                save_rankings_summary(universities["data"], output_dir)
            else:
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

        # 🔥 ASEGURAR QUE EL ORQUESTADOR RECIBA LA RUTA
        if not args.no_json and json_file_path.exists():
            # Print final path for orchestrator to capture
            print(f"FINAL_OUTPUT: {json_file_path}")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
