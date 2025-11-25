"""Utility functions for uQCme."""

import pandas as pd
import requests
import urllib3
import yaml
from io import StringIO
from typing import Union, Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_config_from_file(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Dict[str, Any]: Loaded configuration.
        
    Raises:
        IOError: If file cannot be read.
        yaml.YAMLError: If YAML parsing fails.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_data_from_config(
    data_config: Union[str, Dict[str, Any]]
) -> pd.DataFrame:

    """
    Load data from a file or API based on configuration.
    
    Args:
        data_config: Configuration for data source. Can be a string (file path)
                    or a dictionary with 'file' or 'api_call' keys.
                    
    Returns:
        pd.DataFrame: Loaded data.
        
    Raises:
        ValueError: If configuration is invalid.
        IOError: If file cannot be read.
        requests.RequestException: If API call fails.
    """
    if isinstance(data_config, dict):
        # New structure with file/api_call options
        if data_config.get('api_call'):
            # Load data from API
            api_url = data_config['api_call']
            return load_data_from_api(api_url)
        elif data_config.get('file'):
            # Load data from file
            return pd.read_csv(data_config['file'], sep='\t')
        else:
            error_msg = ("Either 'file' or 'api_call' must be "
                         "specified for data input")
            raise ValueError(error_msg)
    else:
        # Legacy structure - direct file path
        return pd.read_csv(data_config, sep='\t')


def load_data_from_api(api_url: str) -> pd.DataFrame:

    """
    Load data from API endpoint with SSL handling.
    
    Args:
        api_url: URL of the API endpoint.
        
    Returns:
        pd.DataFrame: Loaded data.
    """
    logger.info(f"Loading data from API: {api_url}")
    
    # Make API request with JSON accept header
    headers = {'accept': 'application/json'}
    
    # Try with SSL verification first, then without if it fails
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
    
    # Parse response based on content type
    content_type = response.headers.get('content-type', '')
    
    if content_type.startswith('application/json'):
        # Handle JSON response
        json_data = response.json()
        if isinstance(json_data, list):
            data = pd.DataFrame(json_data)
        elif isinstance(json_data, dict) and 'data' in json_data:
            data = pd.DataFrame(json_data['data'])
        else:
            data = pd.DataFrame([json_data])
    else:
        # Handle CSV/TSV response
        response_text = response.text.strip()
        
        # Check if it looks like CSV data
        if ',' in response_text and '\n' in response_text:
            # Parse as CSV
            data = pd.read_csv(StringIO(response_text))
        else:
            # Try TSV format as fallback
            data = pd.read_csv(StringIO(response_text), sep='\t')
            
    return data
