"""Script para verificar la conexión y datos en PostgreSQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.storage.database_manager import PostgreSQLManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_database():
    """Verificar conexión y contenido de la base de datos."""

    # Crear instancia del manager
    db_manager = PostgreSQLManager()

    # 1. Probar conexión
    print("=== VERIFICACIÓN DE CONEXIÓN ===")
    if db_manager.test_connection():
        print("✅ Conexión exitosa")
    else:
        print("❌ Error de conexión")
        return False

    # 2. Crear tablas si no existen
    print("\n=== CREACIÓN DE TABLAS ===")
    if db_manager.create_tables():
        print("✅ Tablas creadas/verificadas")
    else:
        print("❌ Error creando tablas")
        return False

    # 3. Verificar datos existentes
    print("\n=== VERIFICACIÓN DE DATOS ===")
    try:
        import pandas as pd
        from sqlalchemy import text

        with db_manager.engine.connect() as conn:
            # Contar registros en cada tabla
            rankings_count = conn.execute(
                text("SELECT COUNT(*) FROM university_rankings")
            ).scalar()
            details_count = conn.execute(
                text("SELECT COUNT(*) FROM university_details")
            ).scalar()
            logs_count = conn.execute(
                text("SELECT COUNT(*) FROM scraping_logs")
            ).scalar()

            print(f"📊 University Rankings: {rankings_count} registros")
            print(f"📊 University Details: {details_count} registros")
            print(f"📊 Scraping Logs: {logs_count} registros")

            # Mostrar algunos registros recientes si existen
            if rankings_count > 0:
                print("\n=== ÚLTIMOS RANKINGS ===")
                recent_rankings = conn.execute(
                    text(
                        """
                    SELECT university_name, rank_position, country, created_at 
                    FROM university_rankings 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """
                    )
                ).fetchall()

                for row in recent_rankings:
                    print(
                        f"  {row.rank_position}. {row.university_name} ({row.country}) - {row.created_at}"
                    )

        return True

    except Exception as e:
        print(f"❌ Error verificando datos: {str(e)}")
        return False

    finally:
        db_manager.close()


if __name__ == "__main__":
    verify_database()
