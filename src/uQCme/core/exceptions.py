"""
Custom exceptions for uQCme.
"""


class UQCMeError(Exception):
    """Base exception for all uQCme errors."""


class ConfigError(UQCMeError):
    """Raised when there is an issue with the configuration."""


class DataLoadError(UQCMeError):
    """Raised when there is an issue loading data or files."""
    
    def __init__(self, message: str, error_type: str = None,
                 status_code: int = None):
        super().__init__(message)
        self.error_type = error_type  # 'timeout', '502', 'http_error', etc.
        self.status_code = status_code


class ValidationError(UQCMeError):
    """Raised when data validation fails."""


class ProcessingError(UQCMeError):
    """Raised when an error occurs during QC processing."""

