"""Core QC processing engine."""

import logging
import pandas as pd
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from pandera.errors import SchemaError
from .loader import load_data_from_config, load_config_from_file
from .config import UQCMeConfig, DataInput, QCConfig
from .exceptions import (
    ConfigError, DataLoadError, ProcessingError, ValidationError
)
from .logging import setup_logging
from .schemas import QCRulesSchema, QCTestsSchema

logger = logging.getLogger(__name__)

class QCProcessor:
    """Main class for processing QC rules and generating outcomes."""

    def __init__(self, config_path: Optional[str] = None,
                 data_override: Optional[Dict[str, Any]] = None):
        """Initialize the QC processor with configuration."""
        self.config = self._load_config(config_path)
        
        if not self.config.qc:
            raise ConfigError("Invalid configuration: 'qc' section missing")

        # Apply data override if provided
        if data_override:
            # Convert override dict to DataInput model
            self.config.qc.input.data = DataInput(**data_override)
            logger.info(f"Data source overridden: {data_override}")

        self.logger = setup_logging(str(self.config.log.file))
        self.run_data: pd.DataFrame = pd.DataFrame()
        self.qc_rules: pd.DataFrame = pd.DataFrame()
        self.qc_tests: pd.DataFrame = pd.DataFrame()
        self.mapping: Dict[str, Any] = {}
        self.qc_overrides: Dict[str, Any] = {}
        self.results: pd.DataFrame = pd.DataFrame()
        self.warnings: set = set()  # Collect unique warnings
        self.skipped_rules: set = set()  # Collect unique skipped rules

    @property
    def qc_config(self) -> QCConfig:
        """Get QC configuration, ensuring it exists."""
        if not self.config.qc:
            raise ConfigError("QC config missing")
        return self.config.qc

    def _load_config(self, config_path: Optional[str]) -> UQCMeConfig:
        """Load configuration from YAML file or use defaults."""
        if config_path:
            try:
                config = load_config_from_file(config_path)
                print(f"✓ Configuration loaded from {config_path}")
                return config
            except Exception as e:
                raise ConfigError(f"Error loading config: {e}")
        else:
            return self._get_default_config()

    def _get_default_config(self) -> UQCMeConfig:
        """Get default configuration using bundled files."""
        # defaults are in ../defaults relative to this file
        defaults_dir = Path(__file__).parent.parent / 'defaults'
        config_path = defaults_dir / 'config.yaml'
        
        print(f"✓ Using default configuration from {defaults_dir}")
        
        try:
            config = load_config_from_file(str(config_path))
        except Exception as e:
            raise ConfigError(f"Error loading default config: {e}")
            
        # Update paths to point to the defaults directory if local files
        # don't exist
        if config.qc and config.qc.input:
            inp = config.qc.input
            # Update mapping, rules, tests to absolute paths in defaults dir
            if not Path(inp.mapping).exists():
                inp.mapping = str(defaults_dir / Path(inp.mapping).name)
            if not Path(inp.qc_rules).exists():
                inp.qc_rules = str(defaults_dir / Path(inp.qc_rules).name)
            if not Path(inp.qc_tests).exists():
                inp.qc_tests = str(defaults_dir / Path(inp.qc_tests).name)
        
        return config

    def load_input_files(self):
        """Load all input files specified in configuration."""
        try:
            self.load_reference_data()
            self.load_run_data()
        except Exception as e:
            self.logger.error(f"✗ Error loading files: {e}")
            raise

    def load_run_data(self):
        """Load run data from configuration."""
        data_config = self.qc_config.input.data
        # Pass mapping config for column name normalization
        self.run_data = load_data_from_config(data_config, self.mapping)
        self.logger.info("✓ Run data loaded: %d samples",
                         len(self.run_data))

    def load_reference_data(self):
        """Load QC rules, tests, and mapping configuration."""
        try:
            # Load QC rules
            rules_path = self.qc_config.input.qc_rules
            self.qc_rules = pd.read_csv(rules_path, sep='\t')
            QCRulesSchema.validate(self.qc_rules)
            self.logger.info("✓ QC rules loaded: %d rules from %s",
                             len(self.qc_rules), rules_path)
        except SchemaError as e:
            raise ValidationError(f"QC rules validation failed: {e}")
        except Exception as e:
            raise DataLoadError(f"Failed to load reference data: {e}")

        try:
            # Load QC tests
            tests_path = self.qc_config.input.qc_tests
            self.qc_tests = pd.read_csv(tests_path, sep='\t')
            QCTestsSchema.validate(self.qc_tests)
            self.logger.info("✓ QC tests loaded: %d tests from %s",
                             len(self.qc_tests), tests_path)
        except SchemaError as e:
            raise ValidationError(f"QC tests validation failed: {e}")
        except Exception as e:
            raise DataLoadError(f"Failed to load QC tests: {e}")

        # Load mapping configuration
        mapping_path = self.qc_config.input.mapping
        with open(mapping_path, 'r', encoding='utf-8') as f:
            self.mapping = yaml.safe_load(f)
        self.logger.info("✓ Mapping configuration loaded from %s",
                         mapping_path)

        # Extract and normalize QC overrides
        self._load_qc_overrides()

    def _build_field_mapping(self) -> Dict[str, str]:
        """Build field mapping from config, treating strings as lists."""
        field_mapping = {}
        
        # Process each section in the mapping configuration
        if 'Sections' in self.mapping:
            for section_name, section_data in self.mapping['Sections'].items():
                for field_name, field_config in section_data.items():
                    if isinstance(field_config, dict) and 'QC' in field_config:
                        qc_config = field_config['QC']
                        data_config = field_config.get('data', {})
                        data_mapping = data_config.get('mapping')
                        
                        if 'mapping' in qc_config and data_mapping:
                            qc_mappings = qc_config['mapping']
                            # Treat string as single-item list
                            if isinstance(qc_mappings, str):
                                qc_mappings = [qc_mappings]
                            
                            # Map each QC field to the data field
                            for qc_field in qc_mappings:
                                field_mapping[qc_field] = data_mapping
        
        return field_mapping

    def _load_qc_overrides(self):
        """Load and normalize QC override settings."""
        self.qc_overrides = {}

        if 'QC_overrides' in self.mapping:
            overrides = self.mapping['QC_overrides']

            # Process each override, converting strings to lists
            for key, value in overrides.items():
                if isinstance(value, str):
                    # Convert single string to list
                    self.qc_overrides[key] = [value]
                elif isinstance(value, list):
                    # Keep list as is
                    self.qc_overrides[key] = value
                else:
                    # Keep other types as is (like booleans, numbers)
                    self.qc_overrides[key] = value

        self.logger.info(f"✓ QC overrides loaded: {self.qc_overrides}")

    def _apply_operator(self, value: Any, operator: str,
                        threshold: Any, field_name: str = "unknown") -> bool:
        """Apply comparison operator between value and threshold."""
        try:
            # Handle null/None/NaN values - treat as missing data, rule fails
            if value is None or pd.isna(value) or str(value).lower() in ('null', 'none', 'nan', ''):
                self.logger.debug(
                    f"Null/missing value for field '{field_name}', "
                    f"skipping comparison"
                )
                return False
            
            # Handle numeric comparisons
            if operator == '>=':
                return float(value) >= float(threshold)
            elif operator == '<=':
                return float(value) <= float(threshold)
            elif operator == '>':
                return float(value) > float(threshold)
            elif operator == '<':
                return float(value) < float(threshold)
            elif operator == '=':
                return str(value) == str(threshold)
            elif operator == 'regex':
                # Handle NaN values properly for regex
                if pd.isna(value) or pd.isna(threshold):
                    return False
                return bool(re.match(str(threshold), str(value)))
            else:
                self.logger.warning(f"Unknown operator {operator}")
                return False
        except (ValueError, TypeError) as e:
            self.logger.warning(
                f"Error applying operator {operator} on field '{field_name}': "
                f"value='{value}', threshold='{threshold}' - {e}"
            )
            return False

    def _evaluate_rule(self, sample_data: pd.Series, rule: pd.Series) -> str:
        """Evaluate a single QC rule against sample data.
        
        Returns:
            'PASS': Rule passed
            'FAIL': Rule failed  
            'SKIP': Rule cannot be evaluated (missing field)
        """
        # Get the field value from sample data
        field_name = rule['field']
        rule_id = rule['rule_id']

        # Build dynamic field mapping from configuration
        field_mapping = self._build_field_mapping()

        # Get the actual column name from mapping
        actual_field = field_mapping.get(field_name, field_name)

        # Check if field exists in sample data
        if actual_field not in sample_data.index:
            # Generate helpful warning message
            if field_name in field_mapping:
                # Field was mapped but target column doesn't exist
                warning_msg = (
                    f"Field '{field_name}' (mapped to '{actual_field}') "
                    f"not found in sample data"
                )
            else:
                # Field has no mapping defined
                warning_msg = (
                    f"Field '{field_name}' not found in sample data "
                    f"(no mapping defined in config)"
                )
            self.warnings.add(warning_msg)
            self.skipped_rules.add(rule_id)
            return 'SKIP'

        if actual_field:
            value = sample_data[actual_field]
            operator = rule['operator']
            threshold = rule['value']

            # Apply the rule
            if self._apply_operator(value, operator, threshold, actual_field):
                return 'PASS'
            else:
                return 'FAIL'
        else:
            self.skipped_rules.add(rule_id)
            return 'SKIP'

    def _get_sample_attributes(self, sample: pd.Series) -> Dict[str, str]:
        """Get sample attributes with defaults from QC overrides."""
        attributes = {}

        # Get species from sample data (strip whitespace)
        species_val = sample.get('species', '')
        if isinstance(species_val, str):
            species_val = species_val.strip()
        attributes['species'] = species_val

        # Get assembly_type with override default
        default_assembly = self.qc_overrides.get('assembly_type', 'short')
        if isinstance(default_assembly, list) and default_assembly:
            default_assembly = default_assembly[0]
        attributes['assembly_type'] = sample.get(
            'assembly_type', default_assembly
        )

        return attributes

    def _rule_matches_criteria(self, rule: pd.Series,
                               sample_attributes: Dict[str, str]) -> bool:
        """Check if a rule matches the sample criteria."""
        # Species filtering (strip whitespace for comparison)
        rule_species = str(rule['species']).strip() if pd.notna(rule['species']) else ''
        sample_species = str(sample_attributes['species']).strip() if sample_attributes.get('species') else ''
        # Explicitly handle empty species values: if either is empty, do not match unless rule_species is 'all'
        if rule_species == '' or sample_species == '':
            if rule_species != 'all':
                return False
        elif rule_species != 'all' and rule_species.lower() != sample_species.lower():
            return False

        # Assembly type filtering
        rule_assembly = rule['assembly_type']
        sample_assembly = sample_attributes['assembly_type']
        if rule_assembly != 'all' and rule_assembly != sample_assembly:
            return False

        # Software filtering using overrides
        rule_software = rule['software']
        if 'software' in self.qc_overrides:
            allowed_software = self.qc_overrides['software']
            # If software is specified in rule, it must be in allowed list
            # (case-insensitive comparison)
            if rule_software and pd.notna(rule_software):
                allowed_lower = [s.lower() for s in allowed_software]
                if str(rule_software).lower() not in allowed_lower:
                    return False

        return True

    def process_samples(self):
        """Process all samples through QC rules."""
        self.logger.info("\n🔍 Processing samples through QC rules...")

        results_list = []

        for idx, sample in self.run_data.iterrows():
            sample_results = sample.copy()
            failed_rules = []
            passed_rules = []

            # Get sample attributes with defaults
            sample_attributes = self._get_sample_attributes(sample)

            # Test each rule against this sample
            for _, rule in self.qc_rules.iterrows():
                rule_id = rule['rule_id']

                # Check if rule applies to this sample
                if not self._rule_matches_criteria(rule, sample_attributes):
                    continue

                # Evaluate the rule
                rule_result = self._evaluate_rule(sample, rule)
                if rule_result == 'PASS':
                    passed_rules.append(rule_id)
                elif rule_result == 'FAIL':
                    failed_rules.append(rule_id)
                # 'SKIP' rules are not added to either list

            # Add rule results to sample data
            failed_str = ','.join(failed_rules) if failed_rules else ''
            sample_results['failed_rules'] = failed_str

            passed_str = ','.join(passed_rules) if passed_rules else ''
            sample_results['passed_rules'] = passed_str

            # Determine QC outcomes
            qc_outcomes = self._determine_qc_outcomes(failed_rules, passed_rules)
            outcome_str = ','.join(qc_outcomes) if qc_outcomes else 'PASS'
            sample_results['qc_outcome'] = outcome_str
            
            # Determine QC action based on highest priority outcome
            qc_action = self._determine_qc_action(qc_outcomes)
            sample_results['qc_action'] = qc_action

            results_list.append(sample_results)

        self.results = pd.DataFrame(results_list)
        self.logger.info(f"✓ Processed {len(self.results)} samples")

    def _determine_qc_outcomes(self, failed_rules: List[str],
                                passed_rules: List[str]) -> List[str]:
        """Determine QC test outcomes based on failed and passed rules.
        
        Uses two separate columns:
        - failed_rule_conditions: comma-separated rules, OR logic (any failure triggers)
        - passed_rule_conditions: comma-separated rules, none-failed logic 
          (none of these rules can be in failed_rules)
        
        Both conditions must be satisfied if specified (AND between columns).
        
        Special case: If both columns are empty/NaN, the test matches only when
        there are no failed rules (equivalent to old 'no_failed_rules').
        """
        outcomes = []

        for _, test in self.qc_tests.iterrows():
            passed_conditions = test.get('passed_rule_conditions')
            failed_conditions = test.get('failed_rule_conditions')
            
            # Check if passed_rule_conditions is specified
            has_passed_conditions = (
                pd.notna(passed_conditions) and 
                isinstance(passed_conditions, str) and 
                passed_conditions.strip()
            )
            
            # Check if failed_rule_conditions is specified
            has_failed_conditions = (
                pd.notna(failed_conditions) and 
                isinstance(failed_conditions, str) and 
                failed_conditions.strip()
            )
            
            # Special case: both columns empty = match when no failed rules
            if not has_passed_conditions and not has_failed_conditions:
                if not failed_rules:  # No failed rules = this test matches
                    outcomes.append(test['outcome_id'])
                continue
            
            # Evaluate conditions
            passed_match = True  # Default to True if not specified
            failed_match = True  # Default to True if not specified
            
            if has_passed_conditions:
                # NONE-FAILED logic - NONE of these rules can be in failed_rules
                # BUT at least one of these rules must have been evaluated (in passed_rules or failed_rules)
                required_rules = [r.strip() for r in passed_conditions.split(',')]
                # Check if at least one rule was evaluated
                any_evaluated = any(rule in passed_rules or rule in failed_rules for rule in required_rules)
                if not any_evaluated:
                    passed_match = False  # Skip this test if none of the rules were evaluated
                else:
                    passed_match = not any(rule in failed_rules for rule in required_rules)
            
            if has_failed_conditions:
                # OR logic - ANY rule must be in failed_rules
                required_rules = [r.strip() for r in failed_conditions.split(',')]
                failed_match = any(rule in failed_rules for rule in required_rules)
            
            # Both conditions must be satisfied (AND between columns)
            if passed_match and failed_match:
                outcomes.append(test['outcome_id'])

        # If no specific outcomes, but there are failed rules, mark as
        # general failure
        if not outcomes and failed_rules:
            outcomes.append('FAIL')

        return outcomes

    def _determine_qc_action(self, qc_outcomes: List[str]) -> str:
        """Determine the action required based on highest priority outcome."""
        if not qc_outcomes:
            # If no outcomes (PASS case), find the PASS action
            pass_test = self.qc_tests[
                self.qc_tests['outcome_id'] == 'PASS'
            ]
            if not pass_test.empty:
                return pass_test.iloc[0]['action_required']
            return 'none'
        
        # Find the highest priority among the outcomes
        highest_priority = 0
        action_required = 'none'
        
        for outcome_id in qc_outcomes:
            test_match = self.qc_tests[
                self.qc_tests['outcome_id'] == outcome_id
            ]
            if not test_match.empty:
                test_priority = test_match.iloc[0]['priority']
                test_action = test_match.iloc[0]['action_required']
                
                # Higher number = higher priority
                if test_priority > highest_priority:
                    highest_priority = test_priority
                    action_required = test_action
        
        return action_required

    def save_results(self):
        """Save processing results to output file."""
        try:
            output_path = self.qc_config.output.results
            self.results.to_csv(output_path, sep='\t', index=False)
            self.logger.info(f"✓ Results saved to {output_path}")
        except Exception as e:
            self.logger.error(f"✗ Error saving results: {e}")
            raise ProcessingError(f"Failed to save results: {e}")
    
    def save_warnings(self):
        """Save warnings to output file."""
        try:
            warnings_path = self.qc_config.output.warnings
            
            # Create warnings dataframe
            warnings_data = []
            for warning in sorted(self.warnings):
                warnings_data.append({
                    'warning_type': 'processing',
                    'warning_message': warning,
                    'timestamp': pd.Timestamp.now().isoformat()
                })
            
            # Add skipped rules as warnings
            for rule in sorted(self.skipped_rules):
                warning_msg = f"Rule {rule} skipped due to missing fields"
                warnings_data.append({
                    'warning_type': 'skipped_rule',
                    'warning_message': warning_msg,
                    'timestamp': pd.Timestamp.now().isoformat()
                })
            
            if warnings_data:
                warnings_df = pd.DataFrame(warnings_data)
                warnings_df.to_csv(warnings_path, sep='\t', index=False)
                self.logger.info(f"✓ Warnings saved to {warnings_path}")
            else:
                # Create empty file with headers
                empty_df = pd.DataFrame(columns=[
                    'warning_type', 'warning_message', 'timestamp'
                ])
                empty_df.to_csv(warnings_path, sep='\t', index=False)
                info_msg = (f"✓ No warnings - empty file created at "
                            f"{warnings_path}")
                self.logger.info(info_msg)
                
        except Exception as e:
            self.logger.error(f"✗ Error saving warnings: {e}")
            raise ProcessingError(f"Failed to save warnings: {e}")

    def print_summary(self):
        """Print processing summary statistics."""
        self.logger.info("\n📊 Processing Summary:")
        self.logger.info(f"   Total samples processed: {len(self.results)}")

        # Count QC outcomes
        outcome_counts = {}
        for outcomes_str in self.results['qc_outcome']:
            if outcomes_str and outcomes_str != 'PASS':
                for outcome in outcomes_str.split(','):
                    outcome = outcome.strip()
                    current_count = outcome_counts.get(outcome, 0)
                    outcome_counts[outcome] = current_count + 1

        if outcome_counts:
            self.logger.info("   QC Outcomes:")
            for outcome, count in sorted(outcome_counts.items()):
                self.logger.info(f"     {outcome}: {count}")

        # Count most common failed rules
        failed_rule_counts = {}
        for failed_rules_str in self.results['failed_rules']:
            if failed_rules_str:
                for rule in failed_rules_str.split(','):
                    rule = rule.strip()
                    count = failed_rule_counts.get(rule, 0) + 1
                    failed_rule_counts[rule] = count

        if failed_rule_counts:
            self.logger.info("   Most common failed rules:")
            items = failed_rule_counts.items()
            sorted_failures = sorted(items, key=lambda x: x[1], reverse=True)
            for rule, count in sorted_failures[:10]:  # Top 10
                self.logger.info(f"     {rule}: {count}")

        # Display unique warnings
        if self.warnings:
            self.logger.info("\n⚠️ Warnings encountered:")
            for warning in sorted(self.warnings):
                self.logger.info(f"   {warning}")

        # Display unique skipped rules
        if self.skipped_rules:
            skipped_list = ', '.join(sorted(self.skipped_rules))
            self.logger.info("\n⚠️ Skipped rules (due to missing fields):")
            self.logger.info(f"   {skipped_list}")
