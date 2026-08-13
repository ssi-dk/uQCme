"""Pure runtime resolution and dataframe filtering for dashboard presets."""

from dataclasses import dataclass
from typing import Dict, Iterator, Optional

import pandas as pd

from .mapping import (
    FilteringCondition,
    FilteringSectionsConfig,
    MappingFieldReference,
    MappingSource,
)


# Store a descriptive mapping field after it has resolved to a dataframe column.
@dataclass(frozen=True)
class ResolvedField:
    label: str
    column: str


# Store a typed filter condition after its dataframe column has been resolved.
@dataclass(frozen=True)
class ResolvedFilter:
    label: str
    column: str
    condition: FilteringCondition


# Store all runtime information needed by the dashboard for one preset.
@dataclass(frozen=True)
class ResolvedFilteringSection:
    name: str
    columns: tuple[ResolvedField, ...]
    filters: tuple[ResolvedFilter, ...]
    available: bool
    warnings: tuple[str, ...]


# Yield mapping candidates in the configured data-then-QC precedence order.
def _mapping_candidates(field: MappingFieldReference) -> Iterator[str]:
    for source in (field.data, field.QC):
        if source is None:
            continue
        yield from _source_candidates(source)


# Normalize a string or ordered list mapping source to candidate column names.
def _source_candidates(source: MappingSource) -> Iterator[str]:
    mapping = source.mapping
    if isinstance(mapping, str):
        yield mapping
        return
    yield from mapping


# Resolve the first configured mapping candidate present in the dataframe.
def _resolve_field(field: MappingFieldReference, data: pd.DataFrame) -> Optional[str]:
    for candidate in _mapping_candidates(field):
        if candidate in data.columns:
            return candidate
    return None


# Render the configured references for an actionable missing-column warning.
def _format_references(field: MappingFieldReference) -> str:
    references = []
    if field.data is not None:
        references.append(f"data.mapping={field.data.mapping!r}")
    if field.QC is not None:
        references.append(f"QC.mapping={field.QC.mapping!r}")
    return ", ".join(references)


# Create one warning for a field that cannot resolve against the loaded data.
def _missing_field_warning(
    section_name: str,
    field_kind: str,
    field_label: str,
    field: MappingFieldReference,
) -> str:
    references = _format_references(field)
    return (
        f"FilteringSection '{section_name}' {field_kind} '{field_label}' "
        f"could not resolve a dataframe column from {references}."
    )


# Resolve every configured preset without consulting Streamlit or session state.
def resolve_filtering_sections(
    config: FilteringSectionsConfig, data: pd.DataFrame
) -> Dict[str, ResolvedFilteringSection]:
    resolved_sections: Dict[str, ResolvedFilteringSection] = {}

    for section_name, section in config.sections.items():
        resolved_columns = []
        resolved_filters = []
        warnings = []

        for field_label, field in section.columns.items():
            column = _resolve_field(field, data)
            if column is None:
                warnings.append(
                    _missing_field_warning(
                        section_name, "display column", field_label, field
                    )
                )
                continue
            resolved_columns.append(ResolvedField(field_label, column))

        if not resolved_columns:
            warnings.append(
                f"FilteringSection '{section_name}' has no available display columns."
            )

        missing_filter = False
        for field_label, condition in section.filters.items():
            column = _resolve_field(condition, data)
            if column is None:
                missing_filter = True
                warnings.append(
                    _missing_field_warning(
                        section_name, "filter", field_label, condition
                    )
                )
                continue
            resolved_filters.append(ResolvedFilter(field_label, column, condition))

        resolved_sections[section_name] = ResolvedFilteringSection(
            name=section_name,
            columns=tuple(resolved_columns),
            filters=tuple(resolved_filters),
            available=bool(resolved_columns) and not missing_filter,
            warnings=tuple(warnings),
        )

    return resolved_sections


# Build the missing-safe boolean mask for one resolved condition.
def _condition_mask(data: pd.DataFrame, resolved_filter: ResolvedFilter) -> pd.Series:
    series = data[resolved_filter.column]
    condition = resolved_filter.condition
    not_missing = series.notna()

    if condition.operator == "equals":
        comparison = series.eq(condition.value).fillna(False)
        return not_missing & comparison

    if condition.operator == "in":
        return not_missing & series.isin(condition.values)

    if condition.operator == "contains":
        contains = series.astype("string").str.contains(
            condition.value, case=False, na=False, regex=False
        )
        return not_missing & contains

    if condition.operator == "range":
        numeric = pd.to_numeric(series, errors="coerce")
        range_mask = numeric.notna()
        if condition.min is not None:
            range_mask &= numeric >= condition.min
        if condition.max is not None:
            range_mask &= numeric <= condition.max
        return range_mask

    raise ValueError(f"Unsupported FilteringSection operator: {condition.operator}")


# Apply one available preset to a copy of the complete dataframe.
def apply_filtering_section(
    data: pd.DataFrame, section: ResolvedFilteringSection
) -> Optional[pd.DataFrame]:
    if not section.available:
        return None

    if any(
        resolved_filter.column not in data.columns
        for resolved_filter in section.filters
    ):
        return None

    filtered_data = data.copy()
    for resolved_filter in section.filters:
        filtered_data = filtered_data.loc[
            _condition_mask(filtered_data, resolved_filter)
        ].copy()
    return filtered_data
