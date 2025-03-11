"""Data processor for rankings data."""

import logging
from typing import Dict, Any, List

import pandas as pd

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes parsed university rankings data."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize data processor with configuration.

        Args:
            config: Processor configuration dictionary
        """
        self.config = config

    def process(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process parsed university data.

        Args:
            data: List of dictionaries containing university data

        Returns:
            Processed DataFrame of university rankings
        """
        logger.info("Processing university rankings data")

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(data)

        # Remove duplicates if any
        df = df.drop_duplicates()

        # Handle missing values
        df = self._handle_missing_values(df)

        # Add additional computed columns
        df = self._add_computed_columns(df)

        # Sort by rank
        df = df.sort_values("rank")

        logger.info(f"Processed {len(df)} universities")
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the DataFrame.

        Args:
            df: DataFrame containing university data

        Returns:
            DataFrame with missing values handled
        """
        # For score columns, fill missing values with 0 or other approach
        # based on configuration
        score_columns = [
            "overall_score",
            "teaching_score",
            "research_score",
            "citations_score",
            "industry_income_score",
            "international_outlook_score",
        ]

        missing_strategy = self.config.get("missing_values_strategy", "zero")

        if missing_strategy == "zero":
            df[score_columns] = df[score_columns].fillna(0)
        elif missing_strategy == "mean":
            for col in score_columns:
                df[col] = df[col].fillna(df[col].mean())
        elif missing_strategy == "median":
            for col in score_columns:
                df[col] = df[col].fillna(df[col].median())

        return df

    def _add_computed_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed columns to the DataFrame.

        Args:
            df: DataFrame containing university data

        Returns:
            DataFrame with additional computed columns
        """
        # Add a column for score category (e.g., "Excellent", "Good", etc.)
        if "overall_score" in df.columns:
            df["score_category"] = pd.cut(
                df["overall_score"],
                bins=[0, 30, 50, 70, 90, 100],
                labels=["Poor", "Fair", "Good", "Very Good", "Excellent"],
            )

        # Add continent based on country
        # This would require a country-to-continent mapping

        return df
