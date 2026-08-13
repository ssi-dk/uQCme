"""Typed models for the dashboard mapping extensions."""

from collections.abc import Mapping
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError as PydanticValidationError,
    field_validator,
    model_validator,
)

from .exceptions import ConfigError


MappingValue = Union[str, List[str]]
FilteringOperator = Literal["equals", "in", "contains", "range"]


# Model one data.mapping or QC.mapping entry from a mapping file.
class MappingSource(BaseModel):
    mapping: MappingValue

    model_config = ConfigDict(extra="ignore")

    @field_validator("mapping")
    @classmethod
    def validate_mapping(cls, value: MappingValue) -> MappingValue:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("mapping must not be empty")
            return value

        if not value or any(not item.strip() for item in value):
            raise ValueError("mapping lists must contain at least one name")
        return value


# Model the reusable data/QC mapping reference used by columns and filters.
class MappingFieldReference(BaseModel):
    data: Optional[MappingSource] = None
    QC: Optional[MappingSource] = None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def require_mapping_source(self):
        if self.data is None and self.QC is None:
            raise ValueError("a field must define data.mapping or QC.mapping")
        return self


# Model one explicit FilteringSection filter condition.
class FilteringCondition(MappingFieldReference):
    operator: FilteringOperator
    value: Any = None
    values: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("min", "max", mode="before")
    @classmethod
    def validate_numeric_bound(cls, value):
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("range bounds must be numeric")
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ValueError("range bounds must be numeric") from error

    @model_validator(mode="after")
    def validate_operator_values(self):
        value_fields = {"value", "values", "min", "max"}
        allowed_fields = {
            "equals": {"value"},
            "in": {"values"},
            "contains": {"value"},
            "range": {"min", "max"},
        }[self.operator]
        provided_fields = self.model_fields_set & value_fields
        unexpected_fields = provided_fields - allowed_fields
        if unexpected_fields:
            fields = ", ".join(sorted(unexpected_fields))
            raise ValueError(f"operator '{self.operator}' does not accept: {fields}")

        if self.operator in {"equals", "contains"}:
            if "value" not in self.model_fields_set or self.value is None:
                raise ValueError(f"operator '{self.operator}' requires value")

        if self.operator == "equals" and isinstance(
            self.value, (dict, list, set, tuple)
        ):
            raise ValueError("operator 'equals' requires a scalar value")

        if self.operator == "contains" and not isinstance(self.value, str):
            raise ValueError("operator 'contains' requires a string value")

        if self.operator == "in" and (
            "values" not in self.model_fields_set
            or self.values is None
            or not self.values
        ):
            raise ValueError("operator 'in' requires a non-empty values list")

        if self.operator == "range":
            has_min = "min" in self.model_fields_set and self.min is not None
            has_max = "max" in self.model_fields_set and self.max is not None
            if not has_min and not has_max:
                raise ValueError("operator 'range' requires min or max")

        return self


# Model one named preset and its ordered columns and filters.
class FilteringSection(BaseModel):
    columns: Dict[str, MappingFieldReference]
    filters: Dict[str, FilteringCondition]

    model_config = ConfigDict(extra="forbid")


# Model the optional top-level FilteringSections object.
class FilteringSectionsConfig(BaseModel):
    sections: Dict[str, FilteringSection] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


# Parse the optional dashboard mapping extension and expose configuration errors.
def parse_filtering_sections(
    mapping_config: Optional[Mapping[str, Any]],
) -> FilteringSectionsConfig:
    if mapping_config is None:
        return FilteringSectionsConfig()
    if not isinstance(mapping_config, Mapping):
        raise ConfigError("Mapping YAML must contain a mapping at its root")
    if "FilteringSections" not in mapping_config:
        return FilteringSectionsConfig()

    raw_sections = mapping_config["FilteringSections"]
    if not isinstance(raw_sections, Mapping):
        raise ConfigError("FilteringSections must be a mapping of named sections")

    try:
        return FilteringSectionsConfig(sections=raw_sections)
    except PydanticValidationError as error:
        raise ConfigError("Invalid FilteringSections mapping: " + str(error)) from error
