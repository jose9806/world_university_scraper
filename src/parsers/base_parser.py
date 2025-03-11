"""Base parser class for all parsers."""

import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BaseParser:
    """Base class for all parsers with common functionality."""

    def __init__(self):
        """Initialize base parser."""
        pass

    def _create_soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML.

        Args:
            html: Raw HTML content

        Returns:
            BeautifulSoup object for parsing
        """
        logger.debug("Creating BeautifulSoup object")
        return BeautifulSoup(html, "html.parser")

    def parse(self, content: str) -> List[Dict[str, Any]]:
        """Parse content into structured data.

        Args:
            content: Raw content to parse

        Returns:
            List of dictionaries containing structured data

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement parse method")
