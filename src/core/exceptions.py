"""Custom exceptions for the university rankings scraper."""


class ScraperException(Exception):
    """Exception raised for errors in the scraper."""

    pass


class ParserException(Exception):
    """Exception raised for errors in the parser."""

    pass


class PipelineException(Exception):
    """Exception raised for errors in the scraping pipeline."""

    pass


class ConfigException(Exception):
    """Exception raised for errors in the configuration."""

    pass
