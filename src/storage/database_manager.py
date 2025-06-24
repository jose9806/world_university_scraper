"""Gestor de base de datos PostgreSQL para el scraper de universidades."""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """Gestor de base de datos PostgreSQL para datos de universidades."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicializar el gestor de base de datos.

        Args:
            config: Configuración de la base de datos (opcional)
        """
        if config is None:
            config = self._load_config_from_env()

        self.config = config
        self.engine = None
        self._connection_string = self._build_connection_string()

    def _load_config_from_env(self) -> Dict[str, Any]:
        """Cargar configuración desde variables de entorno."""
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "scrap_db"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        }

    def _build_connection_string(self) -> str:
        """Construir string de conexión PostgreSQL."""
        return (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

    def connect(self) -> bool:
        """Establecer conexión con la base de datos.

        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            self.engine = create_engine(
                self._connection_string,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=False,  # Cambiar a True para debug SQL
            )

            # Probar la conexión
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info("✅ Conexión a PostgreSQL establecida exitosamente")
            return True

        except SQLAlchemyError as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado conectando a DB: {str(e)}")
            return False

    def create_tables(self) -> bool:
        """Crear las tablas necesarias en la base de datos.

        Returns:
            True si las tablas se crean exitosamente
        """
        if not self.engine:
            logger.error("❌ No hay conexión a la base de datos")
            return False

        try:
            with self.engine.connect() as conn:
                # Tabla de rankings universitarios
                rankings_table_sql = """
                CREATE TABLE IF NOT EXISTS university_rankings (
                    id SERIAL PRIMARY KEY,
                    rank_position INTEGER,
                    university_name VARCHAR(500) NOT NULL,
                    country VARCHAR(100),
                    university_url TEXT,
                    overall_score DECIMAL(5,2),
                    teaching_score DECIMAL(5,2),
                    research_score DECIMAL(5,2),
                    citations_score DECIMAL(5,2),
                    industry_income_score DECIMAL(5,2),
                    international_outlook_score DECIMAL(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scrape_batch_id VARCHAR(100),
                    UNIQUE(university_name, scrape_batch_id)
                );
                """

                # Tabla de detalles universitarios
                details_table_sql = """
                CREATE TABLE IF NOT EXISTS university_details (
                    id SERIAL PRIMARY KEY,
                    university_name VARCHAR(500) NOT NULL,
                    university_url TEXT UNIQUE,
                    student_total VARCHAR(50),
                    international_percentage VARCHAR(50),
                    gender_ratio VARCHAR(100),
                    student_staff_ratio VARCHAR(50),
                    ranking_data JSONB,
                    subjects_data JSONB,
                    additional_info JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scrape_batch_id VARCHAR(100)
                );
                """

                # Tabla de logs de scraping
                logs_table_sql = """
                CREATE TABLE IF NOT EXISTS scraping_logs (
                    id SERIAL PRIMARY KEY,
                    batch_id VARCHAR(100) NOT NULL,
                    scrape_type VARCHAR(50) NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    total_urls INTEGER,
                    successful_scrapes INTEGER,
                    failed_scrapes INTEGER,
                    success_rate DECIMAL(5,2),
                    error_details JSONB,
                    config_used JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """

                # Ejecutar creación de tablas
                conn.execute(text(rankings_table_sql))
                conn.execute(text(details_table_sql))
                conn.execute(text(logs_table_sql))
                conn.commit()

                logger.info("✅ Tablas creadas exitosamente")
                return True

        except SQLAlchemyError as e:
            logger.error(f"❌ Error creando tablas: {str(e)}")
            return False

    def save_rankings_data(
        self,
        rankings_data: List[Dict[str, Any]],
        batch_id: str,
        if_exists: str = "replace",
    ) -> bool:
        """Guardar datos de rankings en la base de datos.

        Args:
            rankings_data: Lista de diccionarios con datos de rankings
            batch_id: Identificador del lote de scraping
            if_exists: 'replace', 'append', o 'fail'

        Returns:
            True si los datos se guardan exitosamente
        """
        if not rankings_data:
            logger.warning("⚠️ No hay datos de rankings para guardar")
            return False

        try:
            # Convertir a DataFrame
            df = pd.DataFrame(rankings_data)

            # Limpiar y mapear columnas
            column_mapping = {
                "rank": "rank_position",
                "name": "university_name",
                "country": "country",
                "university_url": "university_url",
                "overall_score": "overall_score",
                "teaching_score": "teaching_score",
                "research_score": "research_score",
                "citations_score": "citations_score",
                "industry_income_score": "industry_income_score",
                "international_outlook_score": "international_outlook_score",
            }

            # Renombrar columnas que existan
            existing_columns = {
                k: v for k, v in column_mapping.items() if k in df.columns
            }
            df = df.rename(columns=existing_columns)

            # Agregar metadatos
            df["scrape_batch_id"] = batch_id
            df["updated_at"] = datetime.now()

            # Guardar en la base de datos
            rows_affected = df.to_sql(
                "university_rankings",
                self.engine,
                if_exists=if_exists,
                index=False,
                method="multi",
            )

            logger.info(
                f"✅ {len(df)} registros de rankings guardados (batch: {batch_id})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando rankings: {str(e)}")
            return False

    def save_details_data(
        self,
        details_data: List[Dict[str, Any]],
        batch_id: str,
        if_exists: str = "replace",
    ) -> bool:
        """Guardar datos detallados de universidades.

        Args:
            details_data: Lista de diccionarios con detalles de universidades
            batch_id: Identificador del lote de scraping
            if_exists: 'replace', 'append', o 'fail'

        Returns:
            True si los datos se guardan exitosamente
        """
        if not details_data:
            logger.warning("⚠️ No hay datos de detalles para guardar")
            return False

        try:
            processed_data = []

            for detail in details_data:
                if "error" in detail:
                    continue  # Skip errored entries

                processed_record = {
                    "university_name": detail.get("name", "Unknown"),
                    "university_url": detail.get("url", ""),
                    "student_total": detail.get("key_stats", {}).get("student_total"),
                    "international_percentage": detail.get("key_stats", {}).get(
                        "international_percentage"
                    ),
                    "gender_ratio": detail.get("key_stats", {}).get("gender_ratio"),
                    "student_staff_ratio": detail.get("key_stats", {}).get(
                        "student_staff_ratio"
                    ),
                    "ranking_data": json.dumps(detail.get("ranking_data", {})),
                    "subjects_data": json.dumps(detail.get("subjects", [])),
                    "additional_info": json.dumps(
                        {
                            k: v
                            for k, v in detail.items()
                            if k
                            not in [
                                "name",
                                "url",
                                "key_stats",
                                "ranking_data",
                                "subjects",
                            ]
                        }
                    ),
                    "scrape_batch_id": batch_id,
                    "updated_at": datetime.now(),
                }
                processed_data.append(processed_record)

            if not processed_data:
                logger.warning("⚠️ No hay datos válidos de detalles para guardar")
                return False

            df = pd.DataFrame(processed_data)

            rows_affected = df.to_sql(
                "university_details",
                self.engine,
                if_exists=if_exists,
                index=False,
                method="multi",
            )

            logger.info(
                f"✅ {len(df)} registros de detalles guardados (batch: {batch_id})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando detalles: {str(e)}")
            return False

    def log_scraping_session(
        self,
        batch_id: str,
        scrape_type: str,
        start_time: datetime,
        end_time: datetime,
        total_urls: int,
        successful_scrapes: int,
        failed_scrapes: int,
        error_details: Optional[Dict] = None,
        config_used: Optional[Dict] = None,
    ) -> bool:
        """Registrar información de la sesión de scraping.

        Args:
            batch_id: ID del lote
            scrape_type: Tipo de scraping ('rankings', 'details', 'full_pipeline')
            start_time: Tiempo de inicio
            end_time: Tiempo de finalización
            total_urls: Total de URLs procesadas
            successful_scrapes: Scraping exitosos
            failed_scrapes: Scraping fallidos
            error_details: Detalles de errores (opcional)
            config_used: Configuración utilizada (opcional)

        Returns:
            True si el log se guarda exitosamente
        """
        try:
            success_rate = (
                (successful_scrapes / total_urls * 100) if total_urls > 0 else 0
            )

            log_data = {
                "batch_id": batch_id,
                "scrape_type": scrape_type,
                "start_time": start_time,
                "end_time": end_time,
                "total_urls": total_urls,
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": failed_scrapes,
                "success_rate": round(success_rate, 2),
                "error_details": json.dumps(error_details or {}),
                "config_used": json.dumps(config_used or {}),
            }

            df = pd.DataFrame([log_data])
            df.to_sql("scraping_logs", self.engine, if_exists="append", index=False)

            logger.info(
                f"✅ Log de scraping guardado (batch: {batch_id}, tipo: {scrape_type})"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando log: {str(e)}")
            return False

    def get_latest_rankings(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtener los rankings más recientes.

        Args:
            limit: Número máximo de registros a retornar

        Returns:
            DataFrame con los rankings o None si hay error
        """
        try:
            query = """
            SELECT * FROM university_rankings 
            ORDER BY created_at DESC, rank_position ASC
            LIMIT %s
            """

            df = pd.read_sql(query, self.engine, params=[limit])
            logger.info(f"✅ Obtenidos {len(df)} rankings más recientes")
            return df

        except Exception as e:
            logger.error(f"❌ Error obteniendo rankings: {str(e)}")
            return None

    def get_scraping_stats(self) -> Optional[Dict[str, Any]]:
        """Obtener estadísticas de scraping.

        Returns:
            Diccionario con estadísticas o None si hay error
        """
        try:
            with self.engine.connect() as conn:
                # Total de universidades en rankings
                total_rankings = conn.execute(
                    text("SELECT COUNT(*) FROM university_rankings")
                ).scalar()

                # Total de detalles de universidades
                total_details = conn.execute(
                    text("SELECT COUNT(*) FROM university_details")
                ).scalar()

                # Últimas sesiones de scraping
                recent_sessions = conn.execute(
                    text(
                        """
                    SELECT scrape_type, COUNT(*) as sessions, 
                           AVG(success_rate) as avg_success_rate
                    FROM scraping_logs 
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY scrape_type
                """
                    )
                ).fetchall()

                stats = {
                    "total_rankings": total_rankings,
                    "total_details": total_details,
                    "recent_sessions": [dict(row._mapping) for row in recent_sessions],
                    "last_updated": datetime.now().isoformat(),
                }

                logger.info("✅ Estadísticas de scraping obtenidas")
                return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """Probar la conexión a la base de datos.

        Returns:
            True si la conexión funciona
        """
        try:
            if not self.engine:
                if not self.connect():
                    return False

            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).scalar()
                logger.info(f"✅ Conexión exitosa. PostgreSQL version: {result}")
                return True

        except Exception as e:
            logger.error(f"❌ Test de conexión falló: {str(e)}")
            return False

    def close(self) -> None:
        """Cerrar la conexión a la base de datos."""
        if self.engine:
            self.engine.dispose()
            logger.info("✅ Conexión a PostgreSQL cerrada")


# Función helper para crear instancia del manager
def create_db_manager(config: Optional[Dict[str, Any]] = None) -> PostgreSQLManager:
    """Crear una instancia del gestor de base de datos.

    Args:
        config: Configuración opcional

    Returns:
        Instancia de PostgreSQLManager
    """
    return PostgreSQLManager(config)
