"""Tests for loading data from an API into the dashboard."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd
import pytest
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
        self.sidebar.subheader = lambda *args, **kwargs: None
        self.sidebar.markdown = lambda *args, **kwargs: None
        self.sidebar.columns = lambda n: [
            _ContextStub() for _ in range(n)
        ]
        self.reset()

    def reset(self):
        self.info_calls = []
        self.warning_calls = []
        self.success_calls = []

    def info(self, message):
        self.info_calls.append(message)

    def warning(self, message):
        self.warning_calls.append(message)

    def success(self, message):
        self.success_calls.append(message)

    def error(self, message):
        raise AssertionError(f"st.error called unexpectedly: {message}")

    def stop(self):
        raise AssertionError("st.stop called unexpectedly")
    
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

from uQCme import app
from uQCme.core import loader


class DummyResponse:
    """Simple response object emulating requests.Response for tests."""

    def __init__(self, payload):
        self._payload = payload
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload

    @property
    def text(self):
        return ""

    def raise_for_status(self):
        return None


def _build_api_config(tmp_path, test_data_paths, api_url: str):
    config = {
        "app": {
            "input": {
                "data": {"api_call": api_url},
                "mapping": str(test_data_paths["mapping"]),
                "qc_rules": str(test_data_paths["qc_rules"]),
                "qc_tests": str(test_data_paths["qc_tests"]),
            }
        }
    }
    config_path = tmp_path / "config_api.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


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

    def fake_get(url, headers, timeout, verify):
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

