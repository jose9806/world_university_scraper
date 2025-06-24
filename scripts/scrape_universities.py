#!/usr/bin/env python3
"""
Script para scraping de detalles universitarios.
Compatible con el orquestador principal (__main__.py).
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scrapers.university_detail_scraper import UniversityDetailScraper
from src.core.config import load_config


def setup_logging(log_level: str = "INFO"):
    """Configurar logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "university_scraper.log"

    # Configurar logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    return logging.getLogger(__name__)


def load_rankings_data(rankings_file: str) -> List[Dict[str, Any]]:
    """Cargar datos de rankings desde archivo JSON."""
    try:
        with open(rankings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # El archivo puede contener los datos directamente o en una clave específica
        if isinstance(data, list):
            rankings_data = data
        elif isinstance(data, dict):
            # Buscar la clave que contiene los rankings
            possible_keys = ["rankings", "data", "universities", "results"]
            rankings_data = None

            for key in possible_keys:
                if key in data and isinstance(data[key], list):
                    rankings_data = data[key]
                    break

            if rankings_data is None:
                # Si no encuentra una clave específica, tomar el primer valor que sea lista
                for value in data.values():
                    if isinstance(value, list):
                        rankings_data = value
                        break
                else:
                    raise ValueError(
                        "No se encontraron datos de rankings en formato lista"
                    )
        else:
            raise ValueError("Formato de archivo de rankings no válido")

        return rankings_data

    except Exception as e:
        raise ValueError(
            f"Error cargando archivo de rankings {rankings_file}: {str(e)}"
        )


def extract_university_urls(
    rankings_data: List[Dict[str, Any]], limit: int = None
) -> List[str]:
    """Extraer URLs de universidades desde datos de rankings."""
    urls = []

    for item in rankings_data:
        if isinstance(item, dict):
            # Buscar URL en diferentes campos posibles
            url_fields = ["university_url", "url", "link", "detail_url"]

            for field in url_fields:
                if field in item and item[field]:
                    url = item[field].strip()
                    if url and url.startswith("http"):
                        urls.append(url)
                        break

    # Aplicar límite si se especifica
    if limit:
        urls = urls[:limit]

    return urls


def save_results(data: List[Dict[str, Any]], output_dir: str) -> str:
    """Guardar resultados en archivo JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"universities_detail_{timestamp}.json"
    output_file = output_path / filename

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return str(output_file)

    except Exception as e:
        raise IOError(f"Error guardando resultados en {output_file}: {str(e)}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Scraper de detalles universitarios")

    # Argumentos requeridos (según el orquestador)
    parser.add_argument(
        "--rankings-file", required=True, help="Archivo JSON con datos de rankings"
    )
    parser.add_argument("--config", required=True, help="Archivo de configuración YAML")

    # Argumentos opcionales (según el orquestador)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Tamaño del lote para procesamiento"
    )
    parser.add_argument("--limit", type=int, help="Límite de universidades a procesar")
    parser.add_argument(
        "--output-dir", default="data/universities", help="Directorio de salida"
    )

    args = parser.parse_args()

    # Configurar logging
    logger = setup_logging(args.log_level)
    logger.info("=" * 60)
    logger.info("UNIVERSITY DETAIL SCRAPER INICIADO")
    logger.info("=" * 60)

    try:
        # 1. Cargar configuración
        logger.info(f"Cargando configuración desde: {args.config}")
        config = load_config(args.config)
        logger.info("✅ Configuración cargada exitosamente")

        # 2. Cargar datos de rankings
        logger.info(f"Cargando datos de rankings desde: {args.rankings_file}")
        rankings_data = load_rankings_data(args.rankings_file)
        logger.info(f"✅ Cargados {len(rankings_data)} registros de rankings")

        # 3. Extraer URLs de universidades
        logger.info("Extrayendo URLs de universidades...")
        university_urls = extract_university_urls(rankings_data, args.limit)

        if not university_urls:
            logger.error("❌ No se encontraron URLs de universidades válidas")
            return 1

        logger.info(f"✅ Encontradas {len(university_urls)} URLs de universidades")

        if args.limit:
            logger.info(f"🔢 Aplicando límite: {args.limit} universidades")

        # 4. Inicializar scraper
        logger.info("Inicializando scraper de universidades...")

        # Actualizar configuración con parámetros de línea de comandos
        scraper_config = config.get("scraper", {})

        # Aplicar batch_size si se especifica
        if args.batch_size:
            scraper_config["batch_size"] = args.batch_size

        scraper = UniversityDetailScraper(scraper_config)
        logger.info("✅ Scraper inicializado")

        # 5. Ejecutar scraping
        logger.info(f"🕷️ Iniciando scraping de {len(university_urls)} universidades...")
        start_time = time.time()

        try:
            university_details = scraper.scrape_university_details(university_urls)
            duration = time.time() - start_time

        except Exception as e:
            logger.error(f"❌ Error durante el scraping: {str(e)}")
            return 1

        # 6. Verificar resultados
        successful_count = len(
            [u for u in university_details if u and "error" not in u]
        )
        failed_count = len(university_details) - successful_count
        success_rate = (
            (successful_count / len(university_urls)) * 100 if university_urls else 0
        )

        logger.info("=" * 60)
        logger.info("RESULTADOS DEL SCRAPING")
        logger.info("=" * 60)
        logger.info(f"⏱️ Duración total: {duration:.2f} segundos")
        logger.info(
            f"⚡ Promedio por universidad: {duration/len(university_urls):.2f} segundos"
        )
        logger.info(f"✅ Exitosos: {successful_count}")
        logger.info(f"❌ Fallidos: {failed_count}")
        logger.info(f"📊 Tasa de éxito: {success_rate:.1f}%")

        # 7. Guardar resultados
        if university_details:
            logger.info(f"💾 Guardando resultados en: {args.output_dir}")

            try:
                output_file = save_results(university_details, args.output_dir)
                logger.info(f"✅ Resultados guardados en: {output_file}")

                # Imprimir el archivo de salida para el orquestador
                # IMPORTANTE: Esta línea es leída por el orquestador para encontrar el archivo
                print(f"UNIVERSITIES_OUTPUT_FILE:{output_file}")

            except Exception as e:
                logger.error(f"❌ Error guardando resultados: {str(e)}")
                return 1
        else:
            logger.warning("⚠️ No hay resultados para guardar")
            return 1

        # 8. Resumen de datos extraídos
        if successful_count > 0:
            logger.info("📊 RESUMEN DE DATOS EXTRAÍDOS:")

            total_rankings = sum(
                len(u.get("ranking_data", {}))
                for u in university_details
                if "ranking_data" in u
            )
            total_stats = sum(
                len(u.get("key_stats", {}))
                for u in university_details
                if "key_stats" in u
            )
            total_subjects = sum(
                len(u.get("subjects", []))
                for u in university_details
                if "subjects" in u
            )

            logger.info(f"   🏆 Total rankings extraídos: {total_rankings}")
            logger.info(f"   📈 Total estadísticas extraídas: {total_stats}")
            logger.info(f"   🎓 Total materias extraídas: {total_subjects}")

            # Mostrar ejemplos de universidades exitosas
            successful_unis = [u for u in university_details if u and "error" not in u][
                :3
            ]
            logger.info("📝 EJEMPLOS DE UNIVERSIDADES PROCESADAS:")

            for i, uni in enumerate(successful_unis, 1):
                name = uni.get("name", "Unknown")
                rankings_count = len(uni.get("ranking_data", {}))
                stats_count = len(uni.get("key_stats", {}))
                logger.info(
                    f"   {i}. {name} - Rankings: {rankings_count}, Stats: {stats_count}"
                )

        logger.info("=" * 60)
        logger.info("UNIVERSITY DETAIL SCRAPER COMPLETADO EXITOSAMENTE")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("\n⏹️ Scraping interrumpido por el usuario")
        return 1

    except Exception as e:
        logger.error(f"❌ Error inesperado: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
