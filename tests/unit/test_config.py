#!/usr/bin/env python3
"""Unit tests for configuration models."""

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

# Add src directory to import path.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.config import UQCMeConfig


class TestConfigModels(unittest.TestCase):
    """Tests for dashboard API action configuration."""

    def test_sample_api_action_method_is_normalized(self):
        """Method names in sample API actions are normalized to uppercase."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {"file": "output/qc_results.tsv"},
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                },
                "dashboard": {
                    "sample_api_actions": [
                        {
                            "label": "Notify",
                            "api_call": "https://example.org/api/notify",
                            "value_field": "sample_name",
                            "method": "post",
                        }
                    ]
                },
            }
        )

        action = config.app.dashboard.sample_api_actions[0]
        self.assertEqual(action.method, "POST")

    def test_sample_api_action_rejects_invalid_method(self):
        """Invalid HTTP methods in sample API actions fail validation."""
        with self.assertRaises(ValidationError):
            UQCMeConfig(
                app={
                    "input": {
                        "data": {"file": "output/qc_results.tsv"},
                        "mapping": "config/mapping.yaml",
                        "qc_rules": "config/QC_rules.tsv",
                        "qc_tests": "config/QC_tests.tsv",
                    },
                    "dashboard": {
                        "sample_api_actions": [
                            {
                                "label": "BadMethod",
                                "api_call": "https://example.org/api/notify",
                                "value_field": "sample_name",
                                "method": "TRACE",
                            }
                        ]
                    },
                }
            )

    def test_report_mode_config_defaults_and_overrides(self):
        """Report mode config should parse default and custom values."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {"file": "output/qc_results.tsv"},
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                },
                "dashboard": {
                    "report_mode": {
                        "enabled": True,
                        "default_visible_sections": {
                            "Basic": True,
                            "Experimental": False
                        },
                        "default_filters": {
                            "species": "Escherichia coli",
                            "completeness": {"min": 90}
                        }
                    }
                },
            }
        )

        report_mode = config.app.dashboard.report_mode
        self.assertTrue(report_mode.enabled)
        self.assertFalse(report_mode.default_visible_sections["Experimental"])
        self.assertEqual(
            report_mode.default_filters["species"], "Escherichia coli"
        )

    def test_data_input_supports_api_bearer_token_fields(self):
        """Data input config should parse bearer token auth fields."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {
                        "api_call": "https://example.org/api/data",
                        "api_bearer_token": "test-token",
                        "api_bearer_token_env": "UQCME_API_TOKEN",
                        "api_headers": {
                            "X-Project-Id": "project-123"
                        },
                    },
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                }
            }
        )

        data_input = config.app.input.data
        self.assertEqual(data_input.api_bearer_token, "test-token")
        self.assertEqual(data_input.api_bearer_token_env, "UQCME_API_TOKEN")
        self.assertEqual(
            data_input.api_headers["X-Project-Id"], "project-123"
        )

    def test_sample_api_action_supports_bearer_token_fields(self):
        """Sample API actions should parse bearer token auth fields."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {"file": "output/qc_results.tsv"},
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                },
                "dashboard": {
                    "sample_api_actions": [
                        {
                            "label": "Notify",
                            "api_call": "https://example.org/api/notify",
                            "value_field": "sample_name",
                            "api_bearer_token": "test-token",
                            "api_bearer_token_env": "UQCME_ACTION_TOKEN",
                        }
                    ]
                },
            }
        )

        action = config.app.dashboard.sample_api_actions[0]
        self.assertEqual(action.api_bearer_token, "test-token")
        self.assertEqual(action.api_bearer_token_env, "UQCME_ACTION_TOKEN")


if __name__ == "__main__":
    unittest.main()
