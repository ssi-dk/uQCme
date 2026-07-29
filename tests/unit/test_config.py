#!/usr/bin/env python3
"""Unit tests for configuration models."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

# Add src directory to import path.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from uQCme.core.config import (
    APIDataSource,
    RawDataInput,
    TSVDataSource,
    UQCMeConfig,
    normalize_data_input,
)
from uQCme.core.exceptions import ConfigError


class TestConfigModels(unittest.TestCase):
    """Tests for dashboard API action configuration."""

    def test_sample_api_action_method_is_normalized(self):
        """Method names in sample API actions are normalized to uppercase."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": RawDataInput(file="output/qc_results.tsv"),
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
                        "data": RawDataInput(file="output/qc_results.tsv"),
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
                    "data": RawDataInput(file="output/qc_results.tsv"),
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                },
                "dashboard": {
                    "report_mode": {
                        "enabled": True,
                        "default_visible_sections": {
                            "Basic": True,
                            "Experimental": False,
                        },
                        "default_filters": {
                            "species": "Escherichia coli",
                            "completeness": {"min": 90},
                        },
                    }
                },
            }
        )

        report_mode = config.app.dashboard.report_mode
        self.assertTrue(report_mode.enabled)
        self.assertFalse(report_mode.default_visible_sections["Experimental"])
        self.assertEqual(report_mode.default_filters["species"], "Escherichia coli")

    def test_dashboard_table_height_defaults_and_overrides(self):
        """Dashboard table height should default to a 100-row viewport."""
        base_input = {
            "data": RawDataInput(file="output/qc_results.tsv"),
            "mapping": "config/mapping.yaml",
            "qc_rules": "config/QC_rules.tsv",
            "qc_tests": "config/QC_tests.tsv",
        }

        default_config = UQCMeConfig(app={"input": base_input})
        custom_config = UQCMeConfig(
            app={
                "input": base_input,
                "dashboard": {"table_height": 4200},
            }
        )

        self.assertEqual(default_config.app.dashboard.table_height, 3600)
        self.assertEqual(custom_config.app.dashboard.table_height, 4200)

    def test_qc_output_paths_are_path_objects(self):
        """QC input and output file paths should parse to Path instances."""
        config = UQCMeConfig(
            qc={
                "input": {
                    "data": RawDataInput(file="input/run_data.tsv"),
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                },
                "output": {
                    "results": "output/qc_results.tsv",
                    "warnings": "output/qc_warnings.tsv",
                },
            }
        )

        self.assertEqual(config.qc.input.mapping, Path("config/mapping.yaml"))
        self.assertEqual(config.qc.input.qc_rules, Path("config/QC_rules.tsv"))
        self.assertEqual(config.qc.input.qc_tests, Path("config/QC_tests.tsv"))
        self.assertEqual(config.qc.output.results, Path("output/qc_results.tsv"))
        self.assertEqual(config.qc.output.warnings, Path("output/qc_warnings.tsv"))

    def test_log_file_is_path_object(self):
        """Log file paths should parse to Path instances."""
        default_config = UQCMeConfig()
        custom_config = UQCMeConfig(log={"file": "logs/uqcme.log"})

        self.assertEqual(default_config.log.file, Path("uqcme.log"))
        self.assertEqual(custom_config.log.file, Path("logs/uqcme.log"))

    def test_data_input_supports_api_bearer_token_fields(self):
        """Data input config should parse bearer token auth fields."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {
                        "api_call": "https://example.org/api/data",
                        "api_bearer_token": "test-token",
                        "api_bearer_token_env": "UQCME_API_TOKEN",
                        "api_headers": {"X-Project-Id": "project-123"},
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
        self.assertEqual(data_input.api_headers["X-Project-Id"], "project-123")

    def test_data_input_config_loads_raw_yaml_shape(self):
        """Config parsing keeps the boundary data input shape unvalidated."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": {
                        "file": "output/qc_results.tsv",
                        "api_call": "https://example.org/api/data",
                    },
                    "mapping": "config/mapping.yaml",
                    "qc_rules": "config/QC_rules.tsv",
                    "qc_tests": "config/QC_tests.tsv",
                }
            }
        )

        self.assertIsInstance(config.app.input.data, RawDataInput)
        self.assertEqual(config.app.input.data.file, "output/qc_results.tsv")
        self.assertEqual(
            config.app.input.data.api_call,
            "https://example.org/api/data",
        )

    def test_data_input_config_rejects_unknown_fields(self):
        """Unknown structured data input fields should fail config parsing."""
        with self.assertRaises(ValidationError):
            UQCMeConfig(
                app={
                    "input": {
                        "data": {
                            "file": "output/qc_results.tsv",
                            "typo": "unexpected",
                        },
                        "mapping": "config/mapping.yaml",
                        "qc_rules": "config/QC_rules.tsv",
                        "qc_tests": "config/QC_tests.tsv",
                    }
                }
            )

    def test_data_input_config_rejects_scalar_path(self):
        """Data input must use the structured YAML shape."""
        with self.assertRaises(ValidationError):
            UQCMeConfig(
                app={
                    "input": {
                        "data": "output/qc_results.tsv",
                        "mapping": "config/mapping.yaml",
                        "qc_rules": "config/QC_rules.tsv",
                        "qc_tests": "config/QC_tests.tsv",
                    }
                }
            )

    def test_normalize_data_input_builds_file_source(self):
        """Raw file config converts to the runtime file data source."""
        data_input = normalize_data_input(RawDataInput(file="output/qc_results.tsv"))

        self.assertIsInstance(data_input.source, TSVDataSource)
        self.assertEqual(data_input.source.path, Path("output/qc_results.tsv"))

    def test_normalize_data_input_treats_empty_string_as_present(self):
        """An explicit empty string is a configured value, not absence."""
        data_input = normalize_data_input(RawDataInput(file=""))

        self.assertIsInstance(data_input.source, TSVDataSource)
        self.assertEqual(data_input.source.path, Path(""))

    def test_normalize_data_input_builds_api_source(self):
        """Raw API config converts to the runtime API data source."""
        with patch.dict("os.environ", {"UQCME_API_TOKEN": "token-from-env"}):
            data_input = normalize_data_input(
                RawDataInput(
                    api_call="https://example.org/api/data",
                    api_bearer_token_env="UQCME_API_TOKEN",
                )
            )

        self.assertIsInstance(data_input.source, APIDataSource)
        self.assertEqual(data_input.source.call, "https://example.org/api/data")
        self.assertEqual(data_input.source.bearer_token, "token-from-env")

    def test_normalize_data_input_builds_bearer_token(self):
        """Raw API bearer token stays a resolved runtime token."""
        data_input = normalize_data_input(
            RawDataInput(
                api_call="https://example.org/api/data",
                api_bearer_token="test-token",
            )
        )

        self.assertIsInstance(data_input.source, APIDataSource)
        self.assertEqual(data_input.source.bearer_token, "test-token")

    def test_normalize_data_input_rejects_missing_bearer_token_env(self):
        """API bearer token env vars are resolved at normalization time."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(
                ConfigError,
                "Environment variable 'UQCME_API_TOKEN' is not set",
            ):
                normalize_data_input(
                    RawDataInput(
                        api_call="https://example.org/api/data",
                        api_bearer_token_env="UQCME_API_TOKEN",
                    )
                )

    def test_normalize_data_input_rejects_two_bearer_token_sources(self):
        """Runtime API auth cannot use both literal and env bearer tokens."""
        with self.assertRaisesRegex(
            ConfigError,
            "cannot specify both 'api_bearer_token' and 'api_bearer_token_env'",
        ):
            normalize_data_input(
                RawDataInput(
                    api_call="https://example.org/api/data",
                    api_bearer_token="test-token",
                    api_bearer_token_env="UQCME_API_TOKEN",
                )
            )

    def test_normalize_data_input_rejects_file_and_api(self):
        """Runtime data input cannot represent both file and API sources."""
        with self.assertRaisesRegex(
            ConfigError,
            "cannot specify both 'file' and 'api_call'",
        ):
            normalize_data_input(
                RawDataInput(
                    file="output/qc_results.tsv",
                    api_call="https://example.org/api/data",
                )
            )

    def test_sample_api_action_supports_bearer_token_fields(self):
        """Sample API actions should parse bearer token auth fields."""
        config = UQCMeConfig(
            app={
                "input": {
                    "data": RawDataInput(file="output/qc_results.tsv"),
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
