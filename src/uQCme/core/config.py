import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from uQCme.core.exceptions import ConfigError


# YAML-facing data input shape. Not validated, hence raw
class RawDataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: Optional[str] = None
    api_call: Optional[str] = None
    api_query_params: Optional[Union[list[str], dict[str, str]]] = None
    api_bearer_token: Optional[str] = None
    api_bearer_token_env: Optional[str] = None
    api_headers: Optional[dict[str, str]] = None


# Data comes from a local file path, not from an API.
@dataclass(frozen=True)
class TSVDataSource:
    path: Path


# Data comes from an API, not from a local file
@dataclass(frozen=True)
class APIDataSource:
    # Base API URL to request e.g. "https://example.org/api/data?a=123"
    call: str
    # Replace any query params in call, such as `a=123` based on the following:
    # * If None, replace nothing
    # * If a list, pick those keys in the dashboard URL, and insert/replace them into
    #   `call` to create the resulting URL
    # * If a dict e.g. {"a": "x", "b": "y"} then take key "a" from dashboard and
    #   add its value to `call` under the key "x".
    query_params: Optional[Union[list[str], dict[str, str]]] = None
    # A bearer token is essentially a password
    bearer_token: Optional[str] = None
    # Pass these as additional HTTP request headers - except "X-Project-Id", which is
    # renamed to `project_id` (for backwards compat, TODO: Remove this edge case)
    headers: Optional[dict[str, str]] = None


# Validated runtime data input with exactly one source
@dataclass(frozen=True)
class DataInput:
    source: Union[TSVDataSource, APIDataSource]


def _normalize_bearer_token(raw: RawDataInput) -> Optional[str]:
    has_literal = raw.api_bearer_token is not None
    has_env = raw.api_bearer_token_env is not None

    if has_literal and has_env:
        raise ConfigError(
            "API data input cannot specify both 'api_bearer_token' "
            "and 'api_bearer_token_env'"
        )
    if has_literal:
        return str(raw.api_bearer_token)
    if has_env:
        env_var = str(raw.api_bearer_token_env)
        token = os.environ.get(env_var)
        if token:
            return token
        raise ConfigError(
            f"Environment variable '{env_var}' is not set, "
            "but it is required for API bearer token authentication."
        )
    return None


def normalize_data_input(raw: RawDataInput) -> DataInput:
    """Convert raw YAML/legacy data config into the runtime representation."""
    has_file = raw.file is not None
    has_api = raw.api_call is not None

    if has_file and has_api:
        raise ConfigError("Data input cannot specify both 'file' and 'api_call'")
    if not has_file and not has_api:
        raise ConfigError("Data input must specify either 'file' or 'api_call'")

    if has_file:
        api_fields = {
            "api_query_params": raw.api_query_params,
            "api_bearer_token": raw.api_bearer_token,
            "api_bearer_token_env": raw.api_bearer_token_env,
            "api_headers": raw.api_headers,
        }
        present_api_fields = [
            name for name, value in api_fields.items() if value is not None
        ]
        if present_api_fields:
            joined_fields = ", ".join(present_api_fields)
            raise ConfigError(
                f"File data input cannot include API-only fields: {joined_fields}"
            )
        return DataInput(source=TSVDataSource(path=Path(str(raw.file))))

    return DataInput(
        source=APIDataSource(
            call=str(raw.api_call),
            query_params=raw.api_query_params,
            bearer_token=_normalize_bearer_token(raw),
            headers=raw.api_headers or None,
        )
    )


# Input bundle for a QC processing run; not just one QC rule
class QCInput(BaseModel):
    data: RawDataInput
    mapping: Path
    qc_rules: Path
    qc_tests: Path


# Output bundle for a QC processing run; not just one QC rule
class QCOutput(BaseModel):
    results: Path = Path("qc_results.tsv")
    warnings: Path = Path("qc_warnings.tsv")


# Overall config for QC run
class QCConfig(BaseModel):
    input: QCInput
    output: QCOutput


class AppServer(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8501


class AppInput(BaseModel):
    data: RawDataInput
    mapping: Path
    qc_rules: Path
    qc_tests: Path
    warnings: Optional[str] = None


class SampleApiAction(BaseModel):
    label: str
    api_call: str
    value_field: str
    method: str = "POST"
    api_bearer_token: Optional[str] = None
    api_bearer_token_env: Optional[str] = None
    payload_field: Optional[str] = None
    timeout_seconds: int = 30
    send_as_list: bool = True
    include_sample_ids: bool = False
    sample_ids_field: str = "sample_ids"
    headers: Optional[dict[str, str]] = None

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value):
        method = str(value or "POST").upper()
        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method not in allowed_methods:
            raise ValueError(
                f"Unsupported method '{method}'. "
                f"Allowed methods: {sorted(allowed_methods)}"
            )
        return method


class ReportModeConfig(BaseModel):
    enabled: bool = False
    default_visible_sections: dict[str, bool] = Field(default_factory=dict)
    default_filters: dict[str, Any] = Field(default_factory=dict)


class DashboardConfig(BaseModel):
    categorical_filter_threshold: int = 20
    max_displayed_rules: int = 10
    table_height: int = Field(default=3600, ge=200)
    debug_api: bool = False
    report_mode: ReportModeConfig = Field(default_factory=ReportModeConfig)
    sample_api_actions: list[SampleApiAction] = Field(default_factory=list)


class AppConfig(BaseModel):
    server: AppServer = Field(default_factory=AppServer)
    input: AppInput
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    ui_styling: Optional[dict[str, Any]] = None
    priority_colors: Optional[dict[Union[int, str], Any]] = None


class LogConfig(BaseModel):
    file: Path = Path("uqcme.log")


class UQCMeConfig(BaseModel):
    title: str = "uQCme - Microbial QC Reporter"
    version: str = "0.9.2"
    qc: Optional[QCConfig] = None
    app: Optional[AppConfig] = None
    log: LogConfig = Field(default_factory=LogConfig)
    outcome_priorities: Optional[dict[str, int]] = None

    @field_validator("qc", "app", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        return v
