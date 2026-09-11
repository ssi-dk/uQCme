import re
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class DataInput(BaseModel):
    file: Optional[str] = None
    api_call: Optional[str] = None
    api_query_params: Optional[Union[List[str], Dict[str, str]]] = None
    api_bearer_token: Optional[str] = None
    api_bearer_token_env: Optional[str] = None
    api_headers: Optional[Dict[str, str]] = None


class QCInput(BaseModel):
    data: Union[str, DataInput, Dict[str, Any]] = Field(default_factory=DataInput)
    mapping: str
    qc_rules: str
    qc_tests: str


class QCOutput(BaseModel):
    results: str = "qc_results.tsv"
    warnings: str = "qc_warnings.tsv"


class QCConfig(BaseModel):
    input: QCInput
    output: QCOutput


class AppServer(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8501


class AppInput(BaseModel):
    data: Union[str, DataInput, Dict[str, Any]] = Field(default_factory=DataInput)
    mapping: str
    qc_rules: str
    qc_tests: str
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
    headers: Optional[Dict[str, str]] = None

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
    default_visible_sections: Dict[str, bool] = Field(default_factory=dict)
    default_filters: Dict[str, Any] = Field(default_factory=dict)


class DashboardConfig(BaseModel):
    categorical_filter_threshold: int = 20
    max_displayed_rules: int = 10
    table_height: int = Field(default=3600, ge=200)
    debug_api: bool = False
    report_mode: ReportModeConfig = Field(default_factory=ReportModeConfig)
    sample_api_actions: List[SampleApiAction] = Field(default_factory=list)


# Validate configuration-driven colors used by dashboard UI surfaces.
class UIStylingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unsupported_species_color_light: str = "#1D4ED8"
    unsupported_species_color_dark: str = "#60A5FA"
    missing_species_color: str = "#808080"
    missing_species_opacity: float = Field(default=0.15, ge=0, le=1)

    @field_validator(
        "unsupported_species_color_light",
        "unsupported_species_color_dark",
        "missing_species_color",
    )
    @classmethod
    def validate_species_color(cls, value):
        return cls._validate_hex_color(value)

    # Validate the color format shared by the species support cues.
    @staticmethod
    def _validate_hex_color(value):
        if not isinstance(value, str) or HEX_COLOR_PATTERN.fullmatch(value) is None:
            raise ValueError("species colors must use six-digit hex format (#RRGGBB)")
        return value


class AppConfig(BaseModel):
    server: AppServer = Field(default_factory=AppServer)
    input: AppInput
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    ui_styling: UIStylingConfig = Field(default_factory=UIStylingConfig)
    priority_colors: Optional[Dict[Union[int, str], Any]] = None

    @field_validator("ui_styling", mode="before")
    @classmethod
    def default_ui_styling(cls, value):
        if value is None:
            return {}
        return value


class LogConfig(BaseModel):
    file: str = "uqcme.log"


class UQCMeConfig(BaseModel):
    title: str = "uQCme - Microbial QC Reporter"
    version: str = "0.9.2"
    qc: Optional[QCConfig] = None
    app: Optional[AppConfig] = None
    log: LogConfig = Field(default_factory=LogConfig)
    outcome_priorities: Optional[Dict[str, int]] = None

    @field_validator("qc", "app", mode="before")
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        return v
