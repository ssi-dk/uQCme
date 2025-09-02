#!/usr/bin/env python3
"""
uQCme - Microbial Quality Control CLI Tool

A command-line tool for processing microbial sequencing QC data against
configurable quality control rules and tests.
"""

import argparse
import logging
import pandas as pd
import yaml
import sys
import re
from pathlib import Path
from typing import Dict, List, Any


class QCProcessor:
    """Main class for processing QC rules and generating outcomes."""

    def __init__(self, config_path: str):
        """Initialize the QC processor with configuration."""
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.run_data: pd.DataFrame = pd.DataFrame()
        self.qc_rules: pd.DataFrame = pd.DataFrame()
        self.qc_tests: pd.DataFrame = pd.DataFrame()
        self.mapping: Dict[str, Any] = {}
        self.qc_overrides: Dict[str, Any] = {}
        self.results: pd.DataFrame = pd.DataFrame()
        self.warnings: set = set()  # Collect unique warnings
        self.skipped_rules: set = set()  # Collect unique skipped rules

    def _setup_logging(self) -> logging.Logger:
        """Set up logging based on configuration."""
        logger = logging.getLogger('uQCme')
        logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Get log file path from config
        log_file = self.config.get('log', {}).get('file', './log/log.tsv')
        
        # Create log directory if it doesn't exist
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter (TSV format for file, readable format for console)
        file_formatter = logging.Formatter(
            '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(message)s'
        )
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            # Can't use self.logger yet since it's not created
            print(f"✓ Configuration loaded from {config_path}")
            return config
        except Exception as e:
            print(f"✗ Error loading config: {e}")
            sys.exit(1)

    def load_input_files(self):
        """Load all input files specified in configuration."""
        try:
            # Load run data
            data_path = self.config['qc']['input']['data']
            self.run_data = pd.read_csv(data_path, sep='\t')
            self.logger.info("✓ Run data loaded: %d samples from %s",
                           len(self.run_data), data_path)

            # Load QC rules
            rules_path = self.config['qc']['input']['qc_rules']
            self.qc_rules = pd.read_csv(rules_path, sep='\t')
            self.logger.info("✓ QC rules loaded: %d rules from %s",
                           len(self.qc_rules), rules_path)

            # Load QC tests
            tests_path = self.config['qc']['input']['qc_tests']
            self.qc_tests = pd.read_csv(tests_path, sep='\t')
            self.logger.info("✓ QC tests loaded: %d tests from %s",
                           len(self.qc_tests), tests_path)

            # Load mapping configuration
            mapping_path = self.config['qc']['input']['mapping']
            with open(mapping_path, 'r', encoding='utf-8') as f:
                self.mapping = yaml.safe_load(f)
            self.logger.info("✓ Mapping configuration loaded from %s",
                           mapping_path)

            # Extract and normalize QC overrides
            self._load_qc_overrides()

        except Exception as e:
            self.logger.error(f"✗ Error loading files: {e}")
            sys.exit(1)

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
                       threshold: Any) -> bool:
        """Apply comparison operator between value and threshold."""
        try:
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
            self.logger.warning(f"Error applying operator {operator}: {e}")
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

        # Get the actual column name
        actual_field = field_mapping.get(field_name, field_name)

        # Check if field exists in sample data
        if actual_field not in sample_data.index:
            warning_msg = f"Field '{actual_field}' not found in sample data"
            self.warnings.add(warning_msg)
            self.skipped_rules.add(rule_id)
            return 'SKIP'

        if actual_field:
            value = sample_data[actual_field]
            operator = rule['operator']
            threshold = rule['value']

            # Apply the rule
            if self._apply_operator(value, operator, threshold):
                return 'PASS'
            else:
                return 'FAIL'
        else:
            self.skipped_rules.add(rule_id)
            return 'SKIP'

    def _get_sample_attributes(self, sample: pd.Series) -> Dict[str, str]:
        """Get sample attributes with defaults from QC overrides."""
        attributes = {}

        # Get species from sample data
        attributes['species'] = sample.get('species', '')

        # Get assembly_type with override default
        default_assembly = self.qc_overrides.get('assembly_type', 'short')
        if isinstance(default_assembly, list) and default_assembly:
            default_assembly = default_assembly[0]
        attributes['assembly_type'] = sample.get('assembly_type', 
                                               default_assembly)

        return attributes

    def _rule_matches_criteria(self, rule: pd.Series, 
                              sample_attributes: Dict[str, str]) -> bool:
        """Check if a rule matches the sample criteria."""
        # Species filtering
        rule_species = rule['species']
        sample_species = sample_attributes['species']
        if rule_species != 'all' and rule_species != sample_species:
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
            qc_outcomes = self._determine_qc_outcomes(failed_rules)
            outcome_str = ','.join(qc_outcomes) if qc_outcomes else 'PASS'
            sample_results['qc_outcome'] = outcome_str
            
            # Determine QC action based on highest priority outcome
            qc_action = self._determine_qc_action(qc_outcomes)
            sample_results['qc_action'] = qc_action

            results_list.append(sample_results)

        self.results = pd.DataFrame(results_list)
        self.logger.info(f"✓ Processed {len(self.results)} samples")

    def _determine_qc_outcomes(self, failed_rules: List[str]) -> List[str]:
        """Determine QC test outcomes based on failed rules."""
        outcomes = []

        for _, test in self.qc_tests.iterrows():
            condition = test['rule_conditions']

            # Skip if condition is NaN or not a string
            if pd.isna(condition) or not isinstance(condition, str):
                continue

            if condition == 'no_failed_rules':
                if not failed_rules:
                    outcomes.append(test['outcome_id'])
            elif condition.startswith('failed_rules_contain:'):
                # Extract rule IDs from condition
                condition_part = condition.replace('failed_rules_contain:', '')
                required_rules = condition_part.split(',')
                # Check if any of the required rules failed
                rule_found = any(
                    rule.strip() in failed_rules for rule in required_rules
                )
                if rule_found:
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
            output_path = self.config['qc']['output']['results']
            self.results.to_csv(output_path, sep='\t', index=False)
            self.logger.info(f"✓ Results saved to {output_path}")
        except Exception as e:
            self.logger.error(f"✗ Error saving results: {e}")
    
    def save_warnings(self):
        """Save warnings to output file."""
        try:
            warnings_path = self.config['qc']['output']['warnings']
            
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='uQCme - Microbial Quality Control CLI Tool'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='Path to configuration YAML file'
    )

    args = parser.parse_args()

    # Print header
    print("🔬 uQCme - Microbial Quality Control CLI Tool")
    print("=" * 50)

    try:
        # Initialize processor
        processor = QCProcessor(args.config)

        # Load input data
        processor.load_input_files()

        # Process samples
        processor.process_samples()

        # Save results
        processor.save_results()
        
        # Save warnings
        processor.save_warnings()

        # Print summary
        processor.print_summary()

        print("\n✅ QC processing completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
