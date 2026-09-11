#!/usr/bin/env python3
"""
uQCme Plotting Library

Contains all plotting and visualization functions for the uQCme application.
This module provides reusable plotting components for QC data visualization.

Note: This module requires the 'app' or 'all' extras to be installed:
    pip install uqcme[app]
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Dict, Any, Optional, Iterable, List, Tuple

from uQCme.app.styling import SpeciesSupportStyling
from uQCme.core.config import UQCMeConfig


@dataclass(frozen=True)
class QualityMetricCatalogEntry:
    """A mapped quality metric and whether it can be plotted."""

    label: str
    data_column: str
    rule_fields: Tuple[str, ...]
    section: str
    value_available: bool
    plottable: bool
    non_plottable_reason: str = ""


def _to_numeric_values(values: pd.Series) -> pd.Series:
    """Coerce a column to numeric values, returning NaN for non-numeric data."""
    try:
        return pd.to_numeric(values, errors="coerce")
    except (ValueError, TypeError):
        return pd.Series(pd.NA, index=values.index)


def _coerce_metric_columns(data: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    """Return a plot copy where selected metric columns are numeric."""
    plot_data = data.copy()
    for metric in metrics:
        if metric in plot_data.columns:
            plot_data[metric] = _to_numeric_values(plot_data[metric])
    return plot_data


def _as_list(value) -> list:
    """Normalize scalar/list config values to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique_text_values(values: Iterable[Any]) -> Tuple[str, ...]:
    """Return ordered, non-empty string values."""
    seen = set()
    unique_values = []
    for value in values:
        if value is None or pd.isna(value):
            continue
        value_text = str(value).strip()
        if not value_text or value_text in seen:
            continue
        seen.add(value_text)
        unique_values.append(value_text)
    return tuple(unique_values)


def _metric_column_status(
    data: pd.DataFrame, data_column: str
) -> tuple[bool, bool, str]:
    """Return value availability, plottability, and non-plottable reason."""
    if data_column not in data.columns:
        return False, False, "missing column"

    values = data[data_column]
    has_values = values.notna().any()
    if not has_values:
        return False, False, "all values empty"

    text_values = values.dropna().astype(str).str.strip()
    if not text_values.astype(bool).any():
        return False, False, "all values empty"

    numeric_values = _to_numeric_values(values)
    if numeric_values.notna().any():
        return True, True, ""

    return True, False, "non-numeric/categorical"


def _mapping_metric_metadata(mapping_config: Optional[Dict[str, Any]]) -> dict:
    """Extract mapping metadata used to define quality metrics."""
    metadata = {
        "by_data": {},
        "by_qc": {},
        "included": [],
        "excluded_data": set(),
        "excluded_qc": set(),
    }

    if not mapping_config or "Sections" not in mapping_config:
        return metadata

    for section_name, section_data in mapping_config.get("Sections", {}).items():
        if not isinstance(section_data, dict):
            continue

        for field_name, field_config in section_data.items():
            if not isinstance(field_config, dict):
                continue

            data_mapping = field_config.get("data", {}).get("mapping")
            if not isinstance(data_mapping, str) or not data_mapping:
                continue

            qc_mappings = _as_list(field_config.get("QC", {}).get("mapping"))
            qc_mappings = [
                str(mapping)
                for mapping in qc_mappings
                if mapping is not None and str(mapping).strip()
            ]
            report_config = field_config.get("report", {}) or {}
            quality_metric_flag = report_config.get("quality_metric")
            is_id_field = report_config.get("id") is True
            has_qc_mapping = bool(qc_mappings)
            is_excluded = quality_metric_flag is False or (
                is_id_field and quality_metric_flag is not True
            )
            is_included = quality_metric_flag is True or has_qc_mapping

            item = {
                "label": field_name,
                "data_column": data_mapping,
                "section": section_name,
                "qc_mappings": tuple(qc_mappings),
                "excluded": is_excluded,
                "included": is_included and not is_excluded,
            }

            metadata["by_data"].setdefault(data_mapping, item)
            for qc_mapping in qc_mappings:
                metadata["by_qc"].setdefault(qc_mapping, item)

            if is_excluded:
                metadata["excluded_data"].add(data_mapping)
                metadata["excluded_qc"].update(qc_mappings)
                continue

            if is_included:
                metadata["included"].append(item)

    return metadata


def _metric_key(data_column: str) -> str:
    """Return a stable catalog key for a data column."""
    return data_column


def build_quality_metric_catalog(
    data: pd.DataFrame,
    mapping_config: Optional[Dict[str, Any]] = None,
    qc_rules: Optional[pd.DataFrame] = None,
) -> List[QualityMetricCatalogEntry]:
    """Build quality metric catalog from rules and mapping configuration."""
    mapping_metadata = _mapping_metric_metadata(mapping_config)
    catalog_records: Dict[str, Dict[str, Any]] = {}

    def add_metric(
        *, label: str, data_column: str, section: str, rule_field: Optional[str] = None
    ) -> None:
        if data_column in mapping_metadata["excluded_data"] or (
            rule_field and rule_field in mapping_metadata["excluded_qc"]
        ):
            return
        key = _metric_key(data_column)
        if key not in catalog_records:
            catalog_records[key] = {
                "label": label,
                "data_column": data_column,
                "section": section,
                "rule_fields": [],
            }

        if rule_field and rule_field not in catalog_records[key]["rule_fields"]:
            catalog_records[key]["rule_fields"].append(rule_field)

    if qc_rules is not None and "field" in qc_rules.columns:
        for rule_field in _unique_text_values(qc_rules["field"]):
            mapping_item = mapping_metadata["by_qc"].get(
                rule_field
            ) or mapping_metadata["by_data"].get(rule_field)

            if mapping_item:
                add_metric(
                    label=mapping_item["label"],
                    data_column=mapping_item["data_column"],
                    section=mapping_item["section"],
                    rule_field=rule_field,
                )
            else:
                add_metric(
                    label=rule_field,
                    data_column=rule_field,
                    section="Rules",
                    rule_field=rule_field,
                )

    for mapping_item in mapping_metadata["included"]:
        add_metric(
            label=mapping_item["label"],
            data_column=mapping_item["data_column"],
            section=mapping_item["section"],
        )

    catalog = []
    for record in catalog_records.values():
        value_available, plottable, reason = _metric_column_status(
            data, record["data_column"]
        )
        catalog.append(
            QualityMetricCatalogEntry(
                label=record["label"],
                data_column=record["data_column"],
                rule_fields=tuple(record["rule_fields"]),
                section=record["section"],
                value_available=value_available,
                plottable=plottable,
                non_plottable_reason=reason,
            )
        )

    return catalog


def get_plottable_quality_metric_columns(
    catalog: Iterable[QualityMetricCatalogEntry],
) -> list:
    """Return data columns for metrics that can be plotted."""
    return [entry.data_column for entry in catalog if entry.plottable]


class QCPlotter:
    """Class containing all plotting functionality for QC data visualization."""

    def __init__(self, config: UQCMeConfig):
        """Initialize plotter with configuration."""
        self.config = config
        self.priority_colors = (
            config.app.priority_colors
            if config.app and config.app.priority_colors
            else {}
        )
        self.species_styling = SpeciesSupportStyling(config.app.ui_styling, ())

    def create_outcome_pie_chart(
        self, data: pd.DataFrame, title: str = "QC Outcome Distribution"
    ) -> go.Figure:
        """Create pie chart for QC outcomes distribution."""
        outcome_counts = data["qc_outcome"].value_counts()

        fig = px.pie(
            values=outcome_counts.values,
            names=outcome_counts.index,
            title=title,
            color_discrete_map=self._get_outcome_colors(),
        )

        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, font=dict(size=12))

        return fig

    def create_species_bar_chart(
        self, data: pd.DataFrame, top_n: int = 10, title: str = "Species Distribution"
    ) -> go.Figure:
        """Create horizontal bar chart for species distribution."""
        if "species" not in data.columns:
            return go.Figure()

        species_labels = data["species"].map(self.species_styling.chart_label_for)
        species_counts = species_labels.value_counts().head(top_n)

        fig = px.bar(
            x=species_counts.values,
            y=species_counts.index,
            orientation="h",
            title=f"Top {top_n} {title}",
            labels={"x": "Sample Count", "y": "Species"},
        )

        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=max(400, top_n * 30),
            margin=dict(l=200),
            showlegend=False,
        )

        return fig

    def create_failed_rules_chart(
        self,
        data: pd.DataFrame,
        top_n: int = 15,
        title: str = "Most Common Failed Rules",
    ) -> go.Figure:
        """Create bar chart for failed rules analysis."""
        failed_rules_data = self._analyze_failed_rules(data)

        if failed_rules_data.empty:
            # Create empty chart
            fig = go.Figure()
            fig.add_annotation(
                text="No failed rules found",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16),
            )
            fig.update_layout(title=title)
            return fig

        top_rules = failed_rules_data.head(top_n)

        fig = px.bar(
            top_rules,
            x="count",
            y="rule",
            orientation="h",
            title=f"Top {top_n} {title}",
            labels={"count": "Failure Count", "rule": "QC Rule"},
        )

        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=max(500, top_n * 25),
            margin=dict(l=250),
        )

        return fig

    def create_distribution_plot(
        self, data: pd.DataFrame, metric: str, title: Optional[str] = None
    ) -> go.Figure:
        """Create distribution histogram for a quality metric."""
        plot_data = _coerce_metric_columns(data, [metric])

        if title is None:
            title = f"Distribution of {self._format_column_name(metric)}"

        fig = px.histogram(
            plot_data,
            x=metric,
            color="qc_outcome",
            title=title,
            nbins=30,
            labels={metric: self._format_column_name(metric)},
            color_discrete_map=self._get_outcome_colors(),
        )

        fig.update_layout(
            bargap=0.1,
            xaxis_title=self._format_column_name(metric),
            yaxis_title="Sample Count",
        )

        return fig

    def create_box_plot(
        self, data: pd.DataFrame, metric: str, title: Optional[str] = None
    ) -> go.Figure:
        """Create box plot for a quality metric by QC outcome."""
        plot_data = _coerce_metric_columns(data, [metric])

        if title is None:
            title = f"{self._format_column_name(metric)} by QC Outcome"

        fig = px.box(
            plot_data,
            x="qc_outcome",
            y=metric,
            title=title,
            labels={
                "qc_outcome": "QC Outcome",
                metric: self._format_column_name(metric),
            },
            color="qc_outcome",
            color_discrete_map=self._get_outcome_colors(),
        )

        fig.update_xaxes(tickangle=45)
        fig.update_layout(showlegend=False)

        return fig

    def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x_metric: str,
        y_metric: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Create scatter plot comparing two quality metrics."""
        plot_data = _coerce_metric_columns(data, [x_metric, y_metric])

        if title is None:
            x_name = self._format_column_name(x_metric)
            y_name = self._format_column_name(y_metric)
            title = f"{x_name} vs {y_name}"

        # Determine which columns to include in hover_data
        hover_cols = [
            column
            for column in ["sample_name", "species"]
            if column in plot_data.columns
        ]

        fig = px.scatter(
            plot_data,
            x=x_metric,
            y=y_metric,
            color="qc_outcome",
            title=title,
            labels={
                x_metric: self._format_column_name(x_metric),
                y_metric: self._format_column_name(y_metric),
            },
            hover_data=hover_cols,
            color_discrete_map=self._get_outcome_colors(),
        )

        fig.update_layout(
            xaxis_title=self._format_column_name(x_metric),
            yaxis_title=self._format_column_name(y_metric),
        )

        return fig

    def create_correlation_heatmap(
        self,
        data: pd.DataFrame,
        metrics: list,
        title: str = "Quality Metrics Correlation",
    ) -> go.Figure:
        """Create correlation heatmap for quality metrics."""
        # Filter to only include available numeric columns
        available_metrics = [col for col in metrics if col in data.columns]

        if len(available_metrics) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="Not enough numeric metrics for correlation analysis",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16),
            )
            fig.update_layout(title=title)
            return fig

        plot_data = _coerce_metric_columns(data, available_metrics)

        # Calculate correlation matrix
        corr_matrix = plot_data[available_metrics].corr()

        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title=title,
            color_continuous_scale="RdBu",
            range_color=[-1, 1],
        )

        fig.update_layout(xaxis_title="Metrics", yaxis_title="Metrics")

        return fig

    def create_quality_overview_dashboard(
        self, data: pd.DataFrame, metrics: Optional[list] = None
    ) -> Dict[str, go.Figure]:
        """Create a set of overview plots for dashboard display."""
        plots = {}

        # Outcome distribution
        plots["outcome_pie"] = self.create_outcome_pie_chart(data)

        # Species distribution
        plots["species_bar"] = self.create_species_bar_chart(data)

        # Failed rules analysis
        plots["failed_rules"] = self.create_failed_rules_chart(data)

        # Quality metrics
        available_cols = metrics if metrics is not None else get_available_metrics(data)

        if available_cols:
            # Distribution of first available metric
            plots["metric_dist"] = self.create_distribution_plot(
                data, available_cols[0]
            )

            # Box plot of first available metric
            plots["metric_box"] = self.create_box_plot(data, available_cols[0])

            # Correlation heatmap if multiple metrics available
            if len(available_cols) > 1:
                plots["correlation"] = self.create_correlation_heatmap(
                    data, available_cols
                )

        return plots

    def _analyze_failed_rules(self, data: pd.DataFrame) -> pd.DataFrame:
        """Analyze failed rules to get counts."""
        failed_rules_counts = {}

        for failed_rules_str in data["failed_rules"]:
            if pd.notna(failed_rules_str) and failed_rules_str:
                rules = failed_rules_str.split(",")
                for rule in rules:
                    rule = rule.strip()
                    current_count = failed_rules_counts.get(rule, 0)
                    failed_rules_counts[rule] = current_count + 1

        if failed_rules_counts:
            items_list = list(failed_rules_counts.items())
            df = pd.DataFrame(items_list, columns=["rule", "count"])
            return df.sort_values("count", ascending=False)
        else:
            return pd.DataFrame(columns=["rule", "count"])

    def _format_column_name(self, col_name: str) -> str:
        """Format column name for display."""
        # Handle common patterns and return human-readable names
        # Remove common prefixes
        display_name = col_name
        for prefix in ["QC/", "QC.", "QC_"]:
            if display_name.startswith(prefix):
                display_name = display_name[len(prefix) :]
                break

        # Replace underscores and format
        display_name = display_name.replace("_", " ").title()
        return display_name

    def _get_outcome_colors(self) -> Dict[str, str]:
        """Get color mapping for QC outcomes."""
        default_colors = {
            "PASS": "#28a745",  # Green
            "WARN": "#ffc107",  # Yellow
            "FAIL": "#dc3545",  # Red
            "WARN_COMPLETENESS": "#fd7e14",  # Orange
            "WARN_CONTAMINATION": "#e83e8c",  # Pink
            "FAIL_SIZE": "#6f42c1",  # Purple
            "FAIL_CONTIGUITY": "#20c997",  # Teal
        }

        # Override with config colors if available
        config_colors = self.priority_colors.get("qc_outcome", {})
        default_colors.update(config_colors)

        return default_colors


def get_available_metrics(
    data: pd.DataFrame, mapping_config: Optional[Dict[str, Any]] = None
) -> list:
    """Get available numeric metrics, excluding mapping-defined non-metrics."""
    excluded_columns = _mapping_metric_metadata(mapping_config)["excluded_data"]
    available_metrics = []
    for col in data.columns:
        if col in excluded_columns:
            continue

        numeric_values = _to_numeric_values(data[col])
        if numeric_values.notna().any():
            available_metrics.append(col)

    return available_metrics


def validate_metric_for_plotting(
    data: pd.DataFrame, metric: str, mapping_config: Optional[Dict[str, Any]] = None
) -> bool:
    """Validate that a metric can be used for plotting."""
    excluded_columns = _mapping_metric_metadata(mapping_config)["excluded_data"]
    if metric not in data.columns or metric in excluded_columns:
        return False

    # Check if column has numeric data
    numeric_values = _to_numeric_values(data[metric])
    return bool(numeric_values.notna().any())
