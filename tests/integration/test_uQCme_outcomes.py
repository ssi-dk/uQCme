#!/usr/bin/env python3
"""
Test suite for uQCme CLI tool

This test suite verifies that the QC outcomes match expected results
for the example dataset, ensuring the tool works correctly.
"""

import unittest
import pandas as pd
import yaml
import sys
import os
from pathlib import Path

# Add the src directory to sys.path to import uQCme package
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from uQCme.core.engine import QCProcessor


class TestUQCmeOutcomes(unittest.TestCase):
    """Test QC outcome generation for example dataset."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent.parent
        self.config_path = self.test_dir / "fixtures" / "config_example.yaml"
        self.results_path = self.test_dir / "uQCme_example_run_data.tsv"
        
        # Initialize processor
        self.processor = QCProcessor(str(self.config_path))
        self.processor.load_input_files()
        self.processor.process_samples()
        
        # Load expected outcomes
        self.results = pd.read_csv(self.results_path, sep='\t')
        
    def test_pass_samples(self):
        """Test samples that should pass all applicable QC rules."""
        expected_pass_samples = [
            'PASS_General_01',
            'PASS_General_02',
            'PASS_E_coli_01',
            'PASS_K_pneumoniae_01',
            'SPECIES_SPECIFIC_KP_PASS',
            'SPECIES_SPECIFIC_SA_PASS'
        ]
        
        for sample_name in expected_pass_samples:
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                failed_rules = sample_row.iloc[0]['failed_rules']
                
                # Handle NaN values
                if pd.isna(failed_rules):
                    failed_rules = ''
                
                self.assertEqual(outcome, 'PASS',
                    f"Sample {sample_name} should be PASS, got {outcome}")
                self.assertEqual(failed_rules, '',
                    f"Sample {sample_name} should have no failed rules, got {failed_rules}")

    def test_size_failure_samples(self):
        """Test samples that should fail size-related QC rules."""
        expected_size_failures = {
            'FAIL_SIZE_TOO_SMALL': ['FAIL_SIZE'],
            'FAIL_SIZE_TOO_LARGE': ['FAIL'],
            'FAIL_ECOLI_SIZE_SMALL': ['WARN_ECOLI_QC', 'FAIL_ECOLI_SIZE'],
            'FAIL_ECOLI_SIZE_LARGE': ['WARN_CONTAMINATION', 'WARN_ECOLI_QC', 'FAIL_ECOLI_SIZE']
        }
        
        for sample_name, expected_outcomes in expected_size_failures.items():
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                actual_outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                expected_set = set(expected_outcomes)
                
                self.assertEqual(actual_outcomes, expected_set,
                    f"Sample {sample_name}: expected {expected_set}, got {actual_outcomes}")

    def test_completeness_warnings(self):
        """Test samples that should trigger completeness warnings."""
        completeness_samples = [
            'WARN_COMPLETENESS_01',
            'WARN_COMPLETENESS_02'
        ]
        
        for sample_name in completeness_samples:
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                
                self.assertIn('WARN_COMPLETENESS', outcomes,
                    f"Sample {sample_name} should have WARN_COMPLETENESS, got {outcomes}")

    def test_contamination_warnings(self):
        """Test samples that should trigger contamination warnings."""
        contamination_samples = [
            'WARN_CONTAMINATION_01',
            'WARN_CONTAMINATION_02'
        ]
        
        for sample_name in contamination_samples:
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                
                self.assertIn('WARN_CONTAMINATION', outcomes,
                    f"Sample {sample_name} should have WARN_CONTAMINATION, got {outcomes}")

    def test_gc_range_warnings(self):
        """Test samples that should trigger GC content warnings."""
        gc_range_samples = [
            'WARN_GC_RANGE_LOW',
            'WARN_GC_RANGE_HIGH'
        ]
        
        for sample_name in gc_range_samples:
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                
                self.assertIn('WARN_GC_RANGE', outcomes,
                    f"Sample {sample_name} should have WARN_GC_RANGE, got {outcomes}")

    def test_assembly_failures(self):
        """Test samples that should fail assembly QC rules."""
        assembly_samples = [
            'FAIL_ASSEMBLY_CONTIGS',
            'FAIL_ASSEMBLY_N50'
        ]
        
        for sample_name in assembly_samples:
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                
                self.assertIn('FAIL_ASSEMBLY', outcomes,
                    f"Sample {sample_name} should have FAIL_ASSEMBLY, got {outcomes}")

    def test_ecoli_specific_rules(self):
        """Test E.coli specific QC rules and outcomes."""
        ecoli_samples = {
            'WARN_ECOLI_QC_01': ['WARN_ECOLI_QC'],
            'WARN_ECOLI_QC_02': ['WARN_CONTAMINATION', 'WARN_ECOLI_QC'],
            'FAIL_ECOLI_SPECIES_01': ['WARN_COMPLETENESS', 'WARN_CONTAMINATION', 'WARN_ECOLI_QC', 'FAIL_ECOLI_SPECIES'],
        }
        
        for sample_name, expected_outcomes in ecoli_samples.items():
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                actual_outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                expected_set = set(expected_outcomes)
                
                self.assertEqual(actual_outcomes, expected_set,
                    f"Sample {sample_name}: expected {expected_set}, got {actual_outcomes}")

    def test_species_specific_outcomes(self):
        """Test species-specific rule evaluation."""
        species_samples = {
            'SPECIES_SPECIFIC_KP_FAIL': ['WARN_COMPLETENESS', 'WARN_CONTAMINATION'],
            'SPECIES_SPECIFIC_SA_FAIL': ['WARN_COMPLETENESS', 'WARN_CONTAMINATION']
        }
        
        for sample_name, expected_outcomes in species_samples.items():
            with self.subTest(sample=sample_name):
                sample_row = self.results[self.results['sample_name'] == sample_name]
                self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
                
                outcome = sample_row.iloc[0]['qc_outcome']
                actual_outcomes = set(outcome.split(',')) if outcome != 'PASS' else set()
                expected_set = set(expected_outcomes)
                
                self.assertEqual(actual_outcomes, expected_set,
                    f"Sample {sample_name}: expected {expected_set}, got {actual_outcomes}")

    def test_skipped_rules(self):
        """Test that the correct rules are skipped due to missing fields."""
        expected_skipped_rules = {
            'A16', 'AB10', 'CJ10', 'EC10', 'EF10', 'EN10', 'HI10', 'HP10', 
            'KP29', 'KP5', 'MG12', 'NG10', 'PA10', 'SA10', 'SE10', 'SF10', 'SP10', 'SS10'
        }
        
        actual_skipped = self.processor.skipped_rules
        
        self.assertEqual(actual_skipped, expected_skipped_rules,
            f"Expected skipped rules {expected_skipped_rules}, got {actual_skipped}")

    def test_warnings_generated(self):
        """Test that appropriate warnings are generated."""
        expected_warnings = {
            "Field 'Ns per 100 kbp' not found in sample data (no mapping defined in config)"
        }
        
        actual_warnings = self.processor.warnings
        
        self.assertEqual(actual_warnings, expected_warnings,
            f"Expected warnings {expected_warnings}, got {actual_warnings}")

    def test_sample_count(self):
        """Test that all 30 samples are processed."""
        self.assertEqual(len(self.results), 30,
            f"Expected 30 samples, got {len(self.results)}")

    def test_no_empty_outcomes(self):
        """Test that no samples have empty or invalid outcomes."""
        for idx, row in self.results.iterrows():
            sample_name = row['sample_name']
            outcome = row['qc_outcome']
            
            with self.subTest(sample=sample_name):
                self.assertIsNotNone(outcome, f"Sample {sample_name} has None outcome")
                self.assertNotEqual(outcome, '', f"Sample {sample_name} has empty outcome")
                self.assertIsInstance(outcome, str, f"Sample {sample_name} outcome is not string")

    def test_outcome_format(self):
        """Test that QC outcomes follow expected format."""
        valid_outcomes = {
            'PASS', 'FAIL', 'WARN_COMPLETENESS', 'WARN_CONTAMINATION', 
            'WARN_GC_RANGE', 'WARN_ECOLI_QC', 'FAIL_ASSEMBLY', 'FAIL_SIZE',
            'FAIL_ECOLI_SIZE', 'FAIL_ECOLI_SPECIES', 'FAIL_MAPPING_ISSUES'
        }
        
        for idx, row in self.results.iterrows():
            sample_name = row['sample_name']
            outcome = row['qc_outcome']
            
            with self.subTest(sample=sample_name):
                outcomes = outcome.split(',') if outcome != 'PASS' else ['PASS']
                for single_outcome in outcomes:
                    single_outcome = single_outcome.strip()
                    self.assertIn(single_outcome, valid_outcomes,
                        f"Sample {sample_name} has invalid outcome: {single_outcome}")


class TestDataIntegrity(unittest.TestCase):
    """Test the integrity of test data files."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent.parent

    def test_all_test_files_exist(self):
        """Test that all required test files exist."""
        required_files = [
            ('fixtures/config_example.yaml', 'config file'),
            ('data/example_run_data.tsv', 'sample data'),
            ('data/mapping.yaml', 'field mapping'),
            ('data/QC_rules.tsv', 'QC rules'),
            ('data/QC_tests.tsv', 'QC tests')
        ]
        
        for filename, description in required_files:
            file_path = self.test_dir / filename
            self.assertTrue(file_path.exists(),
                f"Required {description} file {filename} does not exist")

    def test_config_file_validity(self):
        """Test that the config file is valid YAML."""
        config_path = self.test_dir / "fixtures" / "config_example.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        self.assertIsInstance(config, dict, "Config file should be a dictionary")
        self.assertIn('qc', config, "Config should have 'qc' section")
        self.assertIn('input', config['qc'], "Config should have 'qc.input' section")
        self.assertIn('output', config['qc'], "Config should have 'qc.output' section")

    def test_data_file_structure(self):
        """Test that data files have expected structure."""
        # Test example_run_data.tsv
        data_path = self.test_dir / "data" / "example_run_data.tsv"
        data = pd.read_csv(data_path, sep='\t')
        
        required_columns = ['sample_name', 'species', 'GC', 'N50']
        for col in required_columns:
            self.assertIn(col, data.columns,
                f"Required column {col} missing from example_run_data.tsv")

        # Test QC_rules.tsv
        rules_path = self.test_dir / "data" / "QC_rules.tsv"
        rules = pd.read_csv(rules_path, sep='\t')
        
        required_rule_columns = ['rule_id', 'species', 'assembly_type', 'software', 'field', 'operator', 'value']
        for col in required_rule_columns:
            self.assertIn(col, rules.columns,
                f"Required column {col} missing from QC_rules.tsv")


if __name__ == '__main__':
    # Change to test directory so relative paths work
    test_dir = Path(__file__).parent
    os.chdir(test_dir.parent)
    
    # Run tests
    unittest.main(verbosity=2)
