"""Tests for the public synthetic new-schema dataset."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.engine import QCProcessor  # noqa: E402
from uQCme.core.filtering import (  # noqa: E402
    apply_filtering_section,
    resolve_filtering_sections,
)
from uQCme.core.mapping import parse_filtering_sections  # noqa: E402


REPOSITORY_ROOT = Path(__file__).parents[2]
NEW_DATA_PATH = REPOSITORY_ROOT / "input/example/run_data_new_schema.tsv"
NEW_OUTPUT_PATH = REPOSITORY_ROOT / "tests/fixtures/new_schema_example_run_data.tsv"
OLD_DATA_PATH = REPOSITORY_ROOT / "input/example/run_data.tsv"
COLUMNS_PATH = REPOSITORY_ROOT / "tests/fixtures/new_schema_columns.txt"
GENERATOR_PATH = REPOSITORY_ROOT / "tests/fixtures/generate_new_schema_fixture.py"


def _manifest_columns() -> list[str]:
    return [
        line.strip()
        for line in COLUMNS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_new_schema_fixture_matches_public_manifest_and_legacy_samples():
    # The new fixture uses the new header and preserves every legacy sample.
    new_data = pd.read_csv(NEW_DATA_PATH, sep="\t")
    old_data = pd.read_csv(OLD_DATA_PATH, sep="\t")
    legacy_output = pd.read_csv(
        REPOSITORY_ROOT / "tests/uQCme_example_run_data.tsv", sep="\t"
    )

    assert list(new_data.columns) == _manifest_columns()
    assert len(new_data) == len(old_data)
    assert new_data["sample_name"].tolist() == old_data["sample_name"].tolist()
    assert "rMLST_match" not in legacy_output.columns
    assert "provided_species" not in new_data.columns
    assert set(new_data["lab_group"]) == {"LabA", "LabB"}
    assert {
        "rMLST_match",
        "rMLST_support",
        "Bracken_Species",
        "Bracken_Species1",
        "MLST_Species",
    }.issubset(new_data.columns)


def test_new_schema_fixture_transfers_lab_groups_by_sample_name():
    # Lab groups are copied by identity, not inferred from species or metrics.
    new_data = pd.read_csv(NEW_DATA_PATH, sep="\t").set_index("sample_name")
    old_data = pd.read_csv(OLD_DATA_PATH, sep="\t").set_index("sample_name")

    pd.testing.assert_series_equal(
        new_data["lab_group"].sort_index(),
        old_data["lab_group"].sort_index(),
        check_names=False,
    )


def test_new_schema_fixture_covers_direct_alias_mismatch_and_missing_rmlst():
    # Synthetic rMLST values exercise each Sample Details status category.
    data = pd.read_csv(NEW_DATA_PATH, sep="\t").set_index("sample_name")

    assert data.loc["example_pass_ecoli", "species"] == "E. coli"
    assert data.loc["example_pass_ecoli", "rMLST_match"] == "Escherichia coli"
    assert (
        data.loc["example_pass_general_fail_species_kp", "rMLST_match"]
        == "Klebsiella pneumoniae"
    )
    assert (
        data.loc["example_warn_review", "rMLST_match"]
        == "Cronobacter sakazakii"
    )
    assert pd.isna(data.loc["test_fail_adapter", "rMLST_match"])


def test_new_schema_fixture_generation_is_deterministic(tmp_path):
    # Regeneration from the public source fixture produces identical bytes.
    regenerated_path = tmp_path / "run_data_new_schema.tsv"
    subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--source",
            str(OLD_DATA_PATH),
            "--columns",
            str(COLUMNS_PATH),
            "--output",
            str(regenerated_path),
        ],
        check=True,
    )

    assert regenerated_path.read_bytes() == NEW_DATA_PATH.read_bytes()


def test_new_schema_processed_fixture_has_regenerated_qc_results():
    # The processed fixture contains results generated from the new input.
    output_data = pd.read_csv(NEW_OUTPUT_PATH, sep="\t")

    assert len(output_data) == 19
    assert {"failed_rules", "passed_rules", "qc_outcome", "qc_action"}.issubset(
        output_data.columns
    )
    assert output_data["qc_outcome"].notna().all()
    assert output_data["qc_action"].notna().all()


def test_new_schema_mapping_routes_qc_species_fields_to_species():
    # New QC species fields use the provided category, not rMLST_match.
    mapping = yaml.safe_load(
        (REPOSITORY_ROOT / "input/example/mapping.yaml").read_text(encoding="utf-8")
    )
    provided_species = mapping["Sections"]["QC_metrics"]["Provided Species"]
    expected_species = mapping["Sections"]["QC_metrics"]["Expected species"]

    assert provided_species["data"]["mapping"] == "species"
    assert provided_species["QC"]["mapping"] == [
        "speciesName",
        "genusName",
        "Marker lineage",
    ]
    assert expected_species["data"]["mapping"] == "rMLST_match"
    assert "QC" not in expected_species


def test_new_schema_default_config_and_lab_filters_use_new_columns():
    # The local default and saved lab views resolve against the new schema.
    config = yaml.safe_load(
        (REPOSITORY_ROOT / "config.yaml").read_text(encoding="utf-8")
    )
    assert config["qc"]["input"]["data"]["file"].endswith(
        "input/example/run_data_new_schema.tsv"
    )

    mapping = yaml.safe_load(
        (REPOSITORY_ROOT / "input/example/mapping.yaml").read_text(encoding="utf-8")
    )
    parsed = parse_filtering_sections(mapping)
    data = pd.read_csv(NEW_DATA_PATH, sep="\t")
    resolved = resolve_filtering_sections(parsed, data)

    assert resolved["LabA view"].available is True
    assert resolved["LabB view"].available is True
    assert len(apply_filtering_section(data, resolved["LabA view"])) > 0
    assert len(apply_filtering_section(data, resolved["LabB view"])) > 0
    assert [field.column for field in resolved["LabB view"].columns] == [
        "sample_name",
        "qc_action",
        "Average_Coverage",
    ]


def test_new_schema_qc_engine_maps_species_rules_to_species():
    # The engine resolves all configured species-rule fields to species.
    processor = QCProcessor(
        str(REPOSITORY_ROOT / "tests/fixtures/config_new_schema.yaml")
    )
    processor.load_input_files()
    field_mapping = processor._build_field_mapping()

    assert field_mapping["speciesName"] == "species"
    assert field_mapping["genusName"] == "species"
    assert field_mapping["Marker lineage"] == "species"
    assert "rMLST_match" not in {
        field_mapping["speciesName"],
        field_mapping["genusName"],
        field_mapping["Marker lineage"],
    }
