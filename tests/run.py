"""Run a small functional baseline, the remaining regressions, or the complete local suite."""
import argparse
from pathlib import Path

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


# Match exact test functions, including their parameters, rather than name prefixes.
class RemainingTests:
    def pytest_collection_modifyitems(self, config, items):
        excluded = [item for item in items if item.nodeid.split("[", 1)[0] in ESSENTIAL]
        config.hook.pytest_deselected(items=excluded)
        items[:] = [item for item in items if item not in excluded]


# Keep core selectors explicit and leave slow/external rehearsal opt-in.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("essential", "conditional", "all"), nargs="?", default="essential")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    selection = list(ESSENTIAL) if args.suite == "essential" else []
    import os
    import pytest

    os.chdir(ROOT)
    return pytest.main(["-q", *selection, *(["--collect-only"] if args.list else [])],
                       plugins=[RemainingTests()] if args.suite == "conditional" else [])


if __name__ == "__main__":
    raise SystemExit(main())
