"""Simple file exporters for CSV and JSON."""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

import pandas as pd

from .base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Exports data to CSV files."""

    def export(self, data: pd.DataFrame) -> str:
        """Export DataFrame to CSV file.

        Args:
            data: DataFrame to export

        Returns:
            Path to exported file
        """
        try:
            # Get output directory from config
            output_dir = Path(self.config.get("output_dir", "data/exports/csv"))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.get("filename", f"export_{timestamp}.csv")

            # Replace {timestamp} placeholder if present
            filename = filename.replace("{timestamp}", timestamp)

            # Export to CSV
            output_path = output_dir / filename
            data.to_csv(
                output_path,
                index=self.config.get("index", False),
                encoding=self.config.get("encoding", "utf-8"),
                sep=self.config.get("sep", ","),
            )

            logger.info(f"Exported {len(data)} records to CSV: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export to CSV: {str(e)}")
            raise


class JSONExporter(BaseExporter):
    """Exports data to JSON files."""

    def export(self, data: pd.DataFrame) -> str:
        """Export DataFrame to JSON file.

        Args:
            data: DataFrame to export

        Returns:
            Path to exported file
        """
        try:
            # Get output directory from config
            output_dir = Path(self.config.get("output_dir", "data/exports/json"))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.get("filename", f"export_{timestamp}.json")

            # Replace {timestamp} placeholder if present
            filename = filename.replace("{timestamp}", timestamp)

            # Convert DataFrame to dict
            data_dict = data.to_dict(orient="records")

            # Add metadata if configured
            if self.config.get("include_metadata", False):
                export_data = {
                    "metadata": {
                        "export_timestamp": datetime.now().isoformat(),
                        "record_count": len(data),
                        "columns": list(data.columns),
                        "data_types": {
                            col: str(dtype) for col, dtype in data.dtypes.items()
                        },
                    },
                    "data": data_dict,
                }
            else:
                export_data = data_dict

            # Export to JSON
            output_path = output_dir / filename
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    export_data,
                    f,
                    indent=2 if self.config.get("pretty_print", True) else None,
                    ensure_ascii=self.config.get("ensure_ascii", False),
                )

            logger.info(f"Exported {len(data)} records to JSON: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export to JSON: {str(e)}")
            raise


class ExcelExporter(BaseExporter):
    """Exports data to Excel files."""

    def export(self, data: pd.DataFrame) -> str:
        """Export DataFrame to Excel file.

        Args:
            data: DataFrame to export

        Returns:
            Path to exported file
        """
        try:
            # Get output directory from config
            output_dir = Path(self.config.get("output_dir", "data/exports/excel"))
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.config.get("filename", f"export_{timestamp}.xlsx")

            # Replace {timestamp} placeholder if present
            filename = filename.replace("{timestamp}", timestamp)

            # Export to Excel
            output_path = output_dir / filename

            # Use ExcelWriter for more control
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                # Write main data
                sheet_name = self.config.get("sheet_name", "Data")
                data.to_excel(
                    writer, sheet_name=sheet_name, index=self.config.get("index", False)
                )

                # Add summary sheet if configured
                if self.config.get("include_summary", False):
                    summary_data = {
                        "Metric": ["Total Records", "Columns", "Export Date"],
                        "Value": [
                            len(data),
                            len(data.columns),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ],
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)

            logger.info(f"Exported {len(data)} records to Excel: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export to Excel: {str(e)}")
            raise
