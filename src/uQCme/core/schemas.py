"""
Pandera schemas for data validation.
"""

import pandera.pandas as pa
from pandera.typing import Series
from typing import Optional


class QCRulesSchema(pa.DataFrameModel):
    """Schema for QC rules definition file."""
    rule_id: Series[str] = pa.Field(
        unique=True, description="Unique identifier for the rule"
    )
    species: Series[str] = pa.Field(description="Target species or 'all'")
    assembly_type: Series[str] = pa.Field(
        description="Target assembly type or 'all'"
    )
    software: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Software used to generate the metric"
    )
    field: Series[str] = pa.Field(description="Metric name to evaluate")
    operator: Series[str] = pa.Field(
        isin=["=", "!=", ">", "<", ">=", "<=", "regex", "contains"],
        description="Comparison operator"
    )
    value: Series[str] = pa.Field(description="Threshold value")
    special_field: Optional[Series[str]] = pa.Field(
        nullable=True, description="Optional special field reference"
    )

    class Config:
        coerce = True
        strict = False  # Allow extra columns


class QCTestsSchema(pa.DataFrameModel):
    """Schema for QC tests/outcomes definition file."""
    outcome_id: Series[str] = pa.Field(
        unique=True, description="Unique identifier for the outcome"
    )
    outcome_name: Series[str] = pa.Field(
        description="Display name for the outcome"
    )
    description: Series[str] = pa.Field(
        description="Description of the outcome"
    )
    priority: Series[int] = pa.Field(
        ge=1, description="Priority level (higher number = higher priority)"
    )
    passed_rule_conditions: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Comma-separated list of rules that must NOT fail (all-must-pass logic)"
    )
    failed_rule_conditions: Optional[Series[str]] = pa.Field(
        nullable=True,
        description="Comma-separated list of rules where ANY failure triggers (OR logic)"
    )
    action_required: Series[str] = pa.Field(
        description="Action required for this outcome"
    )

    class Config:
        coerce = True
        strict = False


class RunDataSchema(pa.DataFrameModel):
    """
    Base schema for run data.
    Note: Actual columns depend on the input data, but we enforce some basics.
    """
    sample_name: Series[str] = pa.Field(
        unique=True, description="Unique sample identifier"
    )
    species: Optional[Series[str]] = pa.Field(
        nullable=True, description="Species name"
    )

    class Config:
        coerce = True
        strict = False  # Allow extra columns (metrics)
