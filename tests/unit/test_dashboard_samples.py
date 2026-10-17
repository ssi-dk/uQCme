import importlib
from pathlib import Path

import pandas as pd
import yaml

from tests.support.dashboard import _bare_dashboard

dashboard_main = importlib.import_module("uQCme.app.main")


def test_sample_details_renders_numeric_string_quality_metrics(streamlit_stub):
    """Sample details should show plottable and categorical metric values."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "QC Outcome": {"data": {"mapping": "qc_outcome"}},
                "QC Label": {
                    "data": {"mapping": "qc_label"},
                    "report": {"quality_metric": True},
                },
            },
            "Read_QC": {
                "Coverage": {
                    "data": {"mapping": "coverage_x"},
                    "QC": {"mapping": "Coverage"},
                    "report": {"filter": True},
                },
                "Number of genomes": {
                    "data": {"mapping": "number_of_genomes"},
                    "QC": {"mapping": "number_of_genomes"},
                },
            },
        }
    }
    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "qc_outcome": "PASS",
                "coverage_x": "45.5",
                "number_of_genomes": "2",
                "qc_label": "good",
                "RunID": "12345",
            }
        ]
    )
    dashboard.data = data

    dashboard.render_sample_details_tab(data)

    assert "**Coverage:** 45.5" in streamlit_stub.write_calls
    assert "**Number of genomes:** 2" in streamlit_stub.write_calls
    assert "**QC Label:** good" in streamlit_stub.write_calls
    assert "**RunID:** 12,345" not in streamlit_stub.write_calls


def test_sample_details_resolves_detected_species_from_mapping():
    # The default mapping names the detected species source rMLST_match.
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "QC_metrics": {
                "Expected species": {
                    "data": {"mapping": "rMLST_match"},
                }
            }
        }
    }

    assert dashboard._get_detected_species_field() == "rMLST_match"


def test_species_aliases_are_loaded_from_mapping_yaml():
    # Species aliases are read from the maintained YAML mapping.
    dashboard = _bare_dashboard()
    mapping_path = Path(__file__).parents[1] / "data" / "mapping.yaml"
    dashboard.mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))

    assert dashboard._get_species_aliases()["Klebsiella pneumoniae"] == ["K. pneumoniae"]
    assert dashboard._species_values_match("K. pneumoniae", "Klebsiella pneumoniae")
    assert not dashboard._species_values_match("Klebsiella", "Klebsiella pneumoniae")


def test_curated_species_aliases_match_detected_values():
    # Every curated alias should be accepted by the Sample Details comparison.
    dashboard = _bare_dashboard()
    mapping_path = Path(__file__).parents[1] / "data" / "mapping.yaml"
    dashboard.mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))

    for provided, detected_values in dashboard._get_species_aliases().items():
        for detected in detected_values:
            assert dashboard._species_values_match(provided, detected)


def test_sample_details_renders_detected_species_match_status(streamlit_stub):
    # Every filtered sample gets a compact green or red detected-species row.
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "SpeciesAliases": {
            "Yersinia enterocolitica": ["Yersinia"],
            "Shigella sonnei": ["S. sonnei"],
            "Salmonella enterica": ["Salmonella"],
        },
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "Provided Species": {"data": {"mapping": "species"}},
                "Expected species": {
                    "data": {"mapping": "rMLST_match"},
                },
            }
        },
    }
    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "species": "Escherichia coli",
                "rMLST_match": " escherichia coli ",
            },
            {
                "sample_name": "S2",
                "species": "Escherichia coli",
                "rMLST_match": "Klebsiella pneumoniae",
            },
            {
                "sample_name": "S3",
                "species": "Escherichia coli",
                "rMLST_match": pd.NA,
            },
            {
                "sample_name": "S4",
                "species": "Yersinia",
                "rMLST_match": "Yersinia enterocolitica",
            },
            {
                "sample_name": "S5",
                "species": "S. sonnei",
                "rMLST_match": "Shigella sonnei",
            },
            {
                "sample_name": "S6",
                "species": "Salmonella",
                "rMLST_match": "Salmonella enterica",
            },
            {
                "sample_name": "S7",
                "species": "Unknown category",
                "rMLST_match": "Unknown detected value",
            },
        ]
    )

    dashboard.render_sample_details_tab(data)

    detected_markdown = [
        message
        for message, _ in streamlit_stub.markdown_calls
        if "**detected species:**" in message
    ]
    assert len(detected_markdown) == len(data)
    assert "color: #00AA00" in detected_markdown[0]
    assert "escherichia coli" in detected_markdown[0]
    assert "color: #DC143C" in detected_markdown[1]
    assert "Klebsiella pneumoniae" in detected_markdown[1]
    assert "color: #DC143C" in detected_markdown[2]
    assert "—" in detected_markdown[2]
    assert all("color: #00AA00" in detected_markdown[index] for index in (3, 4, 5))
    assert "color: #DC143C" in detected_markdown[6]

    navigation_html = next(
        message
        for message, _ in streamlit_stub.markdown_calls
        if 'class="uqcme-sample-index"' in message
    )
    assert "detected species" not in navigation_html


def test_sample_sort_is_natural_case_insensitive_and_stable():
    # Sample ordering should handle numeric suffixes and equivalent names.
    dashboard = _bare_dashboard()
    data = pd.DataFrame(
        [
            {"sample_name": "Sample-10", "source_order": 0},
            {"sample_name": "sample-2", "source_order": 1},
            {"sample_name": "SAMPLE-2", "source_order": 2},
            {"sample_name": "Sample-1", "source_order": 3},
            {"sample_name": None, "source_order": 4},
            {"sample_name": "Sample-1", "source_order": 5},
        ]
    )

    sorted_data = dashboard._sort_samples_naturally(data)

    assert list(sorted_data["sample_name"]) == [
        "Sample-1",
        "Sample-1",
        "sample-2",
        "SAMPLE-2",
        "Sample-10",
        None,
    ]
    assert list(sorted_data["source_order"]) == [3, 5, 1, 2, 0, 4]
    assert sorted_data is not data


def test_sample_sort_preserves_order_without_sample_name():
    # Datasets without the canonical sample name should remain unchanged.
    dashboard = _bare_dashboard()
    data = pd.DataFrame(
        [
            {"sample_id": "ID-2"},
            {"sample_id": "ID-1"},
        ]
    )

    sorted_data = dashboard._sort_samples_naturally(data)

    assert list(sorted_data["sample_id"]) == ["ID-2", "ID-1"]
    assert sorted_data is not data


def test_sample_details_renders_navigation_and_every_filtered_sample(streamlit_stub):
    # Sample Details should render one linked section for every filtered row.
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "Species": {
                    "data": {"mapping": "species"},
                    "QC": {"mapping": "species"},
                },
                "QC Outcome": {"data": {"mapping": "qc_outcome"}},
                "QC Action": {"data": {"mapping": "qc_action"}},
                "Q30 fraction": {
                    "data": {"mapping": "observed_q30"},
                    "QC": {"mapping": "q30_fraction"},
                },
            }
        }
    }
    dashboard.qc_rules = pd.DataFrame(
        [
            {
                "rule_id": "PASS3",
                "software": "fastp",
                "field": "q30_fraction",
                "operator": ">=",
                "value": "0.80",
            }
        ]
    )
    data = pd.DataFrame(
        [
            {
                "sample_name": "Sample-10",
                "species": "Listeria",
                "qc_outcome": "FAIL",
                "qc_action": "Review",
                "failed_rules": "PASS3",
                "passed_rules": "rule-1",
                "observed_q30": 0.6,
            },
            {
                "sample_name": "Sample-2",
                "species": "E. coli",
                "qc_outcome": "PASS",
                "qc_action": "Release",
                "failed_rules": "",
                "passed_rules": "rule-1",
                "observed_q30": 0.9,
            },
        ]
    )

    dashboard.render_sample_details_tab(dashboard._sort_samples_naturally(data))

    navigation_html, navigation_kwargs = next(
        (message, kwargs)
        for message, kwargs in streamlit_stub.markdown_calls
        if 'class="uqcme-sample-index"' in message
    )
    html_lines = [
        line for line in navigation_html.splitlines() if line.lstrip().startswith("<")
    ]
    assert navigation_html.startswith("<style>")
    assert all(line == line.lstrip() for line in html_lines)
    assert '\n<table class="uqcme-sample-index">\n' in navigation_html
    assert "\n<tbody>\n<tr>" in navigation_html
    assert navigation_kwargs["unsafe_allow_html"] is True
    assert "rgba(128, 128, 128, 0.35)" in navigation_html
    assert "rgba(128, 128, 128, 0.14)" in navigation_html
    assert "color: inherit" in navigation_html

    markdown = "\n".join(message for message, _ in streamlit_stub.markdown_calls)
    assert "Sample Name</th>" in markdown
    assert "Species</th>" in markdown
    assert "QC Outcome</th>" in markdown
    assert "QC Action</th>" in markdown
    assert "Details" not in markdown
    assert 'href="#sample-sample-2"' in markdown
    assert 'href="#sample-sample-10"' in markdown
    assert "[Back to sample index](#sample-index)" in markdown
    assert "<select" not in markdown
    assert streamlit_stub.write_calls.count("**sample_name:** Sample-2") == 1
    assert streamlit_stub.write_calls.count("**sample_name:** Sample-10") == 1
    assert "**Passed Rules:**" not in streamlit_stub.write_calls
    assert "✅ rule-1" not in streamlit_stub.write_calls
    assert streamlit_stub.columns_calls == [
        ([1, 1, 1], {"gap": "large"}),
        ([1, 1, 1], {"gap": "large"}),
    ]
    assert streamlit_stub.events.count("subheader:Failed Rules") == 2
    assert (
        "❌ fastp q30_fraction must be ≥ 0.80; observed 0.6"
        in streamlit_stub.write_calls
    )
    assert "❌ PASS3" not in streamlit_stub.write_calls
    assert "✅ No failed rules" in streamlit_stub.write_calls


def test_failed_rule_description_falls_back_without_rule_definition():
    # Unresolvable rule IDs should remain visible instead of hiding a failure.
    dashboard = _bare_dashboard()

    description = dashboard._format_failed_rule("UNKNOWN1", pd.Series(dtype=object))

    assert description == "UNKNOWN1 (rule definition unavailable)"


def test_failed_rule_description_handles_missing_observed_value():
    # API data may contain a failed rule without carrying its source metric.
    dashboard = _bare_dashboard()
    dashboard.qc_rules = pd.DataFrame(
        [
            {
                "rule_id": "RULE1",
                "software": "Checkm",
                "field": "Completeness",
                "operator": ">=",
                "value": "90",
            }
        ]
    )

    description = dashboard._format_failed_rule(
        "RULE1", pd.Series({"sample_name": "Sample-1"})
    )

    assert description == "Checkm Completeness must be ≥ 90; observed unavailable"


def test_sample_details_navigation_columns_come_from_config(streamlit_stub):
    streamlit_stub.reset()
    dashboard = _bare_dashboard()

    dashboard.config.app.dashboard.sample_details.index_columns = [
        "sample_name",
        "coverage_x",
        "qc_action",
    ]

    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {
                        "id": True,
                        "label": "Configured <sample>",
                    },
                },
            },
            "Read_QC": {
                "Action": {
                    "data": {"mapping": "qc_action"},
                    "report": {"label": "Disposition"},
                },
                "Coverage": {
                    "data": {"mapping": "coverage_x"},
                    "report": {"label": "Read depth"},
                },
            },
        }
    }

    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "coverage_x": 120,
                "qc_action": "review",
                "species": "Not indexed",
                "qc_outcome": "FAIL",
            }
        ]
    )

    dashboard.render_sample_details_tab(data)

    navigation_html = next(
        message
        for message, _ in streamlit_stub.markdown_calls
        if 'class="uqcme-sample-index"' in message
    )

    assert "Configured <sample>" not in navigation_html

    assert (
        navigation_html.index("Configured &lt;sample&gt;</th>")
        < navigation_html.index("Read depth</th>")
        < navigation_html.index("Disposition</th>")
    )

    assert 'href="#sample-s1"' in navigation_html
    assert "<td>120</td>" in navigation_html
    assert "<td>review</td>" in navigation_html


def test_sample_details_escapes_values_and_disambiguates_duplicate_anchors(streamlit_stub):
    # Data values must not become HTML, and every row needs a unique target.
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                },
                "Species": {"QC": {"mapping": "species"}},
            }
        }
    }
    data = pd.DataFrame(
        [
            {
                "sample_name": "A/B <one>",
                "species": "<b>unsafe</b>",
            },
            {
                "sample_name": "A/B <one>",
                "species": "Second & species",
            },
        ]
    )

    dashboard.render_sample_details_tab(data)

    markdown = "\n".join(message for message, _ in streamlit_stub.markdown_calls)
    assert 'id="sample-a-b-one-1"' in markdown
    assert 'id="sample-a-b-one-2"' in markdown
    assert 'href="#sample-a-b-one-1"' in markdown
    assert 'href="#sample-a-b-one-2"' in markdown
    assert "A/B <one>" not in markdown
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in markdown
    assert "Second &amp; species" in markdown


def test_sample_details_preserves_empty_and_missing_id_warnings(streamlit_stub):
    # Existing validation messages should remain distinct after the refactor.
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Basic": {
                "Sample Name": {
                    "data": {"mapping": "sample_name"},
                    "report": {"id": True},
                }
            }
        }
    }

    dashboard.render_sample_details_tab(pd.DataFrame(columns=["sample_name"]))

    assert streamlit_stub.warning_calls == ["No samples match the current filters."]

    streamlit_stub.reset()
    dashboard.mapping = {}
    dashboard.render_sample_details_tab(pd.DataFrame(columns=["sample_name"]))

    assert streamlit_stub.warning_calls == ["No ID field configured in mapping."]
