"""Data processor for rankings data."""

import logging
from typing import Dict, Any, List
import logging
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
        """Process parsed data."""
        logger.info("Processing university rankings data")

        # Debug the input data
        if not data:
            logger.warning("Empty data received from parser")
            # Return an empty DataFrame with the required columns
            return pd.DataFrame(columns=[
                    'rank', 'name', 'country', 'overall_score', 'teaching_score',
                    'research_score', 'citations_score', 'industry_income_score',
                    'international_outlook_score'
                ])

        logger.info(f"Processing {len(data)} university records")

        # Create DataFrame
        df = pd.DataFrame(data)

        # Apply processing steps
        df = self._handle_missing_values(df)
        df = self._normalize_scores(df)

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the DataFrame."""
        logger.info(f"DataFrame columns: {list(df.columns)}")

        # Define the score columns we expect
        score_columns = [
            "overall_score",
            "teaching_score",
            "research_score",
            "citations_score",
            "industry_income_score",
            "international_outlook_score",
        ]

        # Only process columns that exist in the DataFrame
        existing_score_columns = [col for col in score_columns if col in df.columns]

        if existing_score_columns:
            logger.info(f"Filling NA values for columns: {existing_score_columns}")
            df[existing_score_columns] = df[existing_score_columns].fillna(0)
        else:
            logger.warning("No score columns found in DataFrame")

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
