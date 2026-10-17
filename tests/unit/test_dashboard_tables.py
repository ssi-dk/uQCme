import importlib

import pandas as pd

from tests.support.dashboard import _bare_dashboard, _dashboard_with_presets

dashboard_main = importlib.import_module("uQCme.app.main")


def test_styled_dataframe_uses_configured_table_height(streamlit_stub):
    """The main sample table should cap height at the configured maximum."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(table_height=4200)
    data = pd.DataFrame(
        [{"sample_name": f"S{i}", "qc_outcome": "PASS"} for i in range(200)]
    )

    dashboard._render_styled_dataframe(
        data,
        ["sample_name", "qc_outcome"],
        "data_preview_table",
    )

    assert len(streamlit_stub.data_editor_calls) == 1
    _, kwargs = streamlit_stub.data_editor_calls[0]
    assert kwargs["height"] == 4200


def test_styled_dataframe_shrinks_when_rows_are_below_configured_height(streamlit_stub):
    """The sample table should not leave empty space for small datasets."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(table_height=4200)
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
            {"sample_name": "S2", "qc_outcome": "FAIL"},
        ]
    )

    dashboard._render_styled_dataframe(
        data,
        ["sample_name", "qc_outcome"],
        "data_preview_table",
    )

    assert len(streamlit_stub.data_editor_calls) == 1
    _, kwargs = streamlit_stub.data_editor_calls[0]
    assert kwargs["height"] == 114


def test_styled_dataframe_composes_species_and_qc_action_colors(streamlit_stub):
    """Species support cues should coexist with QC action text styling."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(
        ui_styling={
            "unsupported_species_color_light": "#123456",
            "unsupported_species_color_dark": "#654321",
            "missing_species_color": "#ABCDEF",
            "missing_species_opacity": 0.25,
        }
    )
    dashboard.qc_rules = pd.DataFrame({"species": ["all", "Escherichia coli"]})
    data = pd.DataFrame(
        [
            {
                "species": "Escherichia coli",
                "qc_action": "none",
            },
            {
                "species": "Salmonella enterica",
                "qc_action": "review",
            },
            {
                "species": None,
                "qc_action": "reject",
            },
        ]
    )

    dashboard._render_styled_dataframe(
        data,
        ["species", "qc_action"],
        "species_styling_table",
    )

    styled_data, _ = streamlit_stub.data_editor_calls[0]
    rendered_html = styled_data.to_html()
    assert "light-dark(#123456, #654321)" in rendered_html
    assert "background-color: rgba(171, 205, 239, 0.25)" in rendered_html
    assert ">—<" in rendered_html
    assert "text-shadow: 0 0 3px #00AA00" in rendered_html


def test_styled_dataframe_treats_configured_species_alias_as_supported(streamlit_stub):
    """Configured short species names should not receive unsupported styling."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(
        ui_styling={
            "unsupported_species_color_light": "#123456",
            "unsupported_species_color_dark": "#654321",
            "missing_species_color": "#ABCDEF",
            "missing_species_opacity": 0.25,
        }
    )
    dashboard.mapping = {"SpeciesAliases": {"Escherichia coli": ["E. coli"]}}
    dashboard.qc_rules = pd.DataFrame({"species": ["all", "Escherichia coli"]})
    data = pd.DataFrame(
        {
            "species": ["E. coli", "Escherichia coli", "Unmapped species"],
        }
    )

    dashboard._render_styled_dataframe(
        data,
        ["species"],
        "species_alias_styling_table",
    )

    styled_data, _ = streamlit_stub.data_editor_calls[0]
    styled_data._compute()
    species_column = styled_data.data.columns.get_loc("species")
    assert styled_data.ctx[(0, species_column)] == []
    assert styled_data.ctx[(1, species_column)] == []
    assert styled_data.ctx[(2, species_column)]


def test_supported_species_come_from_explicit_species_rules():
    """General rules should not mark arbitrary species as supported."""
    dashboard = _bare_dashboard()
    dashboard.qc_rules = pd.DataFrame(
        {
            "species": [
                "all",
                "ALL",
                " Escherichia coli ",
                "Klebsiella pneumoniae",
                None,
                "",
            ]
        }
    )

    assert dashboard._get_supported_species() == {
        "Escherichia coli",
        "Klebsiella pneumoniae",
    }


def test_report_table_applies_species_support_styling(streamlit_stub):
    """Static report tables should use the same species support cues."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard(
        ui_styling={
            "unsupported_species_color_light": "#123456",
            "unsupported_species_color_dark": "#654321",
            "missing_species_color": "#ABCDEF",
            "missing_species_opacity": 0.25,
        }
    )
    dashboard.mapping = {"SpeciesAliases": {"Escherichia coli": ["E. coli"]}}
    dashboard.qc_rules = pd.DataFrame({"species": ["all", "Escherichia coli"]})
    data = pd.DataFrame(
        {
            "species": ["E. coli", "Unmapped species", ""],
            "qc_action": ["none", "review", "reject"],
        }
    )

    dashboard.render_report_tab(data)

    report_html = streamlit_stub.markdown_calls[-1][0]
    assert 'class="uqcme-report-table"' in report_html
    assert report_html.count("light-dark(#123456, #654321)") == 1
    assert "background-color: rgba(171, 205, 239, 0.25)" in report_html
    assert ">—<" in report_html


def test_explicit_other_section_mappings_are_preserved_with_unmapped_columns():
    """Explicit Other mappings should keep descriptions and section ordering."""
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Other": {
                "Contigs Path": {
                    "data": {"mapping": "shovil_contigs_path"},
                    "report": {"description": "Path to assembled contigs."},
                },
                "unmapped": True,
            }
        }
    }
    data = pd.DataFrame(
        [
            {
                "shovil_contigs_path": "/tmp/contigs.fa",
                "extra_column": "extra",
            }
        ]
    )

    sections = dashboard._get_columns_by_section(data)

    assert [col["column"] for col in sections["Other"]] == [
        "shovil_contigs_path",
        "extra_column",
    ]
    assert (
        dashboard._get_column_description("shovil_contigs_path")
        == "Path to assembled contigs."
    )


def test_data_tab_renders_column_view_above_table(streamlit_stub):
    streamlit_stub.reset()
    dashboard = _dashboard_with_presets()

    dashboard.render_data_tab(dashboard.data)

    assert "subheader:Column View" in streamlit_stub.events
    assert "data_editor" in streamlit_stub.events

    assert streamlit_stub.events.index(
        "subheader:Column View"
    ) < streamlit_stub.events.index("data_editor")

    rendered_data, _ = streamlit_stub.data_editor_calls[0]

    assert list(rendered_data.columns) == ["sample_name"]


def test_ordered_columns_deduplicate_reused_mapping_columns():
    # Repeated mappings should not create duplicate dataframe columns.
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "QC_metrics": {
                "Provided Species": {"data": {"mapping": "species"}},
                "Species": {"data": {"mapping": "species"}},
            }
        }
    }
    data = pd.DataFrame({"species": ["Escherichia coli"]})

    ordered_columns = dashboard._get_ordered_columns_with_sections(
        data, {"QC_metrics": True}
    )

    assert ordered_columns == ["species"]


def test_data_tab_omits_section_visibility_in_report_mode(streamlit_stub):
    """Report mode should keep its table-only data view."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.report_mode = True
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
        ]
    )
    dashboard.data = data

    dashboard.render_data_tab(data)

    assert "dataframe" in streamlit_stub.events
    assert "subheader:Section Visibility" not in streamlit_stub.events
    assert "pills:Visible sections" not in streamlit_stub.events


def test_column_view_uses_custom_column_selection(streamlit_stub):
    streamlit_stub.reset()
    dashboard = _dashboard_with_presets()

    streamlit_stub.session_state["data_preview_active_preset"] = None
    streamlit_stub.session_state["data_preview_visible_columns"] = ["qc_outcome"]

    dashboard.render_data_tab(dashboard.data)

    rendered_data, _ = streamlit_stub.data_editor_calls[0]

    assert list(rendered_data.columns) == ["qc_outcome"]


def test_column_view_rejects_empty_custom_selection(streamlit_stub):
    streamlit_stub.reset()
    dashboard = _dashboard_with_presets()

    dashboard.render_data_tab(dashboard.data)

    streamlit_stub.session_state["data_preview_custom_columns_Basic"] = []
    streamlit_stub.session_state["data_preview_custom_columns_QC"] = []
    streamlit_stub.form_submitted = True

    streamlit_stub.data_editor_calls.clear()
    streamlit_stub.warning_calls.clear()

    dashboard.render_data_tab(dashboard.data)

    assert "Select at least one column." in streamlit_stub.warning_calls

    rendered_data, _ = streamlit_stub.data_editor_calls[0]

    assert list(rendered_data.columns) == ["sample_name"]


def test_quality_metrics_tab_lists_non_plottable_catalog_entries(streamlit_stub):
    """Non-plottable quality metrics should be listed with reasons."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "Read_QC": {
                "Categorical Metric": {
                    "data": {"mapping": "categorical_metric"},
                    "QC": {"mapping": "CategoricalField"},
                },
                "Empty Metric": {
                    "data": {"mapping": "empty_metric"},
                    "QC": {"mapping": "EmptyField"},
                },
                "Missing Metric": {
                    "data": {"mapping": "missing_metric"},
                    "QC": {"mapping": "MissingField"},
                },
            }
        }
    }
    dashboard.qc_rules = pd.DataFrame(
        [
            {"field": "CategoricalField"},
            {"field": "EmptyField"},
            {"field": "MissingField"},
        ]
    )
    data = pd.DataFrame(
        [
            {
                "sample_name": "S1",
                "categorical_metric": "high",
                "empty_metric": None,
            }
        ]
    )

    dashboard.render_quality_metrics_tab(data)

    assert "Quality metrics omitted from plots" in streamlit_stub.info_calls
    assert (
        "No plottable quality metrics available for visualization."
        in streamlit_stub.warning_calls
    )
    assert len(streamlit_stub.dataframe_calls) == 1
    omitted_table, _ = streamlit_stub.dataframe_calls[0]
    reasons = dict(zip(omitted_table["Metric"], omitted_table["Reason"]))
    assert reasons == {
        "Categorical Metric": "non-numeric/categorical",
        "Empty Metric": "all values empty",
        "Missing Metric": "missing column",
    }



def test_column_information_preserves_legacy_explanations(streamlit_stub):
    dashboard = _bare_dashboard()
    dashboard.mapping = {"Sections": {"Metrics": {
        "Depth": {"data": {"mapping": "depth"}, "QC": {"description": "Legacy depth explanation"}},
    }}}
    dashboard.render_data_tab(pd.DataFrame({"depth": [20], "unmapped": [1]}))
    information = "\n".join(str(value) for value in streamlit_stub.write_calls)
    assert "Legacy depth explanation" in information
    assert not any(line.endswith(" - ") for line in information.splitlines())
