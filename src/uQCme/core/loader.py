"""Data loading utilities for uQCme."""

import copy
import os
import pandas as pd
import requests
import urllib3
import yaml
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from typing import Union, Dict, Any, Optional, List, Tuple
import logging
from pandera.errors import SchemaError
from .config import UQCMeConfig, DataInput
from .exceptions import ConfigError, DataLoadError, ValidationError
from .schemas import RunDataSchema

logger = logging.getLogger(__name__)


def _extract_api_error_detail(
    response: Optional[requests.Response]
) -> Optional[str]:
    """Extract a concise API error detail from response payload/text."""
    if response is None:
        return None

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail = payload.get('detail')
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if detail is not None:
            detail_str = str(detail).strip()
            if detail_str:
                return detail_str

    response_text = (response.text or '').strip()
    if response_text:
        # Keep fallback text bounded so error messages stay readable.
        return response_text[:500]

    return None


def _resolve_project_scope_request(
    api_url: str,
    custom_headers: Optional[Dict[str, str]] = None
) -> tuple[str, Dict[str, str]]:
    """
    Resolve request URL and headers for project scope.

    Backward compatibility:
    - If X-Project-Id is present in headers, move it to project_id query param.
    - Keep remaining headers as request headers.
    """
    headers: Dict[str, str] = {}
    project_id: Optional[str] = None

    if custom_headers:
        for key, value in custom_headers.items():
            if not key or value is None:
                continue
            key_str = str(key)
            value_str = str(value)
            if key_str.lower() == 'x-project-id':
                candidate = value_str.strip()
                if candidate:
                    project_id = candidate
            else:
                headers[key_str] = value_str

    if not project_id:
        return api_url, headers

    parsed = urlparse(api_url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    existing_project = query_params.get('project_id', [])
    if not existing_project or not existing_project[0].strip():
        query_params['project_id'] = [project_id]

    resolved_query = urlencode(query_params, doseq=True)
    resolved_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        resolved_query,
        parsed.fragment
    ))
    return resolved_url, headers


def _resolve_api_bearer_token(
    api_bearer_token: Optional[str] = None,
    api_bearer_token_env: Optional[str] = None
) -> Optional[str]:
    """Resolve bearer token from explicit config value or environment."""
    if api_bearer_token:
        return api_bearer_token

    if api_bearer_token_env:
        token = os.environ.get(api_bearer_token_env)
        if token:
            return token
        raise ConfigError(
            f"Environment variable '{api_bearer_token_env}' is not set, "
            "but it is required for API bearer token authentication."
        )

    return None


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


def _format_duplicate_value(value: Any) -> str:
    """Format duplicate value for user-facing warning messages."""
    if pd.isna(value):
        return "<missing>"

    value_str = str(value)
    if not value_str.strip():
        return "<empty>"

    return value_str


def get_unique_columns_from_mapping(
    mapping_config: Optional[Dict[str, Any]]
) -> List[str]:
    """Return mapped data columns marked as unique in mapping config."""
    unique_columns: List[str] = []
    seen = set()

    if not mapping_config or 'Sections' not in mapping_config:
        return unique_columns

    for section_data in mapping_config['Sections'].values():
        for field_config in section_data.values():
            if not isinstance(field_config, dict):
                continue

            data_config = field_config.get('data', {})
            report_config = field_config.get('report', {})
            is_unique = bool(
                data_config.get('unique') or report_config.get('unique')
            )
            if not is_unique:
                continue

            data_mapping = data_config.get('mapping')
            if isinstance(data_mapping, str) and data_mapping not in seen:
                unique_columns.append(data_mapping)
                seen.add(data_mapping)

    return unique_columns


def get_duplicate_rows_for_column(
    df: pd.DataFrame,
    column: str
) -> List[Dict[str, Any]]:
    """Return duplicate values and their 1-based row positions for a column."""
    if df.empty or column not in df.columns:
        return []

    duplicate_mask = df[column].duplicated(keep=False)
    if not duplicate_mask.any():
        return []

    duplicate_rows = df.loc[duplicate_mask, [column]].copy()
    duplicate_rows = duplicate_rows.reset_index().rename(
        columns={'index': 'row_number'}
    )
    duplicate_rows['row_number'] = duplicate_rows['row_number'] + 1

    duplicates = []
    grouped = duplicate_rows.groupby(column, dropna=False, sort=False)
    for value, group in grouped:
        duplicates.append({
            'column': column,
            'value': value,
            'rows': group['row_number'].astype(int).tolist()
        })

    return duplicates


def collect_duplicate_row_warnings(
    df: pd.DataFrame,
    columns: List[str]
) -> List[str]:
    """Build warning messages for duplicate values in selected columns."""
    warnings: List[str] = []

    for column in columns:
        for duplicate in get_duplicate_rows_for_column(df, column):
            row_numbers = ', '.join(str(row) for row in duplicate['rows'])
            value = _format_duplicate_value(duplicate['value'])
            warnings.append(
                f"Duplicate value '{value}' found in column '{column}' "
                f"at rows {row_numbers}."
            )

    return warnings


def validate_unique_columns(
    df: pd.DataFrame,
    mapping_config: Optional[Dict[str, Any]]
) -> None:
    """Validate mapped columns marked as unique."""
    errors: List[str] = []

    for column in get_unique_columns_from_mapping(mapping_config):
        for duplicate in get_duplicate_rows_for_column(df, column):
            row_numbers = ', '.join(str(row) for row in duplicate['rows'])
            value = _format_duplicate_value(duplicate['value'])
            errors.append(
                f"Column '{column}' is marked unique, but value '{value}' "
                f"appears in rows {row_numbers}."
            )

    if errors:
        raise ValidationError(
            "Unique column validation failed: " + ' '.join(errors)
        )


def validate_run_data_frame(
    df: pd.DataFrame,
    mapping_config: Optional[Dict[str, Any]] = None
) -> None:
    """Validate run data schema and mapping-driven uniqueness rules."""
    try:
        RunDataSchema.validate(df)
    except SchemaError as e:
        raise ValidationError(f"Data validation failed: {e}")

    validate_unique_columns(df, mapping_config)


def prepare_loaded_data_frame(
    df: pd.DataFrame,
    mapping_config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """Apply configured column mappings and validate loaded data."""
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

    validate_run_data_frame(df, mapping_config)
    return df


def _payload_preview(data: Any, limit: int = 20) -> Any:
    """Return a bounded preview of API payload for debug display."""
    if isinstance(data, list):
        return copy.deepcopy(data[:limit])

    if isinstance(data, dict):
        preview = {}
        for idx, (key, value) in enumerate(data.items()):
            if idx >= limit:
                preview['...'] = (
                    f"{len(data) - limit} additional top-level keys omitted"
                )
                break

            if isinstance(value, list) and len(value) > limit:
                preview[key] = copy.deepcopy(value[:limit])
            else:
                preview[key] = copy.deepcopy(value)
        return preview

    return data


def _coerce_api_payload_to_dataframe(data: Any) -> pd.DataFrame:
    """Convert API payload into a DataFrame using existing heuristics."""
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


def _load_api_payload(
    api_url: str,
    bearer_token: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None
) -> Tuple[Any, Dict[str, Any]]:
    """Load raw payload from API endpoint and return debug metadata."""
    resolved_url, resolved_headers = _resolve_project_scope_request(
        api_url, custom_headers
    )
    logger.info(f"Loading data from API: {resolved_url}")

    def _send_request(
        *,
        verify: bool,
        request_headers: Dict[str, str],
        cookies: Optional[Dict[str, str]] = None
    ):
        return requests.get(
            resolved_url,
            headers=request_headers,
            timeout=30,
            verify=verify,
            cookies=cookies
        )

    headers = {'accept': 'application/json'}
    if resolved_headers:
        headers.update(resolved_headers)
    if bearer_token:
        headers['Authorization'] = f'Bearer {bearer_token}'

    debug_info: Dict[str, Any] = {
        'resolved_url': resolved_url,
        'payload_preview': None,
        'payload_type': None,
        'status_code': None,
        'row_count': None,
        'columns': [],
    }

    try:
        verify_ssl = True
        try:
            response = _send_request(
                verify=verify_ssl,
                request_headers=headers
            )
        except requests.exceptions.SSLError:
            warning_msg = ("SSL verification failed, retrying without "
                           "SSL verification...")
            logger.warning(warning_msg)
            urllib3.disable_warnings(
                urllib3.exceptions.InsecureRequestWarning
            )
            verify_ssl = False
            response = _send_request(
                verify=verify_ssl,
                request_headers=headers
            )

        debug_info['status_code'] = response.status_code

        if response.status_code == 401 and bearer_token:
            auth_detail = _extract_api_error_detail(response)
            if auth_detail == "NOT_AUTHENTICATED":
                retry_headers = {
                    key: value for key, value in headers.items()
                    if key.lower() != 'authorization'
                }
                response = _send_request(
                    verify=verify_ssl,
                    request_headers=retry_headers,
                    cookies={'viewer_session': bearer_token}
                )
                debug_info['status_code'] = response.status_code

        response.raise_for_status()
        data = response.json()
        debug_info['payload_type'] = type(data).__name__
        debug_info['payload_preview'] = _payload_preview(data)
        return data, debug_info
    except requests.exceptions.Timeout as e:
        raise DataLoadError(
            f"API request timed out after 30 seconds: {e}",
            error_type="timeout",
            debug_info=debug_info
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        error_detail = _extract_api_error_detail(e.response)
        error_url = None
        if e.response is not None:
            error_url = getattr(e.response, 'url', None)
            debug_info['status_code'] = e.response.status_code
            try:
                payload = e.response.json()
                debug_info['payload_type'] = type(payload).__name__
                debug_info['payload_preview'] = _payload_preview(payload)
            except ValueError:
                if e.response.text:
                    debug_info['payload_type'] = 'text'
                    debug_info['payload_preview'] = e.response.text[:2000]
        if not error_url:
            error_url = resolved_url
        if status_code == 502:
            raise DataLoadError(
                f"API returned 502 Bad Gateway error for url: {error_url}. "
                "The server may be overloaded or temporarily unavailable.",
                error_type="502",
                status_code=502,
                debug_info=debug_info
            )
        elif status_code == 504:
            raise DataLoadError(
                f"API returned 504 Gateway Timeout error for url: {error_url}. "
                "The request took too long to process.",
                error_type="timeout",
                status_code=504,
                debug_info=debug_info
            )
        else:
            detail_msg = f" - {error_detail}" if error_detail else ""
            raise DataLoadError(
                f"API request failed with HTTP {status_code} "
                f"for url: {error_url}{detail_msg}",
                error_type="http_error",
                status_code=status_code,
                debug_info=debug_info
            )
    except requests.RequestException as e:
        raise DataLoadError(
            f"API request failed: {e}",
            debug_info=debug_info
        )
    except ValueError as e:
        raise DataLoadError(
            f"Invalid JSON response: {e}",
            debug_info=debug_info
        )


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
                bearer_token = _resolve_api_bearer_token(
                    api_bearer_token=data_config.api_bearer_token,
                    api_bearer_token_env=data_config.api_bearer_token_env
                )
                df = load_data_from_api(
                    data_config.api_call,
                    bearer_token=bearer_token,
                    custom_headers=data_config.api_headers
                )
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
                bearer_token = _resolve_api_bearer_token(
                    api_bearer_token=data_config.get('api_bearer_token'),
                    api_bearer_token_env=data_config.get(
                        'api_bearer_token_env'
                    )
                )
                df = load_data_from_api(
                    api_url,
                    bearer_token=bearer_token,
                    custom_headers=data_config.get('api_headers')
                )
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
            
        df = prepare_loaded_data_frame(df, mapping_config)
            
        return df
        
    except (pd.errors.ParserError, IOError) as e:
        raise DataLoadError(f"Failed to load data: {e}")
    except (ConfigError, ValidationError):
        raise
    except Exception as e:
        raise DataLoadError(f"Unexpected error loading data: {e}")


def load_data_from_api(
    api_url: str,
    bearer_token: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None
) -> pd.DataFrame:

    """
    Load data from API endpoint with SSL handling.
    
    Args:
        api_url: URL of the API endpoint.
        bearer_token: Optional bearer token for Authorization header.
        custom_headers: Optional additional headers for API requests.
        
    Returns:
        pd.DataFrame: Loaded data.
        
    Raises:
        DataLoadError: If API request fails or response is invalid.
    """
    data, _ = _load_api_payload(
        api_url,
        bearer_token=bearer_token,
        custom_headers=custom_headers
    )
    return _coerce_api_payload_to_dataframe(data)


def load_data_from_api_with_debug(
    api_url: str,
    bearer_token: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load data from API and return debug metadata for UI inspection."""
    data, debug_info = _load_api_payload(
        api_url,
        bearer_token=bearer_token,
        custom_headers=custom_headers
    )
    df = _coerce_api_payload_to_dataframe(data)
    debug_info['row_count'] = len(df)
    debug_info['columns'] = df.columns.tolist()
    return df, debug_info
