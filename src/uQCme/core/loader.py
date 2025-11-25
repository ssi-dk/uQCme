"""Data loading utilities for uQCme."""

import pandas as pd
import requests
import urllib3
import yaml
from typing import Union, Dict, Any
import logging
from pandera.errors import SchemaError
from .config import UQCMeConfig, DataInput
from .exceptions import ConfigError, DataLoadError, ValidationError
from .schemas import RunDataSchema

logger = logging.getLogger(__name__)


def load_config_from_file(config_path: str) -> UQCMeConfig:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        UQCMeConfig: Loaded configuration model.
        
    Raises:
        ConfigError: If file cannot be read or parsed.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
            return UQCMeConfig(**config_dict)
    except (IOError, yaml.YAMLError, Exception) as e:
        raise ConfigError(
            f"Failed to load configuration from {config_path}: {e}"
        )


def load_data_from_config(
    data_config: Union[str, Dict[str, Any], DataInput]
) -> pd.DataFrame:

    """
    Load data from a file or API based on configuration.
    
    Args:
        data_config: Configuration for data source. Can be a string
                    (file path), a dictionary, or a DataInput model.
                    
    Returns:
        pd.DataFrame: Loaded data.
        
    Raises:
        ConfigError: If configuration is invalid.
        DataLoadError: If data cannot be loaded.
    """
    try:
        df = None
        if isinstance(data_config, DataInput):
            if data_config.api_call:
                df = load_data_from_api(data_config.api_call)
            elif data_config.file:
                df = pd.read_csv(data_config.file, sep='\t')
            else:
                # If both are None, check if it was initialized empty
                # For now, raise error if neither is set
                error_msg = "Either 'file' or 'api_call' must be specified"
                raise ConfigError(error_msg)
                
        elif isinstance(data_config, dict):
            # New structure with file/api_call options
            if data_config.get('api_call'):
                # Load data from API
                api_url = data_config['api_call']
                df = load_data_from_api(api_url)
            elif data_config.get('file'):
                # Load data from file
                df = pd.read_csv(data_config['file'], sep='\t')
            else:
                error_msg = ("Either 'file' or 'api_call' must be "
                             "specified for data input")
                raise ConfigError(error_msg)
        else:
            # Legacy structure - direct file path
            df = pd.read_csv(data_config, sep='\t')
            
        # Validate data schema
        try:
            RunDataSchema.validate(df)
        except SchemaError as e:
            raise ValidationError(f"Data validation failed: {e}")
            
        return df
        
    except (pd.errors.ParserError, IOError) as e:
        raise DataLoadError(f"Failed to load data: {e}")
    except (ConfigError, ValidationError):
        raise
    except Exception as e:
        raise DataLoadError(f"Unexpected error loading data: {e}")


def load_data_from_api(api_url: str) -> pd.DataFrame:

    """
    Load data from API endpoint with SSL handling.
    
    Args:
        api_url: URL of the API endpoint.
        
    Returns:
        pd.DataFrame: Loaded data.
        
    Raises:
        DataLoadError: If API request fails or response is invalid.
    """
    logger.info(f"Loading data from API: {api_url}")
    
    # Make API request with JSON accept header
    headers = {'accept': 'application/json'}
    
    # Try with SSL verification first, then without if it fails
    try:
        try:
            response = requests.get(
                api_url, headers=headers, timeout=30, verify=True
            )
        except requests.exceptions.SSLError:
            warning_msg = ("SSL verification failed, retrying without "
                           "SSL verification...")
            logger.warning(warning_msg)
            # Disable SSL warnings for cleaner output
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )
            response = requests.get(
                api_url, headers=headers, timeout=30, verify=False
            )
        
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
    except requests.RequestException as e:
        raise DataLoadError(f"API request failed: {e}")
    except ValueError as e:
        raise DataLoadError(f"Invalid JSON response: {e}")
    
    # Convert to DataFrame
    # Assuming the API returns a list of records or similar structure
    # Adjust this based on actual API response format
    if isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        # If it's a dict, try to find the list of records
        # This is a heuristic, might need adjustment
        for key, value in data.items():
            if (isinstance(value, list) and len(value) > 0 and
                    isinstance(value[0], dict)):
                return pd.DataFrame(value)
        
        # If no list found, try converting the whole dict
        return pd.DataFrame([data])
    else:
        raise DataLoadError(f"Unexpected API response format: {type(data)}")
