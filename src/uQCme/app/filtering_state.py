"""Streamlit-independent state transitions for dashboard presets."""

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Optional

from uQCme.core.filtering import ResolvedFilteringSection


FILTERING_SECTION_QUERY_PARAM = "filtering_section"
_MANUAL_WIDGET_PREFIXES = ("range_", "filter_", "search_")
_RESET_STATE_KEYS = {
    "selected_samples",
    "data_preview_table",
    "data_preview_visible_sections",
    "filters_reset",
}


# Represent the active preset lookup and any warning for the dashboard caller.
@dataclass(frozen=True)
class ActiveFilteringSection:
    key: Optional[str]
    section: Optional[ResolvedFilteringSection]
    warning: Optional[str]


# Read one decoded query parameter value without normalizing its identifier.
def _query_value(query_params: Mapping[str, Any]) -> Optional[str]:
    value = query_params.get(FILTERING_SECTION_QUERY_PARAM)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if value is None:
        return None
    value = str(value)
    return value or None


# Resolve the exact URL preset key against the loaded runtime presets.
def resolve_active_filtering_section(
    query_params: Mapping[str, Any],
    sections: Mapping[str, ResolvedFilteringSection],
) -> ActiveFilteringSection:
    key = _query_value(query_params)
    if key is None:
        return ActiveFilteringSection(None, None, None)

    section = sections.get(key)
    if section is None:
        return ActiveFilteringSection(
            key,
            None,
            f"Unknown FilteringSection '{key}'; showing the normal view.",
        )

    if not section.available:
        details = " ".join(section.warnings)
        warning = f"FilteringSection '{key}' is unavailable; showing the normal view."
        if details:
            warning = f"{warning} {details}"
        return ActiveFilteringSection(key, None, warning)

    return ActiveFilteringSection(key, section, None)


# Remove manual widget keys controlled by one preset before activating it.
def _clear_overlapping_widget_state(
    session_state: MutableMapping[str, Any],
    section: ResolvedFilteringSection,
    id_column: Optional[str],
) -> None:
    controlled_columns = {resolved.column for resolved in section.filters}
    for column in controlled_columns:
        for prefix in _MANUAL_WIDGET_PREFIXES:
            session_state.pop(f"{prefix}{column}", None)

    if id_column and id_column in controlled_columns:
        session_state.pop("search_sample_name", None)


# Replace the active URL key while preserving unrelated URL and session state.
def activate_filtering_section(
    query_params: MutableMapping[str, Any],
    session_state: MutableMapping[str, Any],
    section: ResolvedFilteringSection,
    id_column: Optional[str],
) -> None:
    _clear_overlapping_widget_state(session_state, section, id_column)
    query_params[FILTERING_SECTION_QUERY_PARAM] = section.name


# Remove all feature-owned URL and session state for the full reset action.
def clear_filtering_section_state(
    query_params: MutableMapping[str, Any],
    session_state: MutableMapping[str, Any],
) -> None:
    query_params.pop(FILTERING_SECTION_QUERY_PARAM, None)

    for key in list(session_state):
        if key in _RESET_STATE_KEYS or key.startswith(_MANUAL_WIDGET_PREFIXES):
            session_state.pop(key, None)
