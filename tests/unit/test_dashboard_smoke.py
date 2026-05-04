"""Tests for the dashboard smoke CLI helper."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.app import smoke


@pytest.mark.dashboard_smoke
def test_smoke_parser_documents_runtime_options():
    """The smoke helper should expose the options deployment commands need."""
    help_text = smoke.build_parser().format_help()

    assert "--dashboard-command" in help_text
    assert "--config" in help_text
    assert "--host" in help_text
    assert "--probe-host" in help_text
    assert "--port" in help_text
    assert "--timeout-seconds" in help_text


@pytest.mark.dashboard_smoke
def test_dashboard_command_passes_streamlit_server_flags():
    """The smoke helper should launch through uqcme-dashboard."""
    args = smoke.build_parser().parse_args([
        "--config",
        "config/config.yaml",
        "--host",
        "0.0.0.0",
        "--port",
        "49105",
    ])

    command = smoke.dashboard_command(args)

    assert command[:3] == ["uqcme-dashboard", "--config", "config/config.yaml"]
    assert "--server.headless=true" in command
    assert "--server.address=0.0.0.0" in command
    assert "--server.port=49105" in command


@pytest.mark.dashboard_smoke
def test_probe_host_defaults_to_loopback_when_binding_all_interfaces():
    """0.0.0.0 is a bind address, not the address we should probe."""
    args = smoke.build_parser().parse_args([
        "--host",
        "0.0.0.0",
        "--port",
        "49105",
        "--path",
        "healthz",
    ])

    assert smoke.probe_url(args) == "http://127.0.0.1:49105/healthz"
