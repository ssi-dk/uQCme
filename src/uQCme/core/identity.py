"""Safe, data-independent software and configuration identity."""

import hashlib
import json
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from uQCme import __version__


# Accept only public-safe deployment labels and immutable identifiers.
class DeploymentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = Field(default=1, ge=1, le=1)
    flow_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    installer_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    flow_dirty: bool | None = None
    installer_dirty: bool | None = None
    runtime_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    environment: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,40}$")
    data_mode: str = Field(default="unspecified", pattern=r"^(synthetic|live|unspecified)$")
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


# Validate packaged build metadata before it reaches diagnostic output.
class BuildIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    dirty: bool | None = None
    built_at: str | None = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$"
    )


# Packaged provenance takes priority; editable checkouts may report their own Git identity.
def build_identity():
    metadata = Path(__file__).parents[1] / "_build_info.json"
    if metadata.is_file():
        try:
            return BuildIdentity.model_validate_json(metadata.read_text()).model_dump()
        except (OSError, ValueError):
            return BuildIdentity().model_dump()
    root = Path(__file__).resolve().parents[3]
    if (root / ".git").exists():
        try:
            revision = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
                stderr=subprocess.DEVNULL, timeout=2,
            ).strip()
            dirty = bool(subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"], text=True,
                stderr=subprocess.DEVNULL, timeout=2,
            ).strip())
            return BuildIdentity(revision=revision, dirty=dirty).model_dump()
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return BuildIdentity().model_dump()


# Hash a canonical allowlisted projection, excluding credentials, endpoints and input data.
def configuration_identity(config):
    app = config.app
    projection = {"title": config.title, "outcome_priorities": config.outcome_priorities}
    references = {}
    if app is not None:
        dashboard = app.dashboard
        projection["dashboard"] = {
            key: getattr(dashboard, key) for key in (
                "categorical_filter_threshold", "max_displayed_rules", "table_height"
            )
        }
        projection["dashboard"]["column_presets"] = dashboard.column_presets.model_dump()
        projection["dashboard"]["sample_details"] = dashboard.sample_details.model_dump()
        projection["ui_styling"] = app.ui_styling.model_dump()
        projection["priority_colors"] = app.priority_colors
        source = app.input.data
        values = source.model_dump() if hasattr(source, "model_dump") else source
        projection["source_kind"] = (
            "api" if isinstance(values, dict) and values.get("api_call") else "file"
        )
        projection["query_keys"] = sorted(values.get("api_query_params") or []) if isinstance(values, dict) else []
        for key in ("mapping", "qc_rules", "qc_tests"):
            try:
                references[key] = hashlib.sha256(Path(getattr(app.input, key)).read_bytes()).hexdigest()
            except OSError:
                references[key] = None
    projection["references"] = references
    canonical = json.loads(json.dumps(projection, default=str))
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"sha256": digest, "scope": "presentation-and-qc-references-v1",
            "references_complete": all(value is not None for value in references.values())}


# Sidecar metadata is optional; malformed or unknown fields never leak through diagnostics.
def runtime_identity(config=None, config_path=None):
    result = {"schema_version": 1, "software": {"version": __version__, **build_identity()}}
    if config is not None:
        result["configuration"] = configuration_identity(config)
    deployment = DeploymentIdentity().model_dump()
    if config_path is not None:
        path = Path(config_path).resolve().parent.parent / "deployment.json"
        try:
            deployment = DeploymentIdentity.model_validate_json(path.read_text()).model_dump()
        except (OSError, ValueError):
            pass
    result["deployment"] = deployment
    return result


# Keep a short identity visible in manual workflows without exposing configuration values.
def identity_label(identity):
    software = identity["software"]
    revision = software["revision"]
    build = revision[:12] if revision else "unknown"
    if software["dirty"]:
        build += "+dirty"
    parts = [f"uQCme {software['version']}", f"build {build}"]
    if "configuration" in identity:
        parts.append("config " + identity["configuration"]["sha256"][:12])
    mode = identity["deployment"]["data_mode"]
    if mode != "unspecified":
        parts.append(mode + " data")
    return " · ".join(parts)
