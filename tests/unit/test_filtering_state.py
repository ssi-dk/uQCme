"""Tests for FilteringSection URL and session-state transitions."""

import sys
from pathlib import Path

import pytest

# Add src to path for the repository's source-layout test convention.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.app.filtering_state import (
    activate_filtering_section,
    clear_filtering_section_state,
    resolve_active_filtering_section,
)
from uQCme.core.filtering import (
    ResolvedField,
    ResolvedFilter,
    ResolvedFilteringSection,
)
from uQCme.core.mapping import FilteringCondition


def _resolved_section(name="Local group", available=True):
    """Build a resolved section with two controlled filter columns."""
    condition = FilteringCondition(
        data={"mapping": "sample_name"}, operator="equals", value="S1"
    )
    group_condition = FilteringCondition(
        data={"mapping": "group"}, operator="equals", value="local"
    )
    return ResolvedFilteringSection(
        name=name,
        columns=(ResolvedField("Sample", "sample_name"),),
        filters=(
            ResolvedFilter("Sample", "sample_name", condition),
            ResolvedFilter("Group", "group", group_condition),
        ),
        available=available,
        warnings=("missing filter",) if not available else (),
    )


def test_known_url_key_resolves_active_section_with_special_name():
    """Exact decoded query keys, including spaces, select the preset."""
    section = _resolved_section("Local group / β")

    active = resolve_active_filtering_section(
        {"filtering_section": "Local group / β"}, {section.name: section}
    )

    assert active.key == "Local group / β"
    assert active.section is section
    assert active.warning is None


def test_same_url_key_restores_preset_in_a_fresh_state():
    """A new state object with the same URL reproduces the active preset."""
    section = _resolved_section()
    sections = {section.name: section}

    first = resolve_active_filtering_section(
        {"filtering_section": "Local group"}, sections
    )
    second = resolve_active_filtering_section(
        {"filtering_section": "Local group"}, sections
    )

    assert first.section is section
    assert second.section is section


def test_unknown_url_key_returns_normal_view_warning():
    """Unknown identifiers never select a guessed or normalized preset."""
    active = resolve_active_filtering_section(
        {"filtering_section": "local-group"}, {"Local group": _resolved_section()}
    )

    assert active.key == "local-group"
    assert active.section is None
    assert active.warning == (
        "Unknown FilteringSection 'local-group'; showing the normal view."
    )


def test_unavailable_url_key_returns_normal_view_warning():
    """A known but unavailable preset cannot be activated from its URL."""
    section = _resolved_section(available=False)

    active = resolve_active_filtering_section(
        {"filtering_section": section.name}, {section.name: section}
    )

    assert active.section is None
    assert "FilteringSection 'Local group' is unavailable" in active.warning
    assert "missing filter" in active.warning


def test_missing_or_empty_url_key_has_no_active_section_or_warning():
    """Normal views remain silent when no preset URL parameter is present."""
    sections = {"Local group": _resolved_section()}

    assert resolve_active_filtering_section({}, sections).section is None
    assert (
        resolve_active_filtering_section({"filtering_section": ""}, sections).warning
        is None
    )


def test_activation_replaces_url_and_clears_only_controlled_widget_keys():
    """Activation removes overlapping manual controls but preserves other state."""
    query_params = {
        "filtering_section": "Old view",
        "debug": "true",
        "project_id": "project-1",
    }
    session_state = {
        "range_sample_name": (1, 2),
        "filter_sample_name": "S2",
        "search_sample_name": "S2",
        "range_group": (1, 2),
        "filter_unrelated": "keep",
        "selected_samples": {"S2"},
    }

    activate_filtering_section(
        query_params,
        session_state,
        _resolved_section(),
        id_column="sample_name",
    )

    assert query_params == {
        "filtering_section": "Local group",
        "debug": "true",
        "project_id": "project-1",
    }
    assert "range_sample_name" not in session_state
    assert "filter_sample_name" not in session_state
    assert "search_sample_name" not in session_state
    assert "range_group" not in session_state
    assert session_state["filter_unrelated"] == "keep"
    assert session_state["selected_samples"] == {"S2"}


def test_activation_does_not_clear_sample_search_for_uncontrolled_id():
    """The sample-name widget is preserved when the preset does not control ID."""
    section = ResolvedFilteringSection(
        name="Status view",
        columns=(ResolvedField("Status", "status"),),
        filters=(
            ResolvedFilter(
                "Status",
                "status",
                FilteringCondition(
                    data={"mapping": "status"},
                    operator="equals",
                    value="PASS",
                ),
            ),
        ),
        available=True,
        warnings=(),
    )
    session_state = {"search_sample_name": "S1"}

    activate_filtering_section({}, session_state, section, id_column="sample_name")

    assert session_state["search_sample_name"] == "S1"


def test_switching_presets_replaces_only_filtering_section_url_value():
    """Activating a second preset replaces the first URL identifier."""
    query_params = {"filtering_section": "First", "report_mode": "1"}

    activate_filtering_section(
        query_params, {}, _resolved_section("Second"), id_column=None
    )

    assert query_params == {"filtering_section": "Second", "report_mode": "1"}


def test_clear_removes_feature_state_but_preserves_unrelated_values():
    """Full reset clears URL, widgets, selections, editor, and visibility state."""
    query_params = {
        "filtering_section": "Local group",
        "debug": "true",
        "project_id": "project-1",
    }
    session_state = {
        "range_group": (1, 2),
        "filter_group": "local",
        "search_group": "local",
        "search_sample_name": "S1",
        "selected_samples": {"S1"},
        "data_preview_table": {"edited": True},
        "data_preview_visible_sections": ["Basic"],
        "filters_reset": True,
        "unrelated_state": "keep",
    }

    clear_filtering_section_state(query_params, session_state)

    assert query_params == {"debug": "true", "project_id": "project-1"}
    assert session_state == {"unrelated_state": "keep"}


@pytest.mark.parametrize("key", ["range_group", "filter_group", "search_group"])
def test_clear_removes_all_manual_widget_prefixes(key):
    """Reset owns every supported manual widget key prefix."""
    session_state = {key: "value"}

    clear_filtering_section_state({}, session_state)

    assert session_state == {}
