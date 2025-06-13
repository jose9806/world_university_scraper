"""PostgreSQL exporter for rankings data."""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import (
    create_engine,
    Table,
    MetaData,
    Column,
    Integer,
    String,
    Float,
    inspect,
)
from sqlalchemy.exc import SQLAlchemyError

from src.exporters.base_exporter import BaseExporter
from src.utils.exceptions import ExporterException

logger = logging.getLogger(__name__)


class PostgresExporter(BaseExporter):
    """Exports data to PostgreSQL database."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PostgreSQL exporter with configuration.

        Args:
            config: Exporter configuration dictionary containing database settings
        """
        super().__init__(config)
        self.db_config = config.get("database", {})
        self.engine = self._create_engine()

    def _create_engine(self):
        """Create SQLAlchemy engine for database connection.

        Returns:
            SQLAlchemy engine

        Raises:
            ExporterException: If connection parameters are invalid
        """
        try:
            connection_string = self._get_connection_string()
            logger.debug(
                f"Creating database engine with connection string: {self._get_sanitized_connection_string()}"
            )
            return create_engine(connection_string)
        except Exception as e:
            raise ExporterException(f"Failed to create database engine: {e}")

    def _get_connection_string(self) -> str:
        """Get database connection string from configuration.

        Returns:
            Database connection string

        Raises:
            ExporterException: If required connection parameters are missing
        """
        # Get connection parameters from config
        host = self.db_config.get("host", "localhost")
        port = self.db_config.get("port", 5432)
        database = self.db_config.get("database")
        user = self.db_config.get("user")
        password = self.db_config.get("password")

        # Verify required parameters
        if not all([database, user, password]):
            raise ExporterException(
                "Missing required database connection parameters (database, user, password)"
            )

        # Build connection string
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    def _get_sanitized_connection_string(self) -> str:
        """Get sanitized connection string for logging (without password).

        Returns:
            Sanitized connection string
        """
        host = self.db_config.get("host", "localhost")
        port = self.db_config.get("port", 5432)
        database = self.db_config.get("database", "")
        user = self.db_config.get("user", "")

        return f"postgresql://{user}:******@{host}:{port}/{database}"

    def export(self, data: pd.DataFrame) -> bool:
        """Export DataFrame to PostgreSQL database.

        Args:
            data: DataFrame to export

        Returns:
            Boolean indicating success

        Raises:
            ExporterException: If export operation fails
        """
        table_name = self.db_config.get("table_name", "university_rankings")
        schema = self.db_config.get("schema", "public")
        if_exists = self.db_config.get(
            "if_exists", "replace"
        )  # Options: fail, replace, append

        try:
            logger.info(
                f"Exporting {len(data)} records to PostgreSQL table {schema}.{table_name}"
            )

            # Handle table schema
            if self.db_config.get("create_schema", True):
                self._ensure_table_schema(data, table_name, schema)

            # Export data to database
            data.to_sql(
                name=table_name,
                con=self.engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
                chunksize=1000,  # Process in chunks to avoid memory issues
            )

            logger.info(
                f"Successfully exported data to PostgreSQL table {schema}.{table_name}"
            )
            return True

        except SQLAlchemyError as e:
            raise ExporterException(f"Database export failed: {e}")
        except Exception as e:
            raise ExporterException(f"Export operation failed: {e}")

    def _ensure_table_schema(
        self, data: pd.DataFrame, table_name: str, schema: str
    ) -> None:
        """Create or verify table schema if it doesn't exist.

        Args:
            data: DataFrame containing the data to be exported
            table_name: Name of the target table
            schema: Database schema name

        Raises:
            ExporterException: If schema creation fails
        """
        if not self.db_config.get("manage_schema", False):
            # Skip schema management if disabled
            return

        try:
            metadata = MetaData(schema=schema)

            # Check if table exists
            inspector = inspect(self.engine)
            if inspector.has_table(table_name, schema=schema):
                logger.debug(f"Table {schema}.{table_name} already exists")
                return

            # Define table columns based on DataFrame
            columns = []

            # Add rank as primary key if present
            if "rank" in data.columns:
                columns.append(Column("rank", Integer, primary_key=True))

            # Add other columns based on data types
            for column_name, dtype in data.dtypes.items():
                if column_name == "rank" and "rank" in [col.name for col in columns]:
                    continue  # Skip rank if already added as primary key

                if dtype == "object":
                    columns.append(Column(column_name, String(255)))  # type: ignore
                elif dtype == "float64":
                    columns.append(Column(column_name, Float))  # type: ignore
                elif dtype == "int64":
                    columns.append(Column(column_name, Integer))  # type: ignore
                else:
                    columns.append(Column(column_name, String(255)))  # type: ignore

            # Create table
            table = Table(table_name, metadata, *columns)
            metadata.create_all(self.engine)
            logger.info(f"Created table {schema}.{table_name}")

        except SQLAlchemyError as e:
            raise ExporterException(f"Failed to create table schema: {e}")
