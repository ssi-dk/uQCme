import pandas as pd
import types
import yaml
from uQCme import app
from uQCme.core.config import UQCMeConfig


class StreamlitStub(types.ModuleType):
    """Lightweight stub of the streamlit API used in QCDashboard."""

    def __init__(self):
        super().__init__("streamlit")
        self.sidebar = types.SimpleNamespace()
        self.sidebar.container = self._sidebar_container
        self.sidebar.header = self._sidebar_header
        self.sidebar.subheader = self._sidebar_subheader
        self.sidebar.markdown = self._sidebar_markdown
        self.sidebar.button = lambda *args, **kwargs: False
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
        self.columns_calls = []
        self.info_calls = []
        self.warning_calls = []
        self.success_calls = []
        self.write_calls = []
        self.json_calls = []
        self.markdown_calls = []
        self.dataframe_calls = []
        self.data_editor_calls = []
        self.session_state = _SessionStateStub()
        self.query_params = _QueryParamsStub()
        self.form_submitted = False
        self.clicked_button = None

    def caption(self, message):
        self.events.append(f"caption:{message}")

    def form(self, *args, **kwargs):
        self.events.append("form")
        return _ContextStub()

    def form_submit_button(self, label, **kwargs):
        self.events.append(f"form_submit_button:{label}")
        return self.form_submitted

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
        self.markdown_calls.append((message, kwargs))

    def metric(self, *args, **kwargs):
        self.events.append("metric")

    def columns(self, spec, **kwargs):
        self.events.append("columns")
        self.columns_calls.append((spec, kwargs))
        column_count = spec if isinstance(spec, int) else len(spec)
        return [_ButtonContextStub(self) for _ in range(column_count)]

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

    def _sidebar_container(self):
        return _InsertedContextStub(self.events, "sidebar.container", len(self.events))

    def _sidebar_slider(self, *args, **kwargs):
        return kwargs.get("value")

    def _sidebar_selectbox(self, label, options, index=0, **kwargs):
        return options[index]

    def _sidebar_text_input(self, *args, **kwargs):
        return kwargs.get("value", "")

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
        if data.__class__.__name__ == "Styler":
            return data.data.copy()
        return data.copy()

    def expander(self, *args, **kwargs):
        self.events.append("expander")
        return _ContextStub()

    def error(self, message):
        raise AssertionError(f"st.error called unexpectedly: {message}")

    def stop(self):
        raise AssertionError("st.stop called unexpectedly")

    def rerun(self):
        raise AssertionError("st.rerun called unexpectedly")

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


class _ButtonContextStub(_ContextStub):
    def __init__(self, streamlit):
        self.streamlit = streamlit

    def button(self, label, **kwargs):
        self.streamlit.events.append(f"button:{label}")
        return self.streamlit.clicked_button == label


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


def _bare_dashboard(table_height: int = 3600, ui_styling=None):
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
            "ui_styling": ui_styling,
        }
    )
    dashboard.mapping = {}
    dashboard.report_mode = False
    dashboard.data = pd.DataFrame()
    dashboard.qc_rules = pd.DataFrame()
    return dashboard


def _dashboard_with_presets():
    dashboard = _bare_dashboard()

    dashboard.config.app.dashboard.column_presets.default = "Standard"
    dashboard.config.app.dashboard.column_presets.presets = {
        "Standard": {
            "description": "Standard QC view",
            "columns": {
                "Basic": ["Sample Name"],
            },
        },
        "Everything": {
            "description": "All columns",
            "columns": "*",
        },
    }

    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                },
            },
            "QC": {
                "QC Outcome": {
                    "data": {"mapping": "qc_outcome"},
                },
            },
        }
    }

    dashboard.data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
            }
        ]
    )

    return dashboard
