"""Tests for loading data from an API into the dashboard."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pandas as pd
import pytest
import requests
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))


class DummyPlotter:
    """Minimal QCPlotter substitute for dashboard construction."""

    def __init__(self, config):
        self.config = config


def _empty_metrics(_):
    return []


class StreamlitStub(types.ModuleType):
    """Lightweight stub of the streamlit API used in QCDashboard."""

    def __init__(self):
        super().__init__("streamlit")
        self.sidebar = types.SimpleNamespace()
        self.sidebar.container = self._sidebar_container
        self.sidebar.header = self._sidebar_header
        self.sidebar.subheader = self._sidebar_subheader
        self.sidebar.markdown = self._sidebar_markdown
        self.sidebar.button = self._sidebar_button
        self.sidebar.slider = self._sidebar_slider
        self.sidebar.selectbox = self._sidebar_selectbox
        self.sidebar.text_input = self._sidebar_text_input
        self.sidebar.columns = lambda n: [_ContextStub() for _ in range(n)]
        self.column_config = types.SimpleNamespace(
            NumberColumn=lambda *args, **kwargs: ("number", args, kwargs),
            CheckboxColumn=lambda *args, **kwargs: ("checkbox", args, kwargs),
        )
        self.reset()

    def reset(self):
        self.events = []
        self.info_calls = []
        self.warning_calls = []
        self.success_calls = []
        self.write_calls = []
        self.json_calls = []
        self.dataframe_calls = []
        self.data_editor_calls = []
        self.rerun_calls = 0
        self.button_calls = []
        self.button_values = {}
        self.slider_calls = []
        self.slider_values = {}
        self.selectbox_calls = []
        self.selectbox_values = {}
        self.text_input_calls = []
        self.text_input_values = {}
        self.data_editor_transform = None
        self.session_state = _SessionStateStub()
        self.query_params = _QueryParamsStub()

    def info(self, message):
        self.events.append("info")
        self.info_calls.append(message)

    def warning(self, message):
        self.events.append("warning")
        self.warning_calls.append(message)

    def success(self, message):
        self.events.append("success")
        self.success_calls.append(message)

    def write(self, message):
        self.events.append("write")
        self.write_calls.append(message)

    def header(self, message):
        self.events.append(f"header:{message}")

    def subheader(self, message):
        self.events.append(f"subheader:{message}")

    def markdown(self, message, **kwargs):
        self.events.append("markdown")

    def metric(self, *args, **kwargs):
        self.events.append("metric")

    def columns(self, n):
        self.events.append("columns")
        return [_ContextStub() for _ in range(n)]

    def selectbox(self, label, options, index=0, **kwargs):
        self.events.append(f"selectbox:{label}")
        return options[index]

    def checkbox(self, label, value=False, key=None):
        self.events.append(f"checkbox:{label}")
        if key and key in self.session_state:
            return self.session_state[key]
        if key:
            self.session_state[key] = value
        return value

    def pills(self, label, options, default=None, key=None, **kwargs):
        self.events.append(f"pills:{label}")
        return self._stateful_selection(default, key)

    def multiselect(self, label, options, default=None, key=None, **kwargs):
        self.events.append(f"multiselect:{label}")
        return self._stateful_selection(default, key)

    def _stateful_selection(self, default, key):
        if key and key in self.session_state:
            return self.session_state[key]
        selection = list(default or [])
        if key:
            self.session_state[key] = selection
        return selection

    def _sidebar_header(self, message):
        self.events.append(f"sidebar.header:{message}")

    def _sidebar_subheader(self, message):
        self.events.append(f"sidebar.subheader:{message}")

    def _sidebar_markdown(self, *args, **kwargs):
        self.events.append("sidebar.markdown")

    def _sidebar_button(self, label, **kwargs):
        self.events.append(f"sidebar.button:{label}")
        self.button_calls.append((label, kwargs))
        return self.button_values.get(label, False)

    def _sidebar_container(self):
        return _InsertedContextStub(self.events, "sidebar.container", len(self.events))

    def _sidebar_slider(self, *args, **kwargs):
        key = kwargs.get("key")
        self.slider_calls.append((args, kwargs))
        value = self.slider_values.get(key, kwargs.get("value"))
        if key:
            self.session_state[key] = value
        return value

    def _sidebar_selectbox(self, label, options, index=0, **kwargs):
        key = kwargs.get("key")
        self.selectbox_calls.append((label, list(options), kwargs))
        value = self.selectbox_values.get(key, options[index])
        if key:
            self.session_state[key] = value
        return value

    def _sidebar_text_input(self, *args, **kwargs):
        key = kwargs.get("key")
        self.text_input_calls.append((args, kwargs))
        value = self.text_input_values.get(key, kwargs.get("value", ""))
        if key:
            self.session_state[key] = value
        return value

    def json(self, payload):
        self.events.append("json")
        self.json_calls.append(payload)

    def dataframe(self, data, **kwargs):
        self.events.append("dataframe")
        self.dataframe_calls.append((data, kwargs))
        return None

    def data_editor(self, data, **kwargs):
        self.events.append("data_editor")
        self.data_editor_calls.append((data, kwargs))
        if hasattr(data, "data") and not hasattr(data, "columns"):
            edited_data = data.data.copy()
        else:
            edited_data = data.copy()
        if self.data_editor_transform is not None:
            return self.data_editor_transform(edited_data)
        return edited_data

    def button(self, label, **kwargs):
        self.events.append(f"button:{label}")
        self.button_calls.append((label, kwargs))
        return self.button_values.get(label, False)

    def expander(self, *args, **kwargs):
        self.events.append("expander")
        return _ContextStub()

    def error(self, message):
        raise AssertionError(f"st.error called unexpectedly: {message}")

    def stop(self):
        raise AssertionError("st.stop called unexpectedly")

    def rerun(self):
        self.events.append("rerun")
        self.rerun_calls += 1

    @property
    def runtime(self):
        return types.SimpleNamespace(exists=lambda: True)


class _ContextStub:
    """Simple context manager used by sidebar.columns stub."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None


class _InsertedContextStub(_ContextStub):
    """Context stub that preserves the visual insertion point."""

    def __init__(self, events, prefix: str, insert_index: int):
        self._events = events
        self._prefix = prefix
        self._insert_index = insert_index

    def _record(self, event: str):
        self._events.insert(self._insert_index, event)
        self._insert_index += 1

    def subheader(self, message):
        self._record(f"{self._prefix}.subheader:{message}")

    def markdown(self, *args, **kwargs):
        self._record(f"{self._prefix}.markdown")

    def columns(self, n):
        self._record(f"{self._prefix}.columns")
        return [_ContextStub() for _ in range(n)]


class _QueryParamsStub(dict):
    """Dictionary-like query params stub with Streamlit-compatible API."""

    def to_dict(self):
        return dict(self)


class _SessionStateStub(dict):
    """Dictionary with attribute access for Streamlit session state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


streamlit_stub = StreamlitStub()

# Mock streamlit.web and streamlit.web.cli
web_stub = types.ModuleType("streamlit.web")
cli_stub = types.ModuleType("streamlit.web.cli")
cli_stub.main = lambda: None
web_stub.cli = cli_stub
streamlit_stub.web = web_stub
sys.modules["streamlit.web"] = web_stub
sys.modules["streamlit.web.cli"] = cli_stub

plot_stub = types.ModuleType("uQCme.plot")
plot_stub.QCPlotter = DummyPlotter
plot_stub.get_available_metrics = _empty_metrics

sys.modules["streamlit"] = streamlit_stub
sys.modules["uQCme.plot"] = plot_stub

# We have these imports not at top-level because the code above switches modules
# with stubs as part of the testing. Therefore, modules can't be imported before
# that happens
from uQCme import app  # noqa: E402
from uQCme.core import loader  # noqa: E402
from uQCme.core.config import UQCMeConfig  # noqa: E402
from uQCme.core.filtering import (  # noqa: E402
    ResolvedField,
    ResolvedFilter,
    ResolvedFilteringSection,
)
from uQCme.core.mapping import FilteringCondition, FilteringSectionsConfig  # noqa: E402

dashboard_main = importlib.import_module("uQCme.app.main")


class DummyResponse:
    """Simple response object emulating requests.Response for tests."""

    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload

    @property
    def text(self):
        return ""

    def raise_for_status(self):
        return None


def _build_api_config(
    tmp_path,
    test_data_paths,
    api_url: str,
    api_bearer_token: str | None = None,
    api_bearer_token_env: str | None = None,
    api_headers: dict[str, str] | None = None,
    debug_api: bool = False,
):
    data_config = {"api_call": api_url}
    if api_bearer_token:
        data_config["api_bearer_token"] = api_bearer_token
    if api_bearer_token_env:
        data_config["api_bearer_token_env"] = api_bearer_token_env
    if api_headers:
        data_config["api_headers"] = api_headers

    config = {
        "app": {
            "input": {
                "data": data_config,
                "mapping": str(test_data_paths["mapping"]),
                "qc_rules": str(test_data_paths["qc_rules"]),
                "qc_tests": str(test_data_paths["qc_tests"]),
            },
            "dashboard": {"debug_api": debug_api},
        }
    }
    config_path = tmp_path / "config_api.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _build_dashboard_with_sample_action(
    tmp_path,
    test_data_paths,
    sample_action: dict,
):
    config = {
        "app": {
            "input": {
                "data": {"file": str(test_data_paths["example_run_data"])},
                "mapping": str(test_data_paths["mapping"]),
                "qc_rules": str(test_data_paths["qc_rules"]),
                "qc_tests": str(test_data_paths["qc_tests"]),
            },
            "dashboard": {"sample_api_actions": [sample_action]},
        }
    }
    config_path = tmp_path / "config_sample_action.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return app.QCDashboard(str(config_path))


def _bare_dashboard(table_height: int = 3600):
    """Construct a dashboard instance without loading files."""
    dashboard = app.QCDashboard.__new__(app.QCDashboard)
    dashboard.config = UQCMeConfig(
        app={
            "input": {
                "data": {"file": "output/qc_results.tsv"},
                "mapping": "config/mapping.yaml",
                "qc_rules": "config/QC_rules.tsv",
                "qc_tests": "config/QC_tests.tsv",
            },
            "dashboard": {"table_height": table_height},
        }
    )
    dashboard.mapping = {}
    dashboard.report_mode = False
    dashboard.data = pd.DataFrame()
    dashboard.qc_rules = pd.DataFrame()
    return dashboard


def _dashboard_state_section(name="Local group"):
    """Build a resolved preset for dashboard state wrapper tests."""
    condition = FilteringCondition(
        data={"mapping": "sample_name"}, operator="equals", value="S1"
    )
    return ResolvedFilteringSection(
        name=name,
        columns=(ResolvedField("Sample", "sample_name"),),
        filters=(ResolvedFilter("Sample", "sample_name", condition),),
        available=True,
        warnings=(),
    )


def _dashboard_filtering_config():
    # Build ordered preset definitions for sidebar composition tests.
    return FilteringSectionsConfig(
        sections={
            "Pass only": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                },
                "filters": {
                    "Outcome": {
                        "data": {"mapping": "qc_outcome"},
                        "operator": "equals",
                        "value": "PASS",
                    },
                },
            },
            "Local group": {
                "columns": {
                    "Sample": {"data": {"mapping": "sample_name"}},
                },
                "filters": {
                    "Group": {
                        "data": {"mapping": "group"},
                        "operator": "equals",
                        "value": "local",
                    },
                },
            },
        }
    )


def _dashboard_with_sidebar_filters():
    # Build a dashboard with filterable mapped columns and deterministic rows.
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "Outcome": {
                    "data": {"mapping": "qc_outcome"},
                    "report": {"filter": True},
                },
                "Group": {
                    "data": {"mapping": "group"},
                    "report": {"filter": True},
                },
            }
        }
    }
    dashboard.filtering_sections = _dashboard_filtering_config()
    dashboard.data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS", "group": "local"},
            {"sample_name": "S2", "qc_outcome": "PASS", "group": "remote"},
            {"sample_name": "S3", "qc_outcome": "FAIL", "group": "remote"},
        ]
    )
    return dashboard


def _dashboard_with_preview_preset():
    # Build a preset whose display columns intentionally omit the sample ID.
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample ID": {
                    "data": {"mapping": "sample_id"},
                    "report": {"id": True},
                },
                "Display A": {"data": {"mapping": "display_a"}},
                "Display B": {"data": {"mapping": "display_b"}},
                "Secret": {"data": {"mapping": "secret_value"}},
                "API value": {"data": {"mapping": "api_value"}},
            }
        }
    }
    dashboard.data = pd.DataFrame(
        [
            {
                "sample_id": "S1",
                "display_a": "A1",
                "display_b": "B1",
                "secret_value": "hidden-1",
                "api_value": "value-1",
            },
            {
                "sample_id": "S2",
                "display_a": "A2",
                "display_b": "B2",
                "secret_value": "hidden-2",
                "api_value": "value-2",
            },
        ],
        index=[4, 9],
    )
    dashboard._active_filtering_section = ResolvedFilteringSection(
        name="Preset",
        columns=(
            ResolvedField("Second", "display_b"),
            ResolvedField("First", "display_a"),
        ),
        filters=(),
        available=True,
        warnings=(),
    )
    return dashboard


def test_dashboard_activation_wrapper_updates_url_and_reruns():
    """Dashboard activation should use built-in query params and rerun once."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                }
            }
        }
    }
    streamlit_stub.session_state["filter_sample_name"] = "S2"

    dashboard._activate_filtering_section(_dashboard_state_section())

    assert streamlit_stub.query_params["filtering_section"] == "Local group"
    assert "filter_sample_name" not in streamlit_stub.session_state
    assert streamlit_stub.rerun_calls == 1


def test_sidebar_preset_buttons_follow_mapping_order_before_manual_filters():
    # Preset buttons should be emitted in declaration order before the header.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()

    dashboard.render_sidebar_filters()

    preset_buttons = [
        (label, kwargs)
        for label, kwargs in streamlit_stub.button_calls
        if label != "🧹 Clear View & Filters"
    ]
    assert [label for label, _ in preset_buttons] == [
        "Pass only",
        "Local group",
    ]
    button_positions = [
        streamlit_stub.events.index("sidebar.button:Pass only"),
        streamlit_stub.events.index("sidebar.button:Local group"),
    ]
    header_position = streamlit_stub.events.index("sidebar.header:🔍 Filters")
    assert button_positions[0] < button_positions[1] < header_position


def test_sidebar_active_preset_uses_primary_button_type():
    # The active preset is visually identified through Streamlit's button type.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    streamlit_stub.query_params["filtering_section"] = "Local group"

    dashboard.render_sidebar_filters()

    button_types = {
        label: kwargs.get("type")
        for label, kwargs in streamlit_stub.button_calls
        if label != "🧹 Clear View & Filters"
    }
    assert button_types == {"Pass only": "secondary", "Local group": "primary"}


def test_sidebar_preset_button_delegates_activation_and_reruns():
    # Clicking a usable preset uses the FS-03 transition helper.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    streamlit_stub.button_values["Pass only"] = True

    dashboard.render_sidebar_filters()

    assert streamlit_stub.query_params["filtering_section"] == "Pass only"
    assert streamlit_stub.rerun_calls == 1


def test_unavailable_preset_is_disabled_and_warned_once():
    # A missing filter column must not be activatable.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    dashboard.filtering_sections = FilteringSectionsConfig(
        sections={
            "Missing data": {
                "columns": {"Sample": {"data": {"mapping": "sample_name"}}},
                "filters": {
                    "Missing": {
                        "data": {"mapping": "not_loaded"},
                        "operator": "equals",
                        "value": "x",
                    }
                },
            }
        }
    )

    dashboard.render_sidebar_filters()

    preset_button = next(
        call for call in streamlit_stub.button_calls if call[0] == "Missing data"
    )
    assert preset_button[1]["disabled"] is True
    assert len(streamlit_stub.warning_calls) == 1
    assert "could not resolve" in streamlit_stub.warning_calls[0]


def test_preset_filter_runs_before_manual_sample_search_with_and_logic():
    # A manual filter further narrows the rows selected by the preset.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    streamlit_stub.query_params["filtering_section"] = "Pass only"
    streamlit_stub.text_input_values["search_sample_name"] = "S1"

    filtered_data = dashboard.render_sidebar_filters()

    assert filtered_data["sample_name"].tolist() == ["S1"]
    assert dashboard.data["sample_name"].tolist() == ["S1", "S2", "S3"]


def test_manual_widget_options_use_full_data_after_preset_filtering():
    # Manual choices remain discoverable even when the preset excludes rows.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    streamlit_stub.query_params["filtering_section"] = "Pass only"

    dashboard.render_sidebar_filters()

    outcome_call = next(
        call
        for call in streamlit_stub.selectbox_calls
        if call[2].get("key") == "filter_qc_outcome"
    )
    assert outcome_call[1] == ["All", "FAIL", "PASS"]


def test_qc_outcome_fail_option_matches_composite_failure_outcomes():
    # The semantic FAIL choice should match every failure outcome token.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    dashboard.data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS", "group": "local"},
            {
                "sample_name": "S2",
                "qc_outcome": "FAIL_CONTAMINATION",
                "group": "remote",
            },
            {
                "sample_name": "S3",
                "qc_outcome": "FAIL,FAIL_SIZE",
                "group": "remote",
            },
        ]
    )
    streamlit_stub.selectbox_values["filter_qc_outcome"] = "FAIL"

    filtered_data = dashboard.render_sidebar_filters()

    assert filtered_data["sample_name"].tolist() == ["S2", "S3"]
    outcome_call = next(
        call
        for call in streamlit_stub.selectbox_calls
        if call[2].get("key") == "filter_qc_outcome"
    )
    assert "FAIL" in outcome_call[1]


def test_missing_filtering_sections_preserves_existing_manual_pipeline():
    # Without the optional config, no preset UI or preset mask is introduced.
    streamlit_stub.reset()
    dashboard = _dashboard_with_sidebar_filters()
    dashboard.filtering_sections = FilteringSectionsConfig()
    streamlit_stub.text_input_values["search_sample_name"] = "S3"

    filtered_data = dashboard.render_sidebar_filters()

    assert [
        label
        for label, _ in streamlit_stub.button_calls
        if label != "🧹 Clear View & Filters"
    ] == []
    assert filtered_data["sample_name"].tolist() == ["S3"]


def test_active_preset_limits_preview_to_ordered_display_columns():
    # Preset display columns are the maximum table schema in configured order.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()

    dashboard.render_data_tab(dashboard.data)

    rendered_data, kwargs = streamlit_stub.data_editor_calls[0]
    rendered_frame = (
        rendered_data.data if hasattr(rendered_data, "data") else rendered_data
    )
    assert list(rendered_frame.columns) == ["Select", "display_b", "display_a"]
    assert kwargs["column_order"] == ["Select", "display_b", "display_a"]
    assert "secret_value" not in rendered_frame.columns
    assert "api_value" not in rendered_frame.columns


def test_active_preset_bypasses_section_visibility_controls():
    # Preset-owned visibility must not render the legacy section selector.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()

    dashboard.render_data_tab(dashboard.data)

    assert "subheader:Section Visibility" not in streamlit_stub.events
    assert "pills:Visible sections" not in streamlit_stub.events
    assert "data_preview_visible_sections" not in streamlit_stub.session_state


def test_selection_maps_hidden_id_back_to_full_row_by_index():
    # Selection uses the stable source index even when the ID is not displayed.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()

    def check_first_row(edited_data):
        edited_data.loc[4, "Select"] = True
        return edited_data

    streamlit_stub.data_editor_transform = check_first_row
    dashboard.render_data_tab(dashboard.data)

    assert streamlit_stub.session_state["selected_samples"] == {"S1"}


def test_selection_ignores_editor_rows_not_in_source_dataframe():
    # An unexpected editor index must not select an unrelated source row.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()

    def add_unknown_selected_row(edited_data):
        edited_data.loc[999, "Select"] = True
        return edited_data

    streamlit_stub.data_editor_transform = add_unknown_selected_row
    dashboard.render_data_tab(dashboard.data)

    assert streamlit_stub.session_state["selected_samples"] == set()


def test_sample_actions_receive_full_filtered_rows_when_columns_are_hidden():
    # Downstream actions retain API values and IDs omitted from the preview.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()
    captured = {}

    def capture_rows(filtered_data):
        captured["data"] = filtered_data

    dashboard.render_sample_api_actions = capture_rows
    dashboard.render_data_tab(dashboard.data)

    assert list(captured["data"].columns) == list(dashboard.data.columns)
    pd.testing.assert_frame_equal(captured["data"], dashboard.data)


def test_selected_rows_retain_hidden_api_values_for_downstream_actions():
    # Selection lookup uses the full filtered dataframe, not preview columns.
    streamlit_stub.reset()
    dashboard = _dashboard_with_preview_preset()
    streamlit_stub.session_state["selected_samples"] = {"S2"}

    selected_rows = dashboard._get_selected_sample_rows(dashboard.data)

    assert selected_rows["sample_id"].tolist() == ["S2"]
    assert selected_rows["api_value"].tolist() == ["value-2"]


def test_dashboard_clear_view_wrapper_preserves_unrelated_url_state():
    """Dashboard reset should clear feature state and preserve other URL values."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    streamlit_stub.query_params.update(
        {"filtering_section": "Local group", "debug": "true"}
    )
    streamlit_stub.session_state.update(
        {
            "search_sample_name": "S1",
            "selected_samples": {"S1"},
            "data_preview_table": {"edited": True},
            "data_preview_visible_sections": ["Basic"],
        }
    )

    dashboard._clear_view_and_filters()

    assert streamlit_stub.query_params == {"debug": "true"}
    assert streamlit_stub.session_state == {}
    assert streamlit_stub.rerun_calls == 1


def test_load_data_parses_filtering_sections_after_loading_mapping(
    monkeypatch, tmp_path, test_data_paths
):
    """Dashboard mapping loading should initialize typed FilteringSections."""
    streamlit_stub.reset()
    mapping_path = tmp_path / "mapping_with_filtering_sections.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "Sections": {
                    "Basic": {
                        "Name": {
                            "data": {"mapping": "sample_name"},
                            "report": {"id": True},
                        },
                        "QC outcome": {
                            "data": {"mapping": "qc_outcome"},
                        },
                    }
                },
                "FilteringSections": {
                    "Local group": {
                        "columns": {
                            "Sample": {"data": {"mapping": "sample_name"}},
                        },
                        "filters": {
                            "Status": {
                                "data": {"mapping": "qc_outcome"},
                                "operator": "equals",
                                "value": "PASS",
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config_filtering_sections.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "app": {
                    "input": {
                        "data": {"file": "unused.tsv"},
                        "mapping": str(mapping_path),
                        "qc_rules": str(test_data_paths["qc_rules"]),
                        "qc_tests": str(test_data_paths["qc_tests"]),
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    dashboard = app.QCDashboard(str(config_path))
    monkeypatch.setattr(
        dashboard,
        "_load_data_with_optional_api_debug",
        lambda _data_config: pd.DataFrame(),
    )

    dashboard.load_data()

    assert list(dashboard.filtering_sections.sections) == ["Local group"]


def test_load_data_from_api(monkeypatch, tmp_path, test_data_paths):
    """QCDashboard.load_data should populate data from an API endpoint."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(tmp_path, test_data_paths, expected_url)
    dashboard = app.QCDashboard(str(config_path))

    api_payload = [
        {
            "sample_name": "S1",
            "qc_outcome": "PASS",
            "species": "E. coli",
            "provided_species": "E. coli",
        },
        {
            "sample_name": "S2",
            "qc_outcome": "FAIL",
            "species": "Listeria",
            "provided_species": "Listeria",
        },
    ]

    response = DummyResponse(api_payload)

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        assert headers == {"accept": "application/json"}
        assert timeout == 30
        assert verify is True
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()

    expected_df = pd.DataFrame(api_payload)
    pd.testing.assert_frame_equal(
        dashboard.data.sort_index(axis=1), expected_df.sort_index(axis=1)
    )


def test_load_data_from_api_allows_missing_sample_name_when_not_required(
    monkeypatch, tmp_path, test_data_paths
):
    """API data without sample_name should load when mapping does not require it."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    mapping_path = tmp_path / "mapping_without_sample_name.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "Sections": {
                    "QC_metrics": {
                        "QC outcome": {
                            "data": {"mapping": "qc_outcome"},
                            "report": {"filter": True},
                        },
                        "Provided Species": {
                            "data": {"mapping": "species"},
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    config = {
        "app": {
            "input": {
                "data": {"api_call": expected_url},
                "mapping": str(mapping_path),
                "qc_rules": str(test_data_paths["qc_rules"]),
                "qc_tests": str(test_data_paths["qc_tests"]),
            }
        }
    }
    config_path = tmp_path / "config_api_without_sample_name.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    dashboard = app.QCDashboard(str(config_path))

    api_payload = [
        {
            "qc_outcome": "PASS",
            "species": "E. coli",
            "provided_species": "E. coli",
        },
        {
            "qc_outcome": "FAIL",
            "species": "Listeria",
            "provided_species": "Listeria",
        },
    ]

    response = DummyResponse(api_payload)

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        assert headers == {"accept": "application/json"}
        assert timeout == 30
        assert verify is True
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()

    expected_df = pd.DataFrame(api_payload)
    pd.testing.assert_frame_equal(
        dashboard.data.sort_index(axis=1), expected_df.sort_index(axis=1)
    )


def test_load_data_from_api_with_bearer_token(monkeypatch, tmp_path, test_data_paths):
    """API data loading should include bearer token from config."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        api_bearer_token="token-from-config",
    )
    dashboard = app.QCDashboard(str(config_path))

    response = DummyResponse(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
                "species": "E. coli",
                "provided_species": "E. coli",
            }
        ]
    )

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        assert headers == {
            "accept": "application/json",
            "Authorization": "Bearer token-from-config",
        }
        assert timeout == 30
        assert verify is True
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()


def test_load_data_from_api_with_bearer_token_env(
    monkeypatch, tmp_path, test_data_paths
):
    """API data loading should include bearer token from configured env var."""
    streamlit_stub.reset()
    monkeypatch.setenv("UQCME_TEST_API_TOKEN", "token-from-env")

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        api_bearer_token_env="UQCME_TEST_API_TOKEN",
    )
    dashboard = app.QCDashboard(str(config_path))

    response = DummyResponse(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
                "species": "E. coli",
                "provided_species": "E. coli",
            }
        ]
    )

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        assert headers == {
            "accept": "application/json",
            "Authorization": "Bearer token-from-env",
        }
        assert timeout == 30
        assert verify is True
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()


def test_load_data_from_api_debug_captures_payload(
    monkeypatch, tmp_path, test_data_paths
):
    """Debug mode should retain API payload preview for browser inspection."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        debug_api=True,
    )
    dashboard = app.QCDashboard(str(config_path))

    api_payload = [
        {
            "sample_name": "S1",
            "qc_outcome": "PASS",
            "species": "E. coli",
            "provided_species": "E. coli",
        },
        {
            "sample_name": "S2",
            "qc_outcome": "FAIL",
            "species": "Listeria",
            "provided_species": "Listeria",
        },
    ]

    response = DummyResponse(api_payload)

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()

    assert dashboard.api_debug_info is not None
    assert dashboard.api_debug_info["resolved_url"] == expected_url
    assert dashboard.api_debug_info["payload_preview"] == api_payload
    assert dashboard.api_debug_info["row_count"] == 2
    assert "sample_name" in dashboard.api_debug_info["columns"]


def test_render_api_debug_panel_shows_payload(monkeypatch, tmp_path, test_data_paths):
    """Debug panel should render payload preview and table preview."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        debug_api=True,
    )
    dashboard = app.QCDashboard(str(config_path))
    dashboard.api_debug_info = {
        "resolved_url": expected_url,
        "status_code": 200,
        "payload_type": "list",
        "payload_preview": [{"sample_name": "S1"}],
        "row_count": 1,
        "columns": ["sample_name"],
        "normalized_columns": ["sample_name", "qc_outcome"],
    }
    dashboard.data = pd.DataFrame([{"sample_name": "S1", "qc_outcome": "PASS"}])

    dashboard._render_api_debug_panel()

    assert streamlit_stub.json_calls == [[{"sample_name": "S1"}]]
    assert len(streamlit_stub.dataframe_calls) == 1


def test_styled_dataframe_uses_configured_table_height():
    """The main sample table should cap height at the configured maximum."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(table_height=4200)
    data = pd.DataFrame(
        [{"sample_name": f"S{i}", "qc_outcome": "PASS"} for i in range(200)]
    )

    dashboard._render_styled_dataframe(
        data,
        ["sample_name", "qc_outcome"],
        "data_preview_table",
    )

    assert len(streamlit_stub.data_editor_calls) == 1
    _, kwargs = streamlit_stub.data_editor_calls[0]
    assert kwargs["height"] == 4200


def test_styled_dataframe_shrinks_when_rows_are_below_configured_height():
    """The sample table should not leave empty space for small datasets."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(table_height=4200)
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
            {"sample_name": "S2", "qc_outcome": "FAIL"},
        ]
    )

    dashboard._render_styled_dataframe(
        data,
        ["sample_name", "qc_outcome"],
        "data_preview_table",
    )

    assert len(streamlit_stub.data_editor_calls) == 1
    _, kwargs = streamlit_stub.data_editor_calls[0]
    assert kwargs["height"] == 114


def test_explicit_other_section_mappings_are_preserved_with_unmapped_columns():
    """Explicit Other mappings should keep descriptions and section ordering."""
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Other": {
                "Contigs Path": {
                    "data": {"mapping": "shovil_contigs_path"},
                    "report": {"description": "Path to assembled contigs."},
                },
                "unmapped": True,
            }
        }
    }
    data = pd.DataFrame(
        [
            {
                "shovil_contigs_path": "/tmp/contigs.fa",
                "extra_column": "extra",
            }
        ]
    )

    sections = dashboard._get_columns_by_section(data)

    assert [col["column"] for col in sections["Other"]] == [
        "shovil_contigs_path",
        "extra_column",
    ]
    assert (
        dashboard._get_column_description("shovil_contigs_path")
        == "Path to assembled contigs."
    )


def test_data_tab_renders_section_visibility_below_table():
    """Section visibility controls should render after the main table."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(table_height=4200)
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
            {"sample_name": "S2", "qc_outcome": "FAIL"},
        ]
    )
    dashboard.data = data

    dashboard.render_data_tab(data)

    assert "data_editor" in streamlit_stub.events
    assert "subheader:Section Visibility" in streamlit_stub.events
    assert "pills:Visible sections" in streamlit_stub.events
    assert streamlit_stub.events.index("data_editor") < streamlit_stub.events.index(
        "subheader:Section Visibility"
    )
    assert streamlit_stub.events.index(
        "subheader:Section Visibility"
    ) < streamlit_stub.events.index("pills:Visible sections")


def test_section_visibility_uses_compact_stateful_selection():
    """Selected sections should be read from one compact Streamlit widget."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {"data": {"mapping": "sample_name"}},
            },
            "QC": {
                "QC Outcome": {"data": {"mapping": "qc_outcome"}},
            },
        }
    }
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
        ]
    )
    dashboard.data = data
    streamlit_stub.session_state["data_preview_visible_sections"] = ["Basic"]

    dashboard.render_data_tab(data)

    rendered_data, _ = streamlit_stub.data_editor_calls[0]
    assert list(rendered_data.columns) == ["sample_name"]
    assert "pills:Visible sections" in streamlit_stub.events
    assert not any(event.startswith("checkbox:") for event in streamlit_stub.events)


def test_section_visibility_empty_selection_does_not_show_all_columns():
    """Deselecting all sections should not fall back to showing everything."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {"data": {"mapping": "sample_name"}},
            },
            "QC": {
                "QC Outcome": {"data": {"mapping": "qc_outcome"}},
            },
        }
    }
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
        ]
    )
    dashboard.data = data
    streamlit_stub.session_state["data_preview_visible_sections"] = []

    dashboard.render_data_tab(data)

    rendered_data, _ = streamlit_stub.data_editor_calls[0]
    assert list(rendered_data.columns) == []


def test_sidebar_summary_stays_at_top_of_left_panel():
    """Summary metrics should render in the sidebar above filter controls."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
            {"sample_name": "S2", "qc_outcome": "FAIL"},
        ]
    )
    dashboard.data = data

    dashboard.render_sidebar_filters()

    summary_event = "sidebar.container.subheader:📊 Summary"
    filters_event = "sidebar.header:🔍 Filters"
    assert summary_event in streamlit_stub.events
    assert filters_event in streamlit_stub.events
    assert "subheader:📊 Summary" not in streamlit_stub.events
    assert streamlit_stub.events.index(summary_event) < streamlit_stub.events.index(
        filters_event
    )


def test_filterable_fields_deduplicates_reused_data_columns():
    """Duplicate mapped columns should not create duplicate Streamlit keys."""
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "uQCme": {
                "rMLST Match": {
                    "data": {"mapping": "rMLST_match"},
                    "report": {"filter": True},
                },
            },
            "QC_metrics": {
                "Expected species": {
                    "data": {"mapping": "rMLST_match"},
                    "report": {"filter": True},
                },
                "GC": {
                    "data": {"mapping": "Quast_GC_Pct"},
                    "report": {"filter": True},
                },
            },
        }
    }
    data = pd.DataFrame(
        [
            {"rMLST_match": "E. coli", "Quast_GC_Pct": 50.1},
            {"rMLST_match": "S. aureus", "Quast_GC_Pct": 32.9},
        ]
    )

    fields = dashboard._get_filterable_fields(data)

    assert [field["column"] for field in fields] == [
        "rMLST_match",
        "Quast_GC_Pct",
    ]
    assert fields[0]["field_name"] == "rMLST Match"


def test_sample_details_renders_numeric_string_quality_metrics():
    """Sample details should show plottable and categorical metric values."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "QC Outcome": {"data": {"mapping": "qc_outcome"}},
                "QC Label": {
                    "data": {"mapping": "qc_label"},
                    "report": {"quality_metric": True},
                },
            },
            "Read_QC": {
                "Coverage": {
                    "data": {"mapping": "coverage_x"},
                    "QC": {"mapping": "Coverage"},
                    "report": {"filter": True},
                },
                "Number of genomes": {
                    "data": {"mapping": "number_of_genomes"},
                    "QC": {"mapping": "number_of_genomes"},
                },
            },
        }
    }
    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
                "coverage_x": "45.5",
                "number_of_genomes": "2",
                "qc_label": "good",
                "RunID": "12345",
            }
        ]
    )
    dashboard.data = data

    dashboard.render_sample_details_tab(data)

    assert "**Coverage:** 45.5" in streamlit_stub.write_calls
    assert "**Number of genomes:** 2" in streamlit_stub.write_calls
    assert "**QC Label:** good" in streamlit_stub.write_calls
    assert "**RunID:** 12,345" not in streamlit_stub.write_calls


def test_quality_metrics_tab_lists_non_plottable_catalog_entries():
    """Non-plottable quality metrics should be listed with reasons."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Read_QC": {
                "Categorical Metric": {
                    "data": {"mapping": "categorical_metric"},
                    "QC": {"mapping": "CategoricalField"},
                },
                "Empty Metric": {
                    "data": {"mapping": "empty_metric"},
                    "QC": {"mapping": "EmptyField"},
                },
                "Missing Metric": {
                    "data": {"mapping": "missing_metric"},
                    "QC": {"mapping": "MissingField"},
                },
            }
        }
    }
    dashboard.qc_rules = pd.DataFrame(
        [
            {"field": "CategoricalField"},
            {"field": "EmptyField"},
            {"field": "MissingField"},
        ]
    )
    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "categorical_metric": "high",
                "empty_metric": None,
            }
        ]
    )

    dashboard.render_quality_metrics_tab(data)

    assert "Quality metrics omitted from plots" in streamlit_stub.info_calls
    assert (
        "No plottable quality metrics available for visualization."
        in streamlit_stub.warning_calls
    )
    assert len(streamlit_stub.dataframe_calls) == 1
    omitted_table, _ = streamlit_stub.dataframe_calls[0]
    reasons = dict(zip(omitted_table["Metric"], omitted_table["Reason"]))
    assert reasons == {
        "Categorical Metric": "non-numeric/categorical",
        "Empty Metric": "all values empty",
        "Missing Metric": "missing column",
    }


def test_url_debug_param_enables_api_debug(tmp_path, test_data_paths):
    """URL debug query param should override config and enable debug."""
    streamlit_stub.reset()
    streamlit_stub.query_params["debug"] = "TRUE"

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        debug_api=False,
    )
    dashboard = app.QCDashboard(str(config_path))

    assert dashboard._is_api_debug_enabled() is True


def test_url_debug_param_disables_api_debug(tmp_path, test_data_paths):
    """URL debug query param should override config and disable debug."""
    streamlit_stub.reset()
    streamlit_stub.query_params["debug"] = "FALSE"

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        debug_api=True,
    )
    dashboard = app.QCDashboard(str(config_path))

    assert dashboard._is_api_debug_enabled() is False


def test_trigger_sample_api_action_with_bearer_token(
    monkeypatch, tmp_path, test_data_paths
):
    """Sample action requests should include bearer token from config."""
    streamlit_stub.reset()
    dashboard = _build_dashboard_with_sample_action(
        tmp_path,
        test_data_paths,
        {
            "label": "Notify",
            "api_call": "https://example.test/api/action",
            "value_field": "sample_name",
            "api_bearer_token": "action-token",
            "headers": {"X-Trace-Id": "trace-123"},
        },
    )
    action = dashboard.config.app.dashboard.sample_api_actions[0]
    selected_rows = pd.DataFrame(
        [
            {"sample_name": "S1", "sample_id": "ID-1"},
            {"sample_name": "S2", "sample_id": "ID-2"},
        ]
    )
    response = DummyResponse({"ok": True})

    def fake_request(**kwargs):
        assert kwargs["method"] == "POST"
        assert kwargs["url"] == "https://example.test/api/action"
        assert kwargs["timeout"] == 30
        assert kwargs["headers"] == {
            "X-Trace-Id": "trace-123",
            "Authorization": "Bearer action-token",
        }
        assert kwargs["json"] == {"sample_name": ["S1", "S2"]}
        return response

    monkeypatch.setattr(dashboard_main.requests, "request", fake_request)

    result = dashboard._trigger_sample_api_action(action, selected_rows, "sample_id")

    assert result is response


def test_trigger_sample_api_action_with_bearer_token_env(
    monkeypatch, tmp_path, test_data_paths
):
    """Sample action requests should include bearer token from env var."""
    streamlit_stub.reset()
    monkeypatch.setenv("UQCME_ACTION_TOKEN", "env-action-token")
    dashboard = _build_dashboard_with_sample_action(
        tmp_path,
        test_data_paths,
        {
            "label": "Notify",
            "api_call": "https://example.test/api/action",
            "value_field": "sample_name",
            "api_bearer_token_env": "UQCME_ACTION_TOKEN",
            "send_as_list": False,
        },
    )
    action = dashboard.config.app.dashboard.sample_api_actions[0]
    selected_rows = pd.DataFrame(
        [
            {"sample_name": "S1", "sample_id": "ID-1"},
        ]
    )
    response = DummyResponse({"ok": True})

    def fake_request(**kwargs):
        assert kwargs["headers"] == {
            "Authorization": "Bearer env-action-token",
        }
        assert kwargs["json"] == {"sample_name": "S1"}
        return response

    monkeypatch.setattr(dashboard_main.requests, "request", fake_request)

    result = dashboard._trigger_sample_api_action(action, selected_rows, "sample_id")

    assert result is response


def test_load_data_from_api_with_custom_headers(monkeypatch, tmp_path, test_data_paths):
    """X-Project-Id header should be converted to project_id query param."""
    streamlit_stub.reset()

    expected_url = "https://example.test/api/run-data"
    config_path = _build_api_config(
        tmp_path,
        test_data_paths,
        expected_url,
        api_headers={
            "X-Project-Id": "project-123",
            "X-Trace-Id": "trace-abc",
        },
    )
    dashboard = app.QCDashboard(str(config_path))

    response = DummyResponse(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
                "species": "E. coli",
                "provided_species": "E. coli",
            }
        ]
    )

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == f"{expected_url}?project_id=project-123"
        assert headers == {
            "accept": "application/json",
            "X-Trace-Id": "trace-abc",
        }
        assert timeout == 30
        assert verify is True
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    dashboard.load_data()


def test_load_data_from_api_retries_with_session_cookie(monkeypatch):
    """401 NOT_AUTHENTICATED should retry using viewer_session cookie."""
    expected_url = "https://example.test/api/run-data"
    payload = [
        {
            "sample_name": "S1",
            "qc_outcome": "PASS",
            "species": "E. coli",
            "provided_species": "E. coli",
        }
    ]
    call_count = {"value": 0}

    class UnauthorizedResponse:
        status_code = 401
        text = '{"detail":"NOT_AUTHENTICATED"}'
        url = expected_url

        def json(self):
            return {"detail": "NOT_AUTHENTICATED"}

        def raise_for_status(self):
            raise requests.exceptions.HTTPError(
                "401 Client Error: Unauthorized", response=self
            )

    response = DummyResponse(payload)

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        call_count["value"] += 1

        if call_count["value"] == 1:
            assert headers.get("Authorization") == "Bearer token-from-config"
            assert cookies is None
            return UnauthorizedResponse()

        assert "Authorization" not in headers
        assert cookies == {"viewer_session": "token-from-config"}
        return response

    monkeypatch.setattr(loader.requests, "get", fake_get)

    df = loader.load_data_from_api(expected_url, bearer_token="token-from-config")

    assert call_count["value"] == 2
    expected_df = pd.DataFrame(payload)
    pd.testing.assert_frame_equal(df.sort_index(axis=1), expected_df.sort_index(axis=1))


def test_load_data_from_api_http_error_surfaces_detail(monkeypatch):
    """HTTP errors should include API 'detail' from JSON response body."""
    detail = "No Bifrost results found for the resolved sample selection"
    expected_url = "https://example.test/api/run-data"

    class ErrorResponse:
        status_code = 404
        text = '{"detail":"No Bifrost results found for the resolved sample selection"}'

        def raise_for_status(self):
            raise requests.exceptions.HTTPError(
                "404 Client Error: Bad Request", response=self
            )

        def json(self):
            return {"detail": detail}

    def fake_get(url, headers, timeout, verify, cookies=None):
        assert url == expected_url
        return ErrorResponse()

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(loader.DataLoadError) as exc_info:
        loader.load_data_from_api(expected_url)

    message = str(exc_info.value)
    assert "HTTP 404" in message
    assert expected_url in message
    assert detail in message
