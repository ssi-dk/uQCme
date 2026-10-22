import importlib
import json
from pathlib import Path

import pytest

from tests.support.dashboard import _bare_dashboard
from uQCme import __version__
from uQCme.core.config import DataInput
from uQCme.core.identity import configuration_identity, identity_label, runtime_identity


# Identity must detect relevant changes without depending on API secrets or data locations.
def test_identity_projection_is_stable_private_and_changes_with_settings(tmp_path):
    dashboard = _bare_dashboard()
    config = dashboard.config
    for key in ("mapping", "qc_rules", "qc_tests"):
        path = tmp_path / key
        path.write_text("synthetic reference")
        setattr(config.app.input, key, str(path))
    config.app.input.data = DataInput(
        api_call="https://private.invalid?key=SECRET", api_bearer_token="SECRET"
    )
    first = configuration_identity(config)
    assert first["references_complete"]
    config.app.input.data = DataInput(
        api_call="https://other.invalid", api_bearer_token="CHANGED"
    )
    assert configuration_identity(config) == first
    config.app.dashboard.table_height += 1
    assert configuration_identity(config)["sha256"] != first["sha256"]
    config.app.dashboard.table_height -= 1
    Path(config.app.input.mapping).write_text("changed mapping")
    assert configuration_identity(config)["sha256"] != first["sha256"]
    output = json.dumps(runtime_identity(config))
    for private in ("SECRET", "private.invalid", "other.invalid", str(tmp_path)):
        assert private not in output


# A stale payload version must not masquerade as the installed application version.
def test_identity_uses_package_version_and_validates_sidecar(tmp_path):
    config = _bare_dashboard().config
    config.version = "obsolete"
    config_path = tmp_path / "config/config.yaml"
    config_path.parent.mkdir()
    metadata = tmp_path / "deployment.json"
    metadata.write_text(
        json.dumps(
            {
                "runtime_id": "webservices_test",
                "data_mode": "synthetic",
                "flow_revision": "a" * 40,
            }
        )
    )
    identity = runtime_identity(config, config_path)
    assert identity["software"]["version"] == __version__
    assert "synthetic data" in identity_label(identity)
    assert identity["deployment"]["flow_revision"] == "a" * 40
    metadata.write_text(
        json.dumps({"runtime_id": "private/path", "api_bearer_token": "SECRET"})
    )
    assert runtime_identity(config, config_path)["deployment"]["runtime_id"] is None
    assert "SECRET" not in json.dumps(runtime_identity(config, config_path))


# Safe diagnostics have an explicit switch independent of the raw API debug feature.
def test_dashboard_safe_diagnostics_switch(streamlit_stub, monkeypatch):
    dashboard = _bare_dashboard()
    dashboard._render_identity()
    assert not streamlit_stub.json_calls
    streamlit_stub.query_params["diagnostics"] = "1"
    dashboard._render_identity()
    assert streamlit_stub.json_calls[-1]["software"]["version"] == __version__
    assert not dashboard._is_api_debug_enabled()


# Manual inspection commands must exit before loading data or launching Streamlit.
@pytest.mark.parametrize("module", ["uQCme.cli.main", "uQCme.app.main"])
@pytest.mark.parametrize("flag", ["--version", "--diagnostics"])
def test_manual_identity_commands(module, flag, monkeypatch, capsys):
    import sys

    main = importlib.import_module(module)
    monkeypatch.setattr(sys, "argv", ["uqcme", flag])
    main.main()
    output = capsys.readouterr().out
    if flag == "--diagnostics":
        assert json.loads(output)["software"]["version"] == __version__
    else:
        assert "uQCme " + __version__ in output


# Installed packages retain validated provenance even outside their build checkout.
def test_bundled_metadata(monkeypatch, tmp_path):
    from uQCme.core import identity

    fake_module = tmp_path / "uQCme/core/identity.py"
    fake_module.parent.mkdir(parents=True)
    monkeypatch.setattr(identity, "__file__", str(fake_module))
    metadata = fake_module.parents[1] / "_build_info.json"
    metadata.write_text(
        json.dumps(
            {
                "revision": "b" * 40,
                "dirty": False,
                "built_at": "2026-10-22T12:00:00+00:00",
            }
        )
    )
    assert identity.build_identity()["revision"] == "b" * 40
    metadata.write_text('{"revision": "SECRET"}')
    assert identity.build_identity()["revision"] is None
