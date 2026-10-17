import pandas as pd
import pytest

from tests.support.processing import REPOSITORY_ROOT, make_processor


@pytest.fixture(scope="module")
def legacy_run(tmp_path_factory):
    processor = make_processor("legacy", tmp_path_factory.mktemp("legacy-qc"))
    processor.load_input_files()
    processor.process_samples()
    return processor


@pytest.fixture(scope="module")
def new_schema_run(tmp_path_factory):
    processor = make_processor("new_schema", tmp_path_factory.mktemp("new-schema-qc"))
    processor.load_input_files()
    processor.process_samples()
    return processor


LEGACY_EXPECTED = pd.read_csv(
    REPOSITORY_ROOT / "tests/uQCme_example_run_data.tsv",
    sep="\t", keep_default_na=False,
).set_index("sample_name")


# The checked-in baseline is an expected result, never the actual result.
@pytest.mark.parametrize("sample_name", LEGACY_EXPECTED.index.tolist())
def test_fresh_legacy_processing_preserves_reviewed_outcomes(legacy_run, sample_name):
    actual = legacy_run.results.set_index("sample_name").loc[sample_name]
    expected = LEGACY_EXPECTED.loc[sample_name]
    assert set(actual.qc_outcome.split(",")) == set(expected.qc_outcome.split(","))
    assert set(actual.failed_rules.split(",")) == set(expected.failed_rules.split(","))
    assert actual.qc_action == expected.qc_action


@pytest.mark.parametrize(
    "sample_name, outcome, failed_rule",
    [
        ("example_fail_assembly", "FAIL_GENERAL", "A10"),
        ("example_pass_general_fail_species_kp", "FAIL_KLEBSIELLA_PNEUMONIAE", "KP1"),
        ("test_species_sa_fail_gc", "FAIL_STAPHYLOCOCCUS_AUREUS", "SA12"),
        ("test_multiple_failures", "FAIL", "WARN1"),
    ],
)
def test_new_schema_evaluates_available_metrics(new_schema_run, sample_name, outcome, failed_rule):
    actual = new_schema_run.results.set_index("sample_name").loc[sample_name]
    assert outcome in actual.qc_outcome.split(",")
    assert failed_rule in actual.failed_rules.split(",")
    assert failed_rule not in actual.skipped_rules.split(",")
    assert actual.qc_action == "reject"


def test_pass_and_fail_both_retain_missing_metric_caveats(new_schema_run):
    results = new_schema_run.results.set_index("sample_name")
    passed = results.loc["example_pass_ecoli"]
    failed = results.loc["example_fail_assembly"]
    assert "PASS" in passed.qc_outcome.split(",")
    assert "FAIL_GENERAL" in failed.qc_outcome.split(",")
    for sample in (passed, failed):
        assert "q30_fraction" in sample.missing_qc_fields.split(",")
        assert "PASS3" in sample.skipped_rules.split(",")


@pytest.mark.parametrize("species", ["Klebsiella pneumoniae", "K. pneumoniae", "  K. PNEUMONIAE  "])
def test_aliases_evaluate_the_same_rules_and_preserve_input(processor_factory, species):
    processor = processor_factory()
    processor.load_input_files()
    processor.run_data = processor.run_data.loc[
        processor.run_data.sample_name == "example_pass_general_fail_species_kp"
    ].copy()
    processor.process_samples()
    canonical_result = processor.results.iloc[0].copy()
    processor.run_data["species"] = species
    processor.process_samples()
    actual = processor.results.iloc[0]
    for column in ("failed_rules", "passed_rules", "skipped_rules", "qc_outcome", "qc_action"):
        assert actual[column] == canonical_result[column]
    assert actual.species == species
    assert "FAIL_KLEBSIELLA_PNEUMONIAE" in actual.qc_outcome.split(",")
    assert {"KP1", "KP3", "KP9", "KP11"}.issubset(actual.failed_rules.split(","))
    assert {"KP8", "KP13", "KP15"}.issubset(actual.passed_rules.split(","))


def test_saving_results_and_warnings_uses_the_run_output_directory(new_schema_run):
    new_schema_run.save_results()
    new_schema_run.save_warnings()
    actual = pd.read_csv(new_schema_run.qc_config.output.results, sep="\t", keep_default_na=False)
    assert len(actual) == len(new_schema_run.results)
    assert {"skipped_rules", "missing_qc_fields"}.issubset(actual.columns)
    warnings = pd.read_csv(new_schema_run.qc_config.output.warnings, sep="\t")
    assert "skipped_rule" in set(warnings.warning_type)
