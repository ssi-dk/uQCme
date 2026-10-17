from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest


# Exercise Streamlit's real widget lifecycle without a network service.
SCRIPT = """
import streamlit as st
import pandas as pd
from uQCme.app.main import QCDashboard
from uQCme.core.config import UQCMeConfig

dashboard = QCDashboard.__new__(QCDashboard)
dashboard.config = UQCMeConfig(app={"input": {
    "mapping": "unused", "qc_rules": "unused", "qc_tests": "unused"
}})
dashboard.report_mode = False
dashboard.mapping = {"Sections": {
    "Basic": {"Sample": {"data": {"mapping": "isolate_id"}, "report": {"id": True}}},
    "Metrics": {"Depth": {"data": {"mapping": "depth"}, "report": {
        "description": "Sequencing depth for this sample"
    }}}
}}
dashboard.qc_rules = pd.DataFrame()
dashboard.data = pd.DataFrame({"isolate_id": ["S1", "S2"], "depth": [20, 50]})
dashboard.render_data_tab(dashboard.data)
dashboard.render_sample_details_tab(dashboard.data)
"""


@pytest.mark.parametrize(
    "dashboard_config",
    [
        "{}",
        "{'column_presets': {}}",
        "{'column_presets': None, 'sample_details': None}",
    ],
)
def test_basic_table_works_without_optional_presets(dashboard_config):
    script = SCRIPT.replace(
        "dashboard.report_mode = False",
        "dashboard.config.app.dashboard = type(dashboard.config.app.dashboard)(**"
        + dashboard_config
        + ")\ndashboard.report_mode = False",
    )
    app = AppTest.from_string(script).run()

    assert not app.exception
    assert list(app.dataframe[0].value.columns) == ["isolate_id", "depth", "Select"]
    assert not app.multiselect


def test_navigation_uses_the_mapped_id_and_keeps_column_explanations():
    app = AppTest.from_string(SCRIPT).run()
    markdown = "\n".join(element.value for element in app.markdown)

    assert not app.exception
    assert 'href="#sample-s1"' in markdown
    assert 'href="#sample-s2"' in markdown
    assert "Sequencing depth for this sample" in markdown


def test_optional_presets_and_customization_work_with_real_widgets():
    script = SCRIPT.replace(
        "dashboard.report_mode = False",
        "dashboard.config.app.dashboard.column_presets.presets = {"
        "'Standard': {'columns': {'Basic': ['Sample']}}, "
        "'All': {'columns': '*'}}\ndashboard.report_mode = False",
    )
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert list(app.dataframe[0].value.columns) == ["isolate_id", "Select"]
    app.button(key="data_preview_preset_All").click().run()
    assert not app.exception
    assert "depth" in app.dataframe[0].value.columns
    app.multiselect(key="data_preview_custom_columns_Metrics").set_value([])
    next(
        button for button in app.button if button.label == "Apply custom view"
    ).click().run()
    assert not app.exception
    assert list(app.dataframe[0].value.columns) == ["isolate_id", "Select"]


def test_missing_metric_caveat_is_visible_alongside_the_sample_result():
    script = SCRIPT.replace(
        '"depth": [20, 50]',
        '"depth": [20, 50], "qc_outcome": ["PASS", "FAIL"], '
        '"missing_qc_fields": ["quality", ""]',
    )
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert len(app.warning) == 1
    assert "QC caveat" in app.warning[0].value
    assert "quality" in app.warning[0].value
    assert any("**qc_outcome:** PASS" in item.value for item in app.markdown)


def test_invalid_species_mapping_is_rejected_before_api_input(processor_factory):
    processor = processor_factory("local_example")
    directory = Path(processor.qc_config.output.results).parent
    config_path = directory / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    mapping = {"SpeciesAliases": {"K. pneumoniae": ["Klebsiella pneumoniae"]}}
    mapping_path = directory / "reversed-species.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping))
    config["app"]["input"]["mapping"] = str(mapping_path)
    config["app"]["input"]["data"] = {"api_call": "https://example.test/synthetic"}
    config_path.write_text(yaml.safe_dump(config))
    script = (
        "from uQCme.app.main import QCDashboard\nQCDashboard("
        + repr(str(config_path))
        + ").load_data()"
    )
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert len(app.error) == 1
    assert "QC rule name 'Klebsiella pneumoniae'" in app.error[0].value
