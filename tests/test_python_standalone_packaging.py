#!/usr/bin/env python3
"""Tests for optional python-build-standalone bundle assets."""

import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml


APP_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.standalone
def test_python_standalone_build_script_help():
    """The standalone bundle builder should document required inputs."""
    script_path = APP_ROOT / "scripts" / "build_python_standalone_bundle.py"

    proc = subprocess.run(
        ["python", str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "--profile" in proc.stdout
    assert "--python-bin" in proc.stdout
    assert "--python-archive" in proc.stdout
    assert "--download-python" in proc.stdout
    assert "python-build-standalone" in proc.stdout


@pytest.mark.standalone
def test_python_standalone_build_script_contains_profiles_and_launchers():
    """The builder should define the CLI and dashboard artifact profiles."""
    script_path = APP_ROOT / "scripts" / "build_python_standalone_bundle.py"
    script_text = script_path.read_text(encoding="utf-8")

    assert "uqcme-cli-standalone" in script_text
    assert "uqcme-dashboard-standalone" in script_text
    assert '"uqcme": "uQCme.cli.main"' in script_text
    assert '"uqcme-dashboard": "uQCme.app.main"' in script_text
    assert '"uqcme-dashboard-smoke": "uQCme.app.smoke"' in script_text
    assert 'tarfile.open(archive_path, "w:gz")' in script_text


@pytest.mark.standalone
def test_pixi_config_includes_standalone_packaging_tasks():
    """Pixi should expose standalone bundle build paths."""
    pixi_path = APP_ROOT / "pixi.toml"
    pixi_text = pixi_path.read_text(encoding="utf-8")

    assert "getpybs" in pixi_text
    assert "build-standalone" in pixi_text
    assert "--profile all" in pixi_text
    assert "--profile cli" in pixi_text
    assert "--profile dashboard" in pixi_text


@pytest.mark.standalone
def test_package_defines_dashboard_smoke_console_script():
    """The dashboard smoke command should be a standard package script."""
    pyproject_path = APP_ROOT / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    assert 'uqcme-dashboard-smoke = "uQCme.app.smoke:main"' in pyproject_text


@pytest.mark.standalone
def test_cli_profile_installs_core_runtime_dependencies():
    """The CLI standalone bundle needs dependencies imported by shared core code."""
    pyproject_path = APP_ROOT / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    dependencies = pyproject["project"]["dependencies"]

    assert "requests>=2.31.0" in dependencies


@pytest.mark.standalone
def test_github_action_builds_and_uploads_both_standalone_bundles():
    """The GitHub workflow should publish both standalone tarballs."""
    workflow_path = APP_ROOT / ".github" / "workflows" / "build-standalone.yml"
    with workflow_path.open("r", encoding="utf-8") as handle:
        workflow = yaml.safe_load(handle)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["name"] == "Build Standalone Bundles"
    assert "workflow_dispatch" in workflow_text
    assert "pixi run build-standalone" in workflow_text
    assert "uqcme-cli-standalone-linux-x86_64.tar.gz" in workflow_text
    assert "uqcme-dashboard-standalone-linux-x86_64.tar.gz" in workflow_text


@pytest.mark.standalone
def test_marker_configuration_documents_standalone_and_dashboard_smoke():
    """Pytest markers should let users exclude slow validation families."""
    pyproject_text = (APP_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "standalone: standalone packaging tests" in pyproject_text
    assert "dashboard_smoke: dashboard process startup" in pyproject_text
