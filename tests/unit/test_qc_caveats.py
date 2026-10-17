import pandas as pd
import pytest


@pytest.fixture
def processor(processor_factory):
    result = processor_factory()
    result.mapping = {"Sections": {"QC": {
        "Depth": {"data": {"mapping": "depth"}, "QC": {"mapping": "read_depth"}}
    }}}
    result.qc_rules = pd.DataFrame([
        {"rule_id": "DEPTH", "species": "all", "assembly_type": "all",
         "software": "fixture", "field": "read_depth", "operator": ">=", "value": 5},
        {"rule_id": "QUALITY", "species": "all", "assembly_type": "all",
         "software": "fixture", "field": "quality", "operator": ">=", "value": 30},
    ])
    result.qc_tests = pd.DataFrame([
        {"outcome_id": "PASS", "passed_rule_conditions": "DEPTH,QUALITY",
         "failed_rule_conditions": "", "priority": 1, "action_required": "none"},
        {"outcome_id": "FAIL", "passed_rule_conditions": "",
         "failed_rule_conditions": "DEPTH,QUALITY", "priority": 2, "action_required": "reject"},
    ])
    return result


@pytest.mark.parametrize("depth,outcome,action", [(10, "PASS", "none"), (1, "FAIL", "reject")])
def test_absent_metrics_are_caveats_alongside_the_existing_qc_result(processor, depth, outcome, action):
    processor.run_data = pd.DataFrame([{"sample_name": "S1", "depth": depth}])
    processor.process_samples()
    actual = processor.results.iloc[0]
    assert actual.qc_outcome == outcome
    assert actual.qc_action == action
    assert actual.skipped_rules == "QUALITY"
    assert actual.missing_qc_fields == "quality"


@pytest.mark.parametrize("missing_value", [None, float("nan"), "", "null", "None", "NaN"])
def test_null_values_keep_existing_failure_semantics_and_are_flagged(processor, missing_value):
    processor.run_data = pd.DataFrame([{"sample_name": "S1", "depth": missing_value}])
    processor.process_samples()
    actual = processor.results.iloc[0]
    assert actual.qc_outcome == "FAIL"
    assert actual.failed_rules == "DEPTH"
    assert actual.skipped_rules == "QUALITY"
    assert actual.missing_qc_fields == "depth,quality"


def test_caveats_are_per_sample_and_only_include_applicable_rules(processor):
    processor.qc_rules.loc[1, "species"] = "Species B"
    processor.run_data = pd.DataFrame([
        {"sample_name": "S1", "species": "Species A", "depth": 10},
        {"sample_name": "S2", "species": "Species B", "depth": 10},
    ])
    processor.process_samples()
    first, second = processor.results.iloc[0], processor.results.iloc[1]
    assert first.skipped_rules == first.missing_qc_fields == ""
    assert second.skipped_rules == "QUALITY"
    assert second.missing_qc_fields == "quality"


def test_configured_species_column_drives_rule_selection_and_values(processor):
    processor.mapping = {
        "SpeciesAliases": {"Species A": ["A"]},
        "Sections": {"Identity": {"Organism": {
            "data": {"mapping": "organism"},
            "report": {"species": True},
            "QC": {"mapping": ["speciesName"]},
        }}},
    }
    processor.qc_rules = pd.DataFrame([{
        "rule_id": "IDENTITY", "species": "Species A", "assembly_type": "all",
        "software": "fixture", "field": "speciesName", "operator": "regex", "value": "^Species A$",
    }])
    processor.qc_tests.loc[0, "passed_rule_conditions"] = "IDENTITY"
    processor.run_data = pd.DataFrame([{"sample_name": "S1", "organism": "A"}])
    processor.process_samples()
    actual = processor.results.iloc[0]
    assert actual.organism == "A"
    assert actual.passed_rules == "IDENTITY"
    assert actual.skipped_rules == ""
    assert actual.qc_outcome == "PASS"
