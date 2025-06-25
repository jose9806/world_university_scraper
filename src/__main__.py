"""Main orchestrator with PostgreSQL integration."""

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
from .storage.database_manager import PostgreSQLManager  # 🔥 NUEVO


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


def run_rankings_scraper(
    config_file: str, db_manager: PostgreSQLManager = None, **kwargs
):
    """Run the rankings scraper and optionally save to PostgreSQL."""
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
    if kwargs.get("limit"):
        cmd.extend(["--limit", str(kwargs["limit"])])

    # Run subprocess
    try:
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Rankings scraper completed successfully")

        # 🔥 BUSCAR LA RUTA DEL ARCHIVO EN LA SALIDA
        output_lines = result.stdout.split("\n")
        json_file = None

        # Buscar líneas que contengan la ruta del archivo
        for line in output_lines:
            if "JSON_FILE_PATH:" in line:
                json_file = line.split("JSON_FILE_PATH:")[1].strip()
                break
            elif "FINAL_OUTPUT:" in line:
                json_file = line.split("FINAL_OUTPUT:")[1].strip()
                break
            elif "rankings_" in line and ".json" in line and "saved to:" in line:
                parts = line.split("saved to:")
                if len(parts) > 1:
                    json_file = parts[1].strip()
                    break

        # Si no encuentra la ruta, buscar en el directorio de salida
        if not json_file or not Path(json_file).exists():
            logger.warning("No se pudo encontrar la ruta del archivo en stdout, buscando en directorio...")
            
            output_dir = kwargs.get("output_dir", "data/raw")
            output_path = Path(output_dir)
            
            if output_path.exists():
                json_files = list(output_path.glob("rankings_*.json"))
                if json_files:
                    json_file = str(max(json_files, key=lambda x: x.stat().st_mtime))
                    logger.info(f"📁 Archivo encontrado en directorio: {json_file}")

        # 🔥 INSERTAR EN POSTGRESQL SI SE ENCONTRÓ EL ARCHIVO
        if json_file and db_manager and Path(json_file).exists():
            logger.info("🚀 Insertando datos de rankings en PostgreSQL...")
            
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                
                # 🔥 EXTRAER DATOS CORRECTAMENTE SEGÚN EL FORMATO
                if isinstance(json_data, dict):
                    # Si es un diccionario con wrapper
                    if "data" in json_data:
                        rankings_data = json_data["data"]
                        logger.info(f"📦 Datos extraídos del wrapper: {len(rankings_data)} universidades")
                    elif "success" in json_data and json_data.get("success"):
                        # Buscar datos en diferentes claves posibles
                        rankings_data = json_data.get("data", json_data.get("rankings", []))
                        logger.info(f"📦 Datos extraídos de objeto success: {len(rankings_data)} universidades")
                    else:
                        # Asumir que el diccionario completo son los datos
                        rankings_data = [json_data]
                        logger.info("📦 Tratando diccionario como registro único")
                elif isinstance(json_data, list):
                    # Si ya es una lista directa
                    rankings_data = json_data
                    logger.info(f"📦 Lista directa de datos: {len(rankings_data)} universidades")
                else:
                    logger.error(f"❌ Formato de JSON no reconocido: {type(json_data)}")
                    rankings_data = []

                # Verificar que tenemos datos válidos
                if not rankings_data:
                    logger.warning("⚠️ No se encontraron datos de rankings para insertar")
                    return json_file

                # 🔥 LOGGING DETALLADO PARA DEBUG
                logger.info(f"📊 Datos a insertar:")
                logger.info(f"   - Total universidades: {len(rankings_data)}")
                if rankings_data:
                    first_item = rankings_data[0]
                    logger.info(f"   - Estructura primer item: {list(first_item.keys()) if isinstance(first_item, dict) else type(first_item)}")
                    if isinstance(first_item, dict):
                        logger.info(f"   - Ejemplo: {first_item.get('name', 'N/A')} (rank: {first_item.get('rank', 'N/A')})")

                batch_id = f"rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Insertar en PostgreSQL
                if db_manager.save_rankings_data(
                    rankings_data, batch_id, if_exists="append"
                ):
                    logger.info(
                        f"✅ {len(rankings_data)} rankings insertados en PostgreSQL (batch: {batch_id})"
                    )
                else:
                    logger.error("❌ Error insertando rankings en PostgreSQL")
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Error decodificando JSON: {str(e)}")
            except Exception as e:
                logger.error(f"❌ Error procesando archivo JSON para PostgreSQL: {str(e)}")
                logger.exception("Detalles del error:")
        elif json_file and not Path(json_file).exists():
            logger.error(f"❌ Archivo JSON no existe: {json_file}")
        elif not json_file:
            logger.warning("⚠️ No se pudo determinar la ruta del archivo JSON")
        elif not db_manager:
            logger.info("ℹ️ PostgreSQL manager no disponible - solo guardando archivos")

        return json_file

    except subprocess.CalledProcessError as e:
        logger.error(f"Rankings scraper failed with exit code {e.returncode}")
        logger.error(f"Command: {' '.join(cmd)}")
        if e.stdout:
            logger.error(f"Script stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Script stderr: {e.stderr}")
        raise


def run_university_scraper(
    rankings_file: str, config_file: str, db_manager: PostgreSQLManager = None, **kwargs
) -> str:
    """Run the university detail scraper and optionally save to PostgreSQL."""
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

        # 🔥 NUEVA FUNCIONALIDAD: Insertar automáticamente en PostgreSQL
        if json_file and db_manager and Path(json_file).exists():
            logger.info("🚀 Insertando detalles de universidades en PostgreSQL...")

            with open(json_file, "r", encoding="utf-8") as f:
                universities_data = json.load(f)

            batch_id = f"universities_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            if db_manager.save_details_data(
                universities_data, batch_id, if_exists="append"
            ):
                logger.info(
                    f"✅ {len(universities_data)} detalles de universidades insertados en PostgreSQL"
                )
            else:
                logger.error("❌ Error insertando detalles en PostgreSQL")

        return json_file

    except subprocess.CalledProcessError as e:
        logger.error(f"University detail scraper failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        raise


def run_full_pipeline(config: dict, **kwargs):
    """Run the complete scraping and processing pipeline with PostgreSQL integration."""
    logger = logging.getLogger(__name__)
    logger.info("Starting full pipeline execution with PostgreSQL integration...")

    results = {
        "start_time": datetime.now().isoformat(),
        "rankings_file": None,
        "universities_file": None,
        "processed_files": [],
        "exported_to": [],
        "postgres_inserts": [],
        "errors": [],
    }

    # 🔥 NUEVA FUNCIONALIDAD: Inicializar PostgreSQL Manager
    db_manager = None
    postgres_enabled = config.get("postgres", {}).get("enabled", True)

    if postgres_enabled:
        logger.info("🔗 Conectando a PostgreSQL...")
        db_manager = PostgreSQLManager()

        if db_manager.test_connection():
            logger.info("✅ Conexión a PostgreSQL establecida")

            # Crear tablas si no existen
            if db_manager.create_tables():
                logger.info("✅ Tablas de PostgreSQL verificadas")
            else:
                logger.warning("⚠️ Error creando tablas en PostgreSQL")
        else:
            logger.warning(
                "⚠️ No se pudo conectar a PostgreSQL. Continuando sin inserción automática."
            )
            db_manager = None

    try:
        start_time = datetime.now()

        # Step 1: Rankings scraping
        logger.info("Step 1/4: Scraping university rankings...")
        rankings_config = config.get("rankings_config", "config/default_selenium.yml")

        rankings_file = run_rankings_scraper(
            rankings_config,
            db_manager=db_manager,  # 🔥 Pasar db_manager
            year=kwargs.get("year"),
            view=kwargs.get("view"),
            log_level=kwargs.get("log_level"),
            output_dir=kwargs.get("rankings_output_dir"),
            limit=kwargs.get("limit"),
        )

        if not rankings_file or not Path(rankings_file).exists():
            raise Exception("Rankings file not found after scraping")

        results["rankings_file"] = rankings_file
        logger.info(f"Rankings saved to: {rankings_file}")

        if db_manager:
            results["postgres_inserts"].append("rankings")

        # Step 2: University details scraping
        if not kwargs.get("rankings_only", False):
            logger.info("Step 2/4: Scraping university details...")
            university_config = config.get(
                "university_config", "config/university_detail.yml"
            )

            universities_file = run_university_scraper(
                rankings_file,
                university_config,
                db_manager=db_manager,  # 🔥 Pasar db_manager
                log_level=kwargs.get("log_level"),
                batch_size=kwargs.get("batch_size"),
                limit=kwargs.get("limit"),
                output_dir=kwargs.get("universities_output_dir"),
            )

            if universities_file:
                results["universities_file"] = universities_file
                logger.info(f"University details saved to: {universities_file}")

                if db_manager:
                    results["postgres_inserts"].append("university_details")

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

        # 🔥 NUEVA FUNCIONALIDAD: Registrar sesión de scraping en PostgreSQL
        if db_manager:
            end_time = datetime.now()
            total_urls = (
                kwargs.get("limit", 0) if kwargs.get("limit") else 2000
            )  # Estimación
            successful_scrapes = len(results.get("postgres_inserts", []))
            failed_scrapes = len(results.get("errors", []))

            batch_id = f"pipeline_{start_time.strftime('%Y%m%d_%H%M%S')}"

            db_manager.log_scraping_session(
                batch_id=batch_id,
                scrape_type="full_pipeline",
                start_time=start_time,
                end_time=end_time,
                total_urls=total_urls,
                successful_scrapes=successful_scrapes,
                failed_scrapes=failed_scrapes,
                error_details={"errors": results["errors"]},
                config_used={"mode": "full_pipeline", "limit": kwargs.get("limit")},
            )

            logger.info(
                f"📊 Sesión de scraping registrada en PostgreSQL (batch: {batch_id})"
            )

        results["end_time"] = datetime.now().isoformat()
        results["status"] = "completed"

        # Save pipeline results summary
        save_pipeline_summary(results, config)

        logger.info("Full pipeline completed successfully!")

        # 🔥 NUEVA FUNCIONALIDAD: Mostrar estadísticas de PostgreSQL
        if db_manager:
            stats = db_manager.get_scraping_stats()
            if stats:
                logger.info("📊 Estadísticas de PostgreSQL:")
                logger.info(f"   Total rankings: {stats['total_rankings']}")
                logger.info(f"   Total detalles: {stats['total_details']}")

        return results

    except Exception as e:
        results["errors"].append(str(e))
        results["status"] = "failed"
        results["end_time"] = datetime.now().isoformat()
        logger.error(f"Pipeline failed: {str(e)}")
        raise

    finally:
        # Cerrar conexión a PostgreSQL
        if db_manager:
            db_manager.close()


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
        description="World University Scraper - Main Orchestrator with PostgreSQL Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  rankings-only    : Scrape only university rankings (🔥 AUTO-INSERT to PostgreSQL)
  universities-only: Scrape only university details (🔥 AUTO-INSERT to PostgreSQL)
  full-pipeline    : Complete scraping, processing, and export pipeline (🔥 AUTO-INSERT to PostgreSQL)
  process-only     : Only process existing data files
  export-only      : Only export processed data

EXAMPLES:
  # Scrape rankings and auto-insert to PostgreSQL
  python -m src --mode rankings-only --config config/default_selenium.yml --limit 50
  
  # Full pipeline with PostgreSQL auto-insertion
  python -m src --mode full-pipeline --export-data --config config/full_pipeline.yml --limit 100
  
  # University details only using existing rankings (auto-insert)
  python -m src --mode universities-only --rankings-file data/raw/rankings.json --limit 20
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
        help="Execution mode (all modes auto-insert to PostgreSQL)",
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

    # PostgreSQL options
    parser.add_argument(
        "--no-postgres",
        action="store_true",
        help="Disable automatic PostgreSQL insertion",
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

        # 🔥 NUEVA FUNCIONALIDAD: Configuración de PostgreSQL
        if args.no_postgres:
            config["postgres"] = {"enabled": False}
        else:
            config.setdefault("postgres", {"enabled": True})

        # Execute based on mode
        if args.mode == "rankings-only":
            logger.info("Mode: Rankings-only scraping with PostgreSQL auto-insertion")

            # Create PostgreSQL manager for standalone execution
            db_manager = None
            if not args.no_postgres:
                db_manager = PostgreSQLManager()
                if db_manager.test_connection():
                    db_manager.create_tables()
                    logger.info("✅ PostgreSQL ready for auto-insertion")
                else:
                    logger.warning("⚠️ PostgreSQL not available, saving to files only")
                    db_manager = None

            rankings_config = config.get("rankings_config", str(config_path))
            rankings_file = run_rankings_scraper(
                rankings_config,
                db_manager=db_manager,
                year=args.year,
                view=args.view,
                log_level=args.log_level,
                output_dir=args.output_dir,
                limit=args.limit,
            )

            if db_manager:
                db_manager.close()

            print(f"Rankings saved to: {rankings_file}")
            if not args.no_postgres:
                print("✅ Data automatically inserted to PostgreSQL")

        elif args.mode == "universities-only":
            logger.info(
                "Mode: Universities-only scraping with PostgreSQL auto-insertion"
            )
            if not args.rankings_file:
                logger.error("--rankings-file is required for universities-only mode")
                sys.exit(1)

            # Create PostgreSQL manager for standalone execution
            db_manager = None
            if not args.no_postgres:
                db_manager = PostgreSQLManager()
                if db_manager.test_connection():
                    db_manager.create_tables()
                    logger.info("✅ PostgreSQL ready for auto-insertion")
                else:
                    logger.warning("⚠️ PostgreSQL not available, saving to files only")
                    db_manager = None

            university_config = config.get(
                "university_config", "config/university_detail.yml"
            )
            universities_file = run_university_scraper(
                args.rankings_file,
                university_config,
                db_manager=db_manager,
                log_level=args.log_level,
                batch_size=args.batch_size,
                limit=args.limit,
                output_dir=args.output_dir,
            )

            if db_manager:
                db_manager.close()

            print(f"University details saved to: {universities_file}")
            if not args.no_postgres:
                print("✅ Data automatically inserted to PostgreSQL")

        elif args.mode == "full-pipeline":
            logger.info("Mode: Full pipeline execution with PostgreSQL auto-insertion")
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
            if results.get("postgres_inserts"):
                print(
                    f"✅ Auto-inserted to PostgreSQL: {', '.join(results['postgres_inserts'])}"
                )

        elif args.mode == "process-only":
            logger.info("Mode: Process existing data only")
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
