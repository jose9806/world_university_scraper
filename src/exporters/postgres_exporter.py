"""Exportador PostgreSQL para datos de universidades."""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from ..storage.database_manager import PostgreSQLManager

logger = logging.getLogger(__name__)


class PostgreSQLExporter:
    """Exportador de datos a PostgreSQL."""

    def __init__(self, config: Dict[str, Any]):
        """Inicializar el exportador PostgreSQL.

        Args:
            config: Configuración del exportador
        """
        self.config = config
        self.db_config = config.get("postgres", {})
        self.enabled = config.get("enabled", True)
        self.batch_size = config.get("batch_size", 1000)
        self.if_exists = config.get("if_exists", "replace")  # replace, append, fail

        self.db_manager = None

    def initialize(self) -> bool:
        """Inicializar conexión a la base de datos.

        Returns:
            True si la inicialización es exitosa
        """
        if not self.enabled:
            logger.info("PostgreSQL exporter está deshabilitado")
            return True

        try:
            self.db_manager = PostgreSQLManager(self.db_config)

            if not self.db_manager.connect():
                logger.error("❌ No se pudo conectar a PostgreSQL")
                return False

            if not self.db_manager.create_tables():
                logger.error("❌ No se pudieron crear las tablas")
                return False

            logger.info("✅ PostgreSQL exporter inicializado exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error inicializando PostgreSQL exporter: {str(e)}")
            return False

    def export_rankings_data(
        self, data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Exportar datos de rankings a PostgreSQL.

        Args:
            data: Lista de datos de rankings
            metadata: Metadatos opcionales

        Returns:
            True si la exportación es exitosa
        """
        if not self.enabled or not data:
            return True

        if not self.db_manager:
            logger.error("❌ DB Manager no está inicializado")
            return False

        try:
            batch_id = metadata.get("batch_id", str(uuid.uuid4()))

            # Exportar datos en lotes si es necesario
            if len(data) > self.batch_size:
                return self._export_rankings_in_batches(data, batch_id)
            else:
                return self.db_manager.save_rankings_data(
                    data, batch_id, self.if_exists
                )

        except Exception as e:
            logger.error(f"❌ Error exportando rankings: {str(e)}")
            return False

    def export_university_details(
        self, data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Exportar detalles de universidades a PostgreSQL.

        Args:
            data: Lista de detalles de universidades
            metadata: Metadatos opcionales

        Returns:
            True si la exportación es exitosa
        """
        if not self.enabled or not data:
            return True

        if not self.db_manager:
            logger.error("❌ DB Manager no está inicializado")
            return False

        try:
            batch_id = metadata.get("batch_id", str(uuid.uuid4()))

            # Exportar datos en lotes si es necesario
            if len(data) > self.batch_size:
                return self._export_details_in_batches(data, batch_id)
            else:
                return self.db_manager.save_details_data(data, batch_id, self.if_exists)

        except Exception as e:
            logger.error(f"❌ Error exportando detalles: {str(e)}")
            return False

    def export_combined_data(
        self,
        rankings_data: List[Dict[str, Any]],
        details_data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Exportar datos combinados (rankings + detalles).

        Args:
            rankings_data: Datos de rankings
            details_data: Datos de detalles
            metadata: Metadatos opcionales

        Returns:
            True si ambas exportaciones son exitosas
        """
        if not self.enabled:
            return True

        try:
            batch_id = metadata.get("batch_id", str(uuid.uuid4()))

            # Actualizar metadata con el mismo batch_id
            combined_metadata = (metadata or {}).copy()
            combined_metadata["batch_id"] = batch_id

            rankings_success = self.export_rankings_data(
                rankings_data, combined_metadata
            )
            details_success = self.export_university_details(
                details_data, combined_metadata
            )

            if rankings_success and details_success:
                logger.info(
                    f"✅ Datos combinados exportados exitosamente (batch: {batch_id})"
                )
                return True
            else:
                logger.error(f"❌ Error en exportación combinada (batch: {batch_id})")
                return False

        except Exception as e:
            logger.error(f"❌ Error exportando datos combinados: {str(e)}")
            return False

    def log_export_session(
        self,
        session_type: str,
        start_time: datetime,
        end_time: datetime,
        records_processed: int,
        successful_exports: int,
        failed_exports: int,
        error_details: Optional[Dict] = None,
        batch_id: Optional[str] = None,
    ) -> bool:
        """Registrar información de la sesión de exportación.

        Args:
            session_type: Tipo de exportación
            start_time: Tiempo de inicio
            end_time: Tiempo de finalización
            records_processed: Registros procesados
            successful_exports: Exportaciones exitosas
            failed_exports: Exportaciones fallidas
            error_details: Detalles de errores
            batch_id: ID del lote

        Returns:
            True si el log se guarda exitosamente
        """
        if not self.enabled or not self.db_manager:
            return True

        try:
            return self.db_manager.log_scraping_session(
                batch_id or str(uuid.uuid4()),
                f"export_{session_type}",
                start_time,
                end_time,
                records_processed,
                successful_exports,
                failed_exports,
                error_details,
                self.config,
            )

        except Exception as e:
            logger.error(f"❌ Error registrando sesión de exportación: {str(e)}")
            return False

    def _export_rankings_in_batches(
        self, data: List[Dict[str, Any]], batch_id: str
    ) -> bool:
        """Exportar rankings en lotes más pequeños.

        Args:
            data: Datos a exportar
            batch_id: ID del lote principal

        Returns:
            True si todas las exportaciones son exitosas
        """
        total_batches = (len(data) + self.batch_size - 1) // self.batch_size
        successful_batches = 0

        for i in range(0, len(data), self.batch_size):
            batch_data = data[i : i + self.batch_size]
            sub_batch_id = f"{batch_id}_rankings_{i // self.batch_size + 1}"

            if self.db_manager.save_rankings_data(
                batch_data, sub_batch_id, "append" if i > 0 else self.if_exists
            ):
                successful_batches += 1
            else:
                logger.error(f"❌ Error en lote {i // self.batch_size + 1} de rankings")

        success_rate = successful_batches / total_batches
        logger.info(
            f"Rankings exportados en {successful_batches}/{total_batches} lotes ({success_rate:.1%})"
        )

        return success_rate >= 0.8  # 80% success rate threshold

    def _export_details_in_batches(
        self, data: List[Dict[str, Any]], batch_id: str
    ) -> bool:
        """Exportar detalles en lotes más pequeños.

        Args:
            data: Datos a exportar
            batch_id: ID del lote principal

        Returns:
            True si todas las exportaciones son exitosas
        """
        total_batches = (len(data) + self.batch_size - 1) // self.batch_size
        successful_batches = 0

        for i in range(0, len(data), self.batch_size):
            batch_data = data[i : i + self.batch_size]
            sub_batch_id = f"{batch_id}_details_{i // self.batch_size + 1}"

            if self.db_manager.save_details_data(
                batch_data, sub_batch_id, "append" if i > 0 else self.if_exists
            ):
                successful_batches += 1
            else:
                logger.error(f"❌ Error en lote {i // self.batch_size + 1} de detalles")

        success_rate = successful_batches / total_batches
        logger.info(
            f"Detalles exportados en {successful_batches}/{total_batches} lotes ({success_rate:.1%})"
        )

        return success_rate >= 0.8  # 80% success rate threshold

    def get_export_stats(self) -> Optional[Dict[str, Any]]:
        """Obtener estadísticas de exportación.

        Returns:
            Diccionario con estadísticas o None si hay error
        """
        if not self.enabled or not self.db_manager:
            return None

        return self.db_manager.get_scraping_stats()

    def test_connection(self) -> bool:
        """Probar la conexión a PostgreSQL.

        Returns:
            True si la conexión funciona
        """
        if not self.enabled:
            return True

        if not self.db_manager:
            return self.initialize()

        return self.db_manager.test_connection()

    def cleanup(self) -> None:
        """Limpiar recursos del exportador."""
        if self.db_manager:
            self.db_manager.close()
            self.db_manager = None


def create_postgres_exporter(config: Dict[str, Any]) -> PostgreSQLExporter:
    """Crear una instancia del exportador PostgreSQL.

    Args:
        config: Configuración del exportador

    Returns:
        Instancia de PostgreSQLExporter
    """
    return PostgreSQLExporter(config)
