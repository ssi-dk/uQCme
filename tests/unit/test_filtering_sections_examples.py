"""Tests for the maintained public FilteringSections mapping examples."""

from pathlib import Path
import sys

import pandas as pd
import pytest
import yaml

# Add src to path for the repository's source-layout test convention.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.filtering import apply_filtering_section, resolve_filtering_sections
from uQCme.core.mapping import parse_filtering_sections


REPOSITORY_ROOT = Path(__file__).parents[2]
EXAMPLE_MAPPINGS = (
    REPOSITORY_ROOT / "input/example/mapping.yaml",
    REPOSITORY_ROOT / "src/uQCme/defaults/mapping.yaml",
)


@pytest.mark.parametrize("mapping_path", EXAMPLE_MAPPINGS)
def test_public_mapping_example_contains_supported_filtering_section(mapping_path):
    # Each maintained mapping exposes synthetic lab-specific presets.
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))

    parsed = parse_filtering_sections(mapping)

    assert list(parsed.sections) == ["LabA view", "LabB view"]
    assert parsed.sections["LabA view"].filters["Lab group"].value == "LabA"
    assert parsed.sections["LabB view"].filters["Lab group"].value == "LabB"


@pytest.mark.parametrize("mapping_path", EXAMPLE_MAPPINGS)
def test_public_mapping_example_resolves_and_filters_documented_rows(mapping_path):
    # Each lab preset resolves and selects its lab's documented rows.
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    parsed = parse_filtering_sections(mapping)
    coverage_column = (
        "Average_Coverage"
        if mapping_path == REPOSITORY_ROOT / "input/example/mapping.yaml"
        else "coverage_x"
    )
    data = pd.DataFrame(
        {
            "sample_name": ["sample_pass", "sample_fail"],
            "qc_outcome": ["PASS", "FAIL,FAIL_SIZE"],
            "species": ["Example organism A", "Example organism B"],
            "qc_action": ["none", "reject"],
            coverage_column: [55, 15],
            "lab_group": ["LabA", "LabB"],
        }
    )

    resolved = resolve_filtering_sections(parsed, data)
    lab_a_rows = apply_filtering_section(data, resolved["LabA view"])
    lab_b_rows = apply_filtering_section(data, resolved["LabB view"])

    assert resolved["LabA view"].available is True
    assert resolved["LabB view"].available is True
    assert lab_a_rows is not None
    assert lab_b_rows is not None
    assert lab_a_rows["sample_name"].tolist() == ["sample_pass"]
    assert lab_b_rows["sample_name"].tolist() == ["sample_fail"]
    assert [field.column for field in resolved["LabA view"].columns] == [
        "sample_name",
        "qc_outcome",
        "species",
    ]
    assert [field.column for field in resolved["LabB view"].columns] == [
        "sample_name",
        "qc_action",
        coverage_column,
    ]


def test_public_mapping_examples_use_only_supported_filtering_section_keys():
    # The maintained examples share the strict public schema contract.
    supported_section_keys = {"columns", "filters"}

    for mapping_path in EXAMPLE_MAPPINGS:
        mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
        sections = mapping["FilteringSections"]

        assert set(sections) == {"LabA view", "LabB view"}
        for section in sections.values():
            assert set(section) == supported_section_keys
            assert set(section["filters"]["Lab group"]) == {
                "data",
                "operator",
                "value",
            }


def test_public_example_data_contains_synthetic_lab_groups():
    # The example input carries the grouping field used by both saved views.
    data = pd.read_csv(
        REPOSITORY_ROOT / "input/example/run_data.tsv",
        sep="\t",
    )

    assert set(data["lab_group"]) == {"LabA", "LabB"}
