import importlib

import pandas as pd

from tests.support.dashboard import _ContextStub, _bare_dashboard

dashboard_main = importlib.import_module("uQCme.app.main")


def test_sidebar_summary_stays_at_top_of_left_panel(streamlit_stub):
    """Summary metrics should render in the sidebar above filter controls."""
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    data = pd.DataFrame(
        [
            {"sample_name": "S1", "qc_outcome": "PASS"},
            {"sample_name": "S2", "qc_outcome": "FAIL"},
        ]
    )
    dashboard.data = data

    dashboard.render_sidebar_filters()

    summary_event = "sidebar.container.subheader:📊 Summary"
    filters_event = "sidebar.header:🔍 Filters"
    assert summary_event in streamlit_stub.events
    assert filters_event in streamlit_stub.events
    assert "subheader:📊 Summary" not in streamlit_stub.events
    assert streamlit_stub.events.index(summary_event) < streamlit_stub.events.index(
        filters_event
    )


def test_filterable_fields_deduplicates_reused_data_columns():
    """Duplicate mapped columns should not create duplicate Streamlit keys."""
    dashboard = _bare_dashboard()
    dashboard.mapping = {
        "Sections": {
            "uQCme": {
                "rMLST Match": {
                    "data": {"mapping": "rMLST_match"},
                    "report": {"filter": True},
                },
            },
            "QC_metrics": {
                "Expected species": {
                    "data": {"mapping": "rMLST_match"},
                    "report": {"filter": True},
                },
                "GC": {
                    "data": {"mapping": "Quast_GC_Pct"},
                    "report": {"filter": True},
                },
            },
        }
    }
    data = pd.DataFrame(
        [
            {"rMLST_match": "E. coli", "Quast_GC_Pct": 50.1},
            {"rMLST_match": "S. aureus", "Quast_GC_Pct": 32.9},
        ]
    )

    fields = dashboard._get_filterable_fields(data)

    assert [field["column"] for field in fields] == [
        "rMLST_match",
        "Quast_GC_Pct",
    ]
    assert fields[0]["field_name"] == "rMLST Match"


def test_run_sorts_filtered_data_before_report_rendering(streamlit_stub):
    # Report mode should receive the same sorted rows as other dashboard views.
    streamlit_stub.reset()
    dashboard = _bare_dashboard()
    dashboard.report_mode = True
    dashboard.data = pd.DataFrame(
        [
            {"sample_name": "Sample-10"},
            {"sample_name": "Sample-2"},
        ]
    )
    filtered_data = dashboard.data.iloc[[0, 1]].copy()
    rendered_data = []
    dashboard.setup_page = lambda: None
    dashboard.load_data = lambda: None
    dashboard.render_header = lambda: None
    dashboard._render_api_debug_panel = lambda: None
    dashboard.render_sidebar_filters = lambda: filtered_data
    dashboard.render_report_tab = lambda data: rendered_data.append(data)

    dashboard.run()

    assert list(rendered_data[0]["sample_name"]) == ["Sample-2", "Sample-10"]
    assert list(dashboard.data["sample_name"]) == ["Sample-10", "Sample-2"]


def test_run_sorts_filtered_data_before_interactive_views(streamlit_stub, monkeypatch):
    # Every interactive view should receive the same post-filter ordering.
    class RunSidebarStub(_ContextStub):
        def subheader(self, message):
            return None

        def markdown(self, message, **kwargs):
            return None

    class PlaceholderStub:
        def info(self, message):
            return None

    streamlit_stub.reset()
    monkeypatch.setattr(streamlit_stub, "sidebar", RunSidebarStub())
    monkeypatch.setattr(
        streamlit_stub,
        "empty",
        lambda: PlaceholderStub(),
        raising=False,
    )
    monkeypatch.setattr(
        streamlit_stub,
        "expander",
        lambda *args, **kwargs: _ContextStub(),
        raising=False,
    )
    monkeypatch.setattr(
        streamlit_stub,
        "file_uploader",
        lambda *args, **kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        streamlit_stub,
        "tabs",
        lambda labels: [_ContextStub() for _ in labels],
        raising=False,
    )

    dashboard = _bare_dashboard()
    dashboard.data = pd.DataFrame(
        [
            {"sample_name": "Sample-10"},
            {"sample_name": "Sample-2"},
        ]
    )
    filtered_data = dashboard.data.iloc[[0, 1]].copy()
    rendered_data = []
    dashboard.setup_page = lambda: None
    dashboard.load_data = lambda: None
    dashboard.render_header = lambda: None
    dashboard._render_api_debug_panel = lambda: None
    dashboard.render_sidebar_filters = lambda: filtered_data
    for method_name in [
        "render_data_tab",
        "render_overview_tab",
        "render_quality_metrics_tab",
        "render_sample_details_tab",
    ]:
        setattr(
            dashboard,
            method_name,
            lambda data, method_name=method_name: rendered_data.append(
                (method_name, list(data["sample_name"]))
            ),
        )
    dashboard.render_qc_tests_tab = lambda: None
    dashboard.render_warnings_tab = lambda: None

    dashboard.run()

    assert rendered_data == [
        ("render_data_tab", ["Sample-2", "Sample-10"]),
        ("render_overview_tab", ["Sample-2", "Sample-10"]),
        ("render_quality_metrics_tab", ["Sample-2", "Sample-10"]),
        ("render_sample_details_tab", ["Sample-2", "Sample-10"]),
    ]
