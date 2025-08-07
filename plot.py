#!/usr/bin/env python3
"""
uQCme Plotting Library

Contains all plotting and visualization functions for the uQCme application.
This module provides reusable plotting components for QC data visualization.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional


class QCPlotter:
    """Class containing all plotting functionality for QC data visualization."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize plotter with configuration."""
        self.config = config
        self.priority_colors = config.get('priority_colors', {})

    def create_outcome_pie_chart(
        self,
        data: pd.DataFrame,
        title: str = "QC Outcome Distribution"
    ) -> go.Figure:
        """Create pie chart for QC outcomes distribution."""
        outcome_counts = data['qc_outcome'].value_counts()
        
        fig = px.pie(
            values=outcome_counts.values,
            names=outcome_counts.index,
            title=title,
            color_discrete_map=self._get_outcome_colors()
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            showlegend=True,
            font=dict(size=12)
        )
        
        return fig

    def create_species_bar_chart(
        self,
        data: pd.DataFrame,
        top_n: int = 10,
        title: str = "Species Distribution"
    ) -> go.Figure:
        """Create horizontal bar chart for species distribution."""
        species_counts = data['species'].value_counts().head(top_n)
        
        fig = px.bar(
            x=species_counts.values,
            y=species_counts.index,
            orientation='h',
            title=f"Top {top_n} {title}",
            labels={'x': 'Sample Count', 'y': 'Species'}
        )
        
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=max(400, top_n * 30),
            margin=dict(l=200)
        )
        
        return fig

    def create_failed_rules_chart(
        self,
        data: pd.DataFrame,
        top_n: int = 15,
        title: str = "Most Common Failed Rules"
    ) -> go.Figure:
        """Create bar chart for failed rules analysis."""
        failed_rules_data = self._analyze_failed_rules(data)
        
        if failed_rules_data.empty:
            # Create empty chart
            fig = go.Figure()
            fig.add_annotation(
                text="No failed rules found",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(title=title)
            return fig
        
        top_rules = failed_rules_data.head(top_n)
        
        fig = px.bar(
            top_rules,
            x='count',
            y='rule',
            orientation='h',
            title=f"Top {top_n} {title}",
            labels={'count': 'Failure Count', 'rule': 'QC Rule'}
        )
        
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=max(500, top_n * 25),
            margin=dict(l=250)
        )
        
        return fig

    def create_distribution_plot(
        self,
        data: pd.DataFrame,
        metric: str,
        title: Optional[str] = None
    ) -> go.Figure:
        """Create distribution histogram for a quality metric."""
        if title is None:
            title = f"Distribution of {self._format_column_name(metric)}"
        
        fig = px.histogram(
            data,
            x=metric,
            color='qc_outcome',
            title=title,
            nbins=30,
            labels={metric: self._format_column_name(metric)},
            color_discrete_map=self._get_outcome_colors()
        )
        
        fig.update_layout(
            bargap=0.1,
            xaxis_title=self._format_column_name(metric),
            yaxis_title="Sample Count"
        )
        
        return fig

    def create_box_plot(
        self,
        data: pd.DataFrame,
        metric: str,
        title: Optional[str] = None
    ) -> go.Figure:
        """Create box plot for a quality metric by QC outcome."""
        if title is None:
            title = f"{self._format_column_name(metric)} by QC Outcome"
        
        fig = px.box(
            data,
            x='qc_outcome',
            y=metric,
            title=title,
            labels={
                'qc_outcome': 'QC Outcome',
                metric: self._format_column_name(metric)
            },
            color='qc_outcome',
            color_discrete_map=self._get_outcome_colors()
        )
        
        fig.update_xaxes(tickangle=45)
        fig.update_layout(showlegend=False)
        
        return fig

    def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x_metric: str,
        y_metric: str,
        title: Optional[str] = None
    ) -> go.Figure:
        """Create scatter plot comparing two quality metrics."""
        if title is None:
            x_name = self._format_column_name(x_metric)
            y_name = self._format_column_name(y_metric)
            title = f"{x_name} vs {y_name}"
        
        fig = px.scatter(
            data,
            x=x_metric,
            y=y_metric,
            color='qc_outcome',
            title=title,
            labels={
                x_metric: self._format_column_name(x_metric),
                y_metric: self._format_column_name(y_metric)
            },
            hover_data=['sample_name', 'species'],
            color_discrete_map=self._get_outcome_colors()
        )
        
        fig.update_layout(
            xaxis_title=self._format_column_name(x_metric),
            yaxis_title=self._format_column_name(y_metric)
        )
        
        return fig

    def create_correlation_heatmap(
        self,
        data: pd.DataFrame,
        metrics: list,
        title: str = "Quality Metrics Correlation"
    ) -> go.Figure:
        """Create correlation heatmap for quality metrics."""
        # Filter to only include available numeric columns
        available_metrics = [col for col in metrics if col in data.columns]
        
        if len(available_metrics) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="Not enough numeric metrics for correlation analysis",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(title=title)
            return fig
        
        # Calculate correlation matrix
        corr_matrix = data[available_metrics].corr()
        
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            aspect="auto",
            title=title,
            color_continuous_scale="RdBu",
            range_color=[-1, 1]
        )
        
        fig.update_layout(
            xaxis_title="Metrics",
            yaxis_title="Metrics"
        )
        
        return fig

    def create_quality_overview_dashboard(
        self, data: pd.DataFrame
    ) -> Dict[str, go.Figure]:
        """Create a set of overview plots for dashboard display."""
        plots = {}
        
        # Outcome distribution
        plots['outcome_pie'] = self.create_outcome_pie_chart(data)
        
        # Species distribution
        plots['species_bar'] = self.create_species_bar_chart(data)
        
        # Failed rules analysis
        plots['failed_rules'] = self.create_failed_rules_chart(data)
        
        # Quality metrics (if available)
        numeric_cols = ['GC', 'N50', 'bin_length_at_1x', 'filtered_reads_num']
        available_cols = [col for col in numeric_cols if col in data.columns]
        
        if available_cols:
            # Distribution of first available metric
            plots['metric_dist'] = self.create_distribution_plot(
                data, available_cols[0]
            )
            
            # Box plot of first available metric
            plots['metric_box'] = self.create_box_plot(
                data, available_cols[0]
            )
            
            # Correlation heatmap if multiple metrics available
            if len(available_cols) > 1:
                plots['correlation'] = self.create_correlation_heatmap(
                    data, available_cols
                )
        
        return plots

    def _analyze_failed_rules(self, data: pd.DataFrame) -> pd.DataFrame:
        """Analyze failed rules to get counts."""
        failed_rules_counts = {}
        
        for failed_rules_str in data['failed_rules']:
            if pd.notna(failed_rules_str) and failed_rules_str:
                rules = failed_rules_str.split(',')
                for rule in rules:
                    rule = rule.strip()
                    current_count = failed_rules_counts.get(rule, 0)
                    failed_rules_counts[rule] = current_count + 1
        
        if failed_rules_counts:
            items_list = list(failed_rules_counts.items())
            df = pd.DataFrame(items_list, columns=['rule', 'count'])
            return df.sort_values('count', ascending=False)
        else:
            return pd.DataFrame(columns=['rule', 'count'])

    def _format_column_name(self, col_name: str) -> str:
        """Format column name for display."""
        name_mapping = {
            'GC': 'GC Content (%)',
            'N50': 'N50 (bp)',
            'bin_length_at_1x': 'Genome Size (bp)',
            'filtered_reads_num': 'Filtered Reads Count',
            'completeness': 'Completeness (%)',
            'contamination': 'Contamination (%)',
            'contigs': 'Contig Count',
            'largest_contig': 'Largest Contig (bp)',
            'total_length': 'Total Length (bp)'
        }
        return name_mapping.get(col_name, col_name.replace('_', ' ').title())

    def _get_outcome_colors(self) -> Dict[str, str]:
        """Get color mapping for QC outcomes."""
        default_colors = {
            'PASS': '#28a745',  # Green
            'WARN': '#ffc107',  # Yellow
            'FAIL': '#dc3545',  # Red
            'WARN_COMPLETENESS': '#fd7e14',  # Orange
            'WARN_CONTAMINATION': '#e83e8c',  # Pink
            'FAIL_SIZE': '#6f42c1',  # Purple
            'FAIL_CONTIGUITY': '#20c997'  # Teal
        }
        
        # Override with config colors if available
        config_colors = self.priority_colors.get('qc_outcome', {})
        default_colors.update(config_colors)
        
        return default_colors


def get_available_metrics(data: pd.DataFrame) -> list:
    """Get list of available numeric metrics for plotting."""
    potential_metrics = [
        'GC', 'N50', 'bin_length_at_1x', 'filtered_reads_num',
        'completeness', 'contamination', 'contigs',
        'largest_contig', 'total_length'
    ]
    
    return [col for col in potential_metrics if col in data.columns]


def validate_metric_for_plotting(data: pd.DataFrame, metric: str) -> bool:
    """Validate that a metric can be used for plotting."""
    if metric not in data.columns:
        return False
    
    # Check if column has numeric data
    try:
        pd.to_numeric(data[metric], errors='coerce')
        return True
    except (ValueError, TypeError):
        return False
