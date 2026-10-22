"""Run a small functional baseline, the remaining regressions, or the complete local suite."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ESSENTIAL = (
    "tests/integration/test_qc_outcomes.py::test_fresh_legacy_processing_preserves_reviewed_outcomes",
    "tests/integration/test_qc_outcomes.py::test_new_schema_evaluates_available_metrics",
    "tests/unit/test_species.py::test_aliases_resolve_to_the_configured_rule_name",
    "tests/unit/test_species.py::test_reversed_legacy_alias_entries_have_an_actionable_error",
    "tests/unit/test_dashboard_api.py::test_load_data_from_api_with_bearer_token",
    "tests/unit/test_identity.py::test_identity_projection_is_stable_private_and_changes_with_settings",
    "tests/unit/test_identity.py::test_identity_uses_package_version_and_validates_sidecar",
)


# Keep core selectors explicit and leave slow/external rehearsal opt-in.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("essential", "conditional", "all"), nargs="?", default="essential")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    selection = list(ESSENTIAL) if args.suite == "essential" else []
    if args.suite == "conditional":
        selection = ["--deselect=" + node for node in ESSENTIAL]
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *selection,
                            *(["--collect-only"] if args.list else [])], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
