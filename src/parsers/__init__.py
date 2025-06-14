"""Parser modules for processing scraped data."""

# Import base parser
from .base_parser import BaseParser

# Import specific parsers
from .rankings_parser import RankingsParser
from .university_detail_parser import UniversityDetailParser

# Expose these classes for direct import from the package
__all__ = [
    "BaseParser",
    "RankingsParser",
    "UniversityDetailParser",
]
