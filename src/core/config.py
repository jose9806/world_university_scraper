"""Configuration loading and validation for the university rankings scraper."""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary containing configuration settings

    Raises:
        ValueError: If configuration is invalid
    """
    logger.info(f"Loading configuration from {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Validate configuration
    _validate_config(config)

    return config


def _validate_config(config: Dict[str, Any]):
    """Validate configuration dictionary.

    Args:
        config: Dictionary containing configuration settings

    Raises:
        ValueError: If configuration is invalid
    """
    # Check for required sections
    required_sections = ["general", "scraper"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")

    # If using Selenium, check for selenium section
    if config.get("scraper", {}).get("type") == "selenium" and "selenium" not in config:
        raise ValueError(
            "Selenium scraper type specified but no selenium configuration section found"
        )

    # Additional validation logic could be added here

    logger.info("Configuration validation successful")
