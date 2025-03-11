"""Custom exceptions for the application."""


class BaseException(Exception):
    """Base exception for all application exceptions."""
    pass


class ScraperException(BaseException):
    """Exception raised for errors in the scraper."""
    pass


class ParserException(BaseException):
    """Exception raised for errors in the parser."""
    pass


class ProcessorException(BaseException):
    """Exception raised for errors in the data processor."""
    pass


class ExporterException(BaseException):
    """Exception raised for errors in the exporter."""
    pass


class StorageException(BaseException):
    """Exception raised for errors in the storage."""
    pass


class ConfigException(BaseException):
    """Exception raised for errors in the configuration."""
    pass
