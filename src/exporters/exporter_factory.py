"""Factory for creating appropriate exporters."""

import logging
from typing import Dict, Type, Any

from .base_exporter import BaseExporter
from .postgres_exporter import PostgreSQLExporter
from ..utils.exceptions import ExporterException

logger = logging.getLogger(__name__)

EXPORTERS: Dict[str, Type[BaseExporter]] = {
    "postgres": PostgreSQLExporter,
}


def create_exporter(exporter_type: str, config: Dict[str, Any]) -> BaseExporter:
    """Create appropriate exporter based on the specified type.

    Args:
        exporter_type: Type of exporter to create
        config: Configuration for the exporter

    Returns:
        Exporter instance

    Raises:
        ExporterException: If exporter type is not supported
    """
    exporter_type = exporter_type.lower()

    if exporter_type not in EXPORTERS:
        available_exporters = ", ".join(EXPORTERS.keys())
        raise ExporterException(
            f"Unsupported exporter type: {exporter_type}. "
            f"Available exporters: {available_exporters}"
        )

    exporter_class = EXPORTERS[exporter_type]
    logger.debug(f"Creating exporter of type: {exporter_type}")

    return exporter_class(config)
