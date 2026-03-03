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


if __name__ == "__main__":
    unittest.main()
