"""
Logging configuration for uQCme.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_file: Path to the log file. If None, console only.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Use a specific logger for the application
    logger = logging.getLogger('uQCme')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Setup file logging if path provided
    if log_file:
        try:
            log_path = Path(log_file)
            log_dir = log_path.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create file handler
            file_handler = logging.FileHandler(str(log_path), mode='a')
            file_handler.setLevel(logging.INFO)
            
            # Create formatter (TSV format for file)
            file_formatter = logging.Formatter(
                '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
        except (OSError, IOError) as e:
            # Fallback to console warning if file logging fails
            print(f"Warning: Could not setup file logging to {log_file}: {e}")
    
    return logger
