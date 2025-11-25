"""
Custom exceptions for uQCme.
"""


class UQCMeError(Exception):
    """Base exception for all uQCme errors."""


class ConfigError(UQCMeError):
    """Raised when there is an issue with the configuration."""


class DataLoadError(UQCMeError):
    """Raised when there is an issue loading data or files."""


class ValidationError(UQCMeError):
    """Raised when data validation fails."""


class ProcessingError(UQCMeError):
    """Raised when an error occurs during QC processing."""

