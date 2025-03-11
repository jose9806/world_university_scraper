"""Configuration loading and validation."""

import logging
from pathlib import Path
from typing import Dict, Any

import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Dict containing configuration values

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    logger.info(f"Loading configuration from {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    logger.debug(f"Loaded configuration: {config}")
    return config
