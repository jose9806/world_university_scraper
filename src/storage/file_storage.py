"""File storage for data persistence."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Union

import pandas as pd

from utils.exceptions import StorageException

logger = logging.getLogger(__name__)


class FileStorage:
    """Handles file storage operations for scraped data."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize file storage with configuration.

        Args:
            config: Storage configuration dictionary
        """
        self.config = config
        self.base_path = Path(config.get("base_path", "data"))

        # Ensure directories exist
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensure all required directories exist."""
        os.makedirs(self.base_path / "raw", exist_ok=True)
        os.makedirs(self.base_path / "processed", exist_ok=True)
        os.makedirs(self.base_path / "exports", exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp for filenames.

        Returns:
            Formatted timestamp string
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def save_raw_data(self, data: str) -> Path:
        """Save raw scraped data.

        Args:
            data: Raw HTML or other scraped content

        Returns:
            Path to saved file
        """
        timestamp = self._get_timestamp()
        filename = f"rankings_raw_{timestamp}.html"
        filepath = self.base_path / "raw" / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(data)

            logger.info(f"Saved raw data to {filepath}")
            return filepath
        except Exception as e:
            raise StorageException(f"Failed to save raw data: {e}")

    def save_processed_data(self, data: pd.DataFrame) -> Path:
        """Save processed data.

        Args:
            data: Processed DataFrame

        Returns:
            Path to saved file
        """
        timestamp = self._get_timestamp()
        filename = f"rankings_processed_{timestamp}.pkl"
        filepath = self.base_path / "processed" / filename

        try:
            data.to_pickle(filepath)
            logger.info(f"Saved processed data to {filepath}")
            return filepath
        except Exception as e:
            raise StorageException(f"Failed to save processed data: {e}")

    def save_exported_data(self, data: Union[str, bytes], format_name: str) -> Path:
        """Save exported data.

        Args:
            data: Exported data content
            format_name: Export format name

        Returns:
            Path to saved file
        """
        timestamp = self._get_timestamp()
        filename = f"rankings_export_{timestamp}.{format_name}"
        filepath = self.base_path / "exports" / filename

        try:
            # Different handling based on format
            if isinstance(data, str):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(data)
            else:
                with open(filepath, "wb") as f:
                    f.write(data)

            logger.info(f"Saved {format_name} export to {filepath}")
            return filepath
        except Exception as e:
            raise StorageException(f"Failed to save exported data: {e}")
