"""Base exporter class for all exporters."""

import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


class BaseExporter:
    """Base class for all data exporters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the exporter with configuration.

        Args:
            config: Exporter configuration dictionary
        """
        self.config = config

    def export(self, data: pd.DataFrame) -> bool:
        """Export data to the target destination.

        Args:
            data: DataFrame to export

        Returns:
            Boolean indicating success

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement export method")
