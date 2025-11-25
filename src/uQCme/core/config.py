from typing import Dict, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator


class DataInput(BaseModel):
    file: Optional[str] = None
    api_call: Optional[str] = None


class QCInput(BaseModel):
    data: Union[str, DataInput, Dict[str, Any]] = Field(
        default_factory=DataInput
    )
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
    data: Union[str, DataInput, Dict[str, Any]] = Field(
        default_factory=DataInput
    )
    mapping: str
    qc_rules: str
    qc_tests: str
    warnings: Optional[str] = None


class DashboardConfig(BaseModel):
    categorical_filter_threshold: int = 20
    section_toggle_columns: int = 3
    max_displayed_rules: int = 10


class AppConfig(BaseModel):
    server: AppServer = Field(default_factory=AppServer)
    input: AppInput
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    ui_styling: Optional[Dict[str, Any]] = None
    priority_colors: Optional[Dict[Union[int, str], Any]] = None


class LogConfig(BaseModel):
    file: str = "uqcme.log"


class UQCMeConfig(BaseModel):
    title: str = "uQCme - Microbial QC Reporter"
    version: str = "0.1.0"
    qc: Optional[QCConfig] = None
    app: Optional[AppConfig] = None
    log: LogConfig = Field(default_factory=LogConfig)
    outcome_priorities: Optional[Dict[str, int]] = None

    @field_validator('qc', 'app', mode='before')
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        return v
