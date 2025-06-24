"""Exporter modules for data export to various formats."""

# Import base classes
from .base_exporter import BaseExporter

# Import file exporters (always available)
from .file_exporter import CSVExporter, JSONExporter, ExcelExporter

# Import factory function
from .exporter_factory import create_exporter

# Import PostgreSQL exporter if available
try:
    from .postgres_exporter import PostgreSQLExporter

    __all__ = [
        "BaseExporter",
        "CSVExporter",
        "JSONExporter",
        "ExcelExporter",
        "PostgreSQLExporter",
        "create_exporter",
    ]
except ImportError:
    __all__ = [
        "BaseExporter",
        "CSVExporter",
        "JSONExporter",
        "ExcelExporter",
        "create_exporter",
    ]
