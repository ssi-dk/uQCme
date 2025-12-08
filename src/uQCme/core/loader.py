"""Data loading utilities for uQCme."""

import pandas as pd
import requests
import urllib3
import yaml
from typing import Union, Dict, Any, Optional
import logging
from pandera.errors import SchemaError
from .config import UQCMeConfig, DataInput
from .exceptions import ConfigError, DataLoadError, ValidationError
from .schemas import RunDataSchema

logger = logging.getLogger(__name__)


def _get_column_mappings(mapping_config: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract column mappings from mapping config.
    
    Looks for fields where 'QC.mapping' contains a target column name and returns
    a dict mapping from source column (data.mapping) to target column (QC.mapping).
    
    The mapping structure is:
    - data.mapping: source column name in input data
    - QC.mapping: target column name(s) in processed data
    
    Args:
        mapping_config: The mapping configuration dictionary.
        
    Returns:
        Dict mapping source column names to target column names.
    """
    column_mappings = {}
    
    if not mapping_config or 'Sections' not in mapping_config:
        return column_mappings
    
    for section_data in mapping_config['Sections'].values():
        for field_config in section_data.values():
            if not isinstance(field_config, dict):
                continue
            
            qc_config = field_config.get('QC', {})
            qc_mapping = qc_config.get('mapping')
            data_config = field_config.get('data', {})
            data_mapping = data_config.get('mapping')
            
            if not data_mapping:
                continue
                
            # Handle both string and list QC mappings
            if isinstance(qc_mapping, str):
                qc_targets = [qc_mapping]
            elif isinstance(qc_mapping, list):
                qc_targets = qc_mapping
            else:
                continue
            
            # Map the data column to each QC target that's a standard field
            standard_fields = ['sample_name', 'species']
            for target in qc_targets:
                if target in standard_fields:
                    column_mappings[data_mapping] = target
                    break  # Only map to first matching standard field
    
    return column_mappings


def _get_sample_name_source(mapping_config: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Extract the source column name that should be renamed to 'sample_name'.
    
    Looks for a field where 'QC.mapping' is 'sample_name' and returns the 
    'data.mapping' value (the original column name in the input data that
    should be renamed to sample_name).
    
    The mapping structure is:
    - data.mapping: source column name in input data
    - QC.mapping: target column name in processed data
    
    Args:
        mapping_config: The mapping configuration dictionary.
        
    Returns:
        The source column name to rename to 'sample_name', or None if not found.
    """
    if not mapping_config or 'Sections' not in mapping_config:
        return None
    
    for section_data in mapping_config['Sections'].values():
        for field_config in section_data.values():
            if not isinstance(field_config, dict):
                continue
            
            # Check if this field's QC mapping targets 'sample_name'
            qc_config = field_config.get('QC', {})
            qc_mapping = qc_config.get('mapping')
            
            if qc_mapping == 'sample_name':
                # Get the source column from data.mapping
                data_config = field_config.get('data', {})
                data_mapping = data_config.get('mapping')
                if data_mapping:
                    return data_mapping
    
    return None


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
    data_config: Union[str, Dict[str, Any], DataInput],
    mapping_config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:

    """
    Load data from a file or API based on configuration.
    
    Args:
        data_config: Configuration for data source. Can be a string
                    (file path), a dictionary, or a DataInput model.
        mapping_config: Optional mapping configuration that defines
                       column name mappings (e.g., QC.mapping -> sample_name).
                    
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
            
        # Apply column mappings from configuration
        if df is not None and mapping_config:
            column_mappings = _get_column_mappings(mapping_config)
            rename_map = {}
            
            for source_col, target_col in column_mappings.items():
                # Only rename if source exists and target doesn't
                if source_col in df.columns and target_col not in df.columns:
                    rename_map[source_col] = target_col
            
            if rename_map:
                df = df.rename(columns=rename_map)
        
        # Fallback for sample_name if not mapped
        if df is not None and 'sample_name' not in df.columns:
            sample_name_source = _get_sample_name_source(mapping_config)
            if sample_name_source and sample_name_source in df.columns:
                df = df.rename(columns={sample_name_source: 'sample_name'})
            elif 'sampleName' in df.columns:
                # Fallback: try camelCase version
                df = df.rename(columns={'sampleName': 'sample_name'})

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
    except requests.exceptions.Timeout as e:
        raise DataLoadError(
            f"API request timed out after 30 seconds: {e}",
            error_type="timeout"
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        if status_code == 502:
            raise DataLoadError(
                f"API returned 502 Bad Gateway error. The server may be "
                f"overloaded or temporarily unavailable: {e}",
                error_type="502",
                status_code=502
            )
        elif status_code == 504:
            raise DataLoadError(
                f"API returned 504 Gateway Timeout error. The request "
                f"took too long to process: {e}",
                error_type="timeout",
                status_code=504
            )
        else:
            raise DataLoadError(
                f"API request failed with HTTP {status_code}: {e}",
                error_type="http_error",
                status_code=status_code
            )
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
