#!/usr/bin/env python3
"""
Test suite for uQCme CLI tool

This test suite verifies that the QC outcomes match expected results
for the example dataset, ensuring the tool works correctly.

The test data is structured with two groups:
  - example_* samples: pedagogical, demonstrate each major scenario
  - test_* samples: edge cases for systematic rule coverage
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

    def _get_outcome_set(self, sample_name):
        """Return (outcome_set, failed_rules_str) for a sample."""
        sample_row = self.results[self.results['sample_name'] == sample_name]
        self.assertEqual(len(sample_row), 1, f"Sample {sample_name} not found")
        outcome = sample_row.iloc[0]['qc_outcome']
        failed = sample_row.iloc[0]['failed_rules']
        if pd.isna(failed):
            failed = ''
        return set(outcome.split(',')), failed

    # ── Example samples ──────────────────────────────────────────

    def test_example_pass_ecoli(self):
        """E. coli sample passing all rules (PASS + PASS_GENERAL)."""
        outcomes, failed = self._get_outcome_set('example_pass_ecoli')
        self.assertEqual(outcomes, {'PASS', 'PASS_GENERAL'})
        self.assertEqual(failed, '')

    def test_example_pass_saureus(self):
        """S. aureus sample passing all rules (PASS + PASS_GENERAL)."""
        outcomes, failed = self._get_outcome_set('example_pass_saureus')
        self.assertEqual(outcomes, {'PASS', 'PASS_GENERAL'})
        self.assertEqual(failed, '')

    def test_example_pass_general_fail_species_kp(self):
        """K. pneumoniae: passes general + read QC, fails species rules."""
        outcomes, failed = self._get_outcome_set(
            'example_pass_general_fail_species_kp')
        self.assertIn('PASS', outcomes)
        self.assertIn('PASS_GENERAL', outcomes)
        self.assertIn('FAIL_KLEBSIELLA_PNEUMONIAE', outcomes)

    def test_example_warn_review(self):
        """Sample in warning zone: fails PASS thresholds, passes WARN."""
        outcomes, failed = self._get_outcome_set('example_warn_review')
        self.assertEqual(outcomes, {'WARN'})
        # Should have failed strict PASS rules
        for rule in ['PASS1', 'PASS2', 'PASS3', 'PASS4', 'PASS5']:
            self.assertIn(rule, failed,
                f"Expected {rule} in failed rules for WARN sample")

    def test_example_fail_read_qc(self):
        """Sample failing all read QC thresholds → FAIL outcome."""
        outcomes, failed = self._get_outcome_set('example_fail_read_qc')
        self.assertEqual(outcomes, {'FAIL'})
        # Should have failed both PASS and WARN rules
        for rule in ['WARN1', 'WARN2', 'WARN3', 'WARN4', 'WARN5']:
            self.assertIn(rule, failed)

    def test_example_fail_assembly(self):
        """Sample with good read QC but bad assembly → PASS + FAIL_GENERAL."""
        outcomes, failed = self._get_outcome_set('example_fail_assembly')
        self.assertIn('PASS', outcomes)
        self.assertIn('FAIL_GENERAL', outcomes)
        # A-rules should be in failed
        for rule in ['A1', 'A2']:
            self.assertIn(rule, failed)

    # ── Test: boundary conditions ────────────────────────────────

    def test_boundary_pass_exact(self):
        """All PASS thresholds exactly at limit → should PASS."""
        outcomes, failed = self._get_outcome_set('test_boundary_pass_exact')
        self.assertEqual(outcomes, {'PASS', 'PASS_GENERAL'})
        self.assertEqual(failed, '')

    def test_boundary_warn_exact(self):
        """All WARN thresholds exactly at limit → should WARN."""
        outcomes, failed = self._get_outcome_set('test_boundary_warn_exact')
        self.assertEqual(outcomes, {'WARN'})

    # ── Test: individual WARN-tier failures ──────────────────────

    def test_fail_coverage(self):
        """Coverage just below WARN threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_coverage')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_contamination(self):
        """Contamination just above WARN threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_contamination')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_q30(self):
        """Q30 just below WARN threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_q30')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_readlen(self):
        """Read length just below WARN threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_readlen')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_dup(self):
        """Duplication rate just above WARN threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_dup')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_gc(self):
        """Unexpected GC just above threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_gc')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_ncontent(self):
        """N content just above threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_ncontent')
        self.assertEqual(outcomes, {'FAIL'})

    def test_fail_adapter(self):
        """Adapter count just above threshold → FAIL."""
        outcomes, _ = self._get_outcome_set('test_fail_adapter')
        self.assertEqual(outcomes, {'FAIL'})

    # ── Test: special cases ──────────────────────────────────────

    def test_multiple_genomes(self):
        """Multiple genomes detected → PASS + FAIL_GENERAL (A20)."""
        outcomes, failed = self._get_outcome_set('test_multiple_genomes')
        self.assertIn('PASS', outcomes)
        self.assertIn('FAIL_GENERAL', outcomes)
        self.assertIn('A20', failed)

    def test_species_sa_fail_gc(self):
        """S. aureus with GC outside species range → species-specific fail."""
        outcomes, failed = self._get_outcome_set('test_species_sa_fail_gc')
        self.assertIn('PASS', outcomes)
        self.assertIn('PASS_GENERAL', outcomes)
        self.assertIn('FAIL_STAPHYLOCOCCUS_AUREUS', outcomes)
        # SA GC rules should fail (SA4 = GC<=33.1, SA12 = GC(%)<33.1)
        self.assertIn('SA4', failed)
        self.assertIn('SA12', failed)

    def test_multiple_failures(self):
        """Everything bad → FAIL + FAIL_GENERAL."""
        outcomes, _ = self._get_outcome_set('test_multiple_failures')
        self.assertIn('FAIL', outcomes)
        self.assertIn('FAIL_GENERAL', outcomes)

    # ── Structural tests ─────────────────────────────────────────

    def test_skipped_rules(self):
        """Test that the correct rules are skipped due to missing fields."""
        expected_skipped_rules = {
            'A16', 'A17', 'A18', 'A19', 'A3',
            'EC5', 'EC10', 'EC13', 'EC14', 'EC15',
            'KP5', 'KP8', 'KP13', 'KP14', 'KP15', 'KP24', 'KP29',
            'KP32', 'KP33', 'KP34',
            'SA5', 'SA10', 'SA13', 'SA14', 'SA15',
        }

        actual_skipped = self.processor.skipped_rules

        self.assertEqual(actual_skipped, expected_skipped_rules,
            f"Expected skipped rules {sorted(expected_skipped_rules)}, "
            f"got {sorted(actual_skipped)}")

    def test_warnings_generated(self):
        """Test that appropriate warnings are generated."""
        # The new mapping adds Sylph/fastp fields but still lacks some
        expected_substrings = [
            "Ns per 100 kbp",
        ]

        for substring in expected_substrings:
            self.assertTrue(
                any(substring in w for w in self.processor.warnings),
                f"Expected a warning containing '{substring}', "
                f"got {self.processor.warnings}")

    def test_sample_count(self):
        """Test that all 19 samples are processed."""
        self.assertEqual(len(self.results), 19,
            f"Expected 19 samples, got {len(self.results)}")

    def test_no_empty_outcomes(self):
        """Test that no samples have empty or invalid outcomes."""
        for idx, row in self.results.iterrows():
            sample_name = row['sample_name']
            outcome = row['qc_outcome']

            with self.subTest(sample=sample_name):
                self.assertIsNotNone(outcome,
                    f"Sample {sample_name} has None outcome")
                self.assertNotEqual(outcome, '',
                    f"Sample {sample_name} has empty outcome")
                self.assertIsInstance(outcome, str,
                    f"Sample {sample_name} outcome is not string")

    def test_outcome_format(self):
        """Test that QC outcomes follow expected format."""
        valid_outcomes = {
            'PASS', 'PASS_GENERAL', 'WARN', 'FAIL', 'FAIL_GENERAL',
            'FAIL_ACINETOBACTER_BAUMANNII',
            'FAIL_CAMPYLOBACTER_COLI',
            'FAIL_CAMPYLOBACTER_JEJUNI',
            'FAIL_ESCHERICHIA_COLI',
            'FAIL_ENTEROCOCCUS_FAECIUM',
            'FAIL_ENTEROBACTER_SPP',
            'FAIL_HAEMOPHILUS_INFLUENZAE',
            'FAIL_HELICOBACTER_PYLORI',
            'FAIL_KLEBSIELLA_PNEUMONIAE',
            'FAIL_MYCOPLASMA_GENITALIUM',
            'FAIL_NEISSERIA_GONORRHOEAE',
            'FAIL_PSEUDOMONAS_AERUGINOSA',
            'FAIL_STAPHYLOCOCCUS_AUREUS',
            'FAIL_SALMONELLA_ENTERICA',
            'FAIL_SHIGELLA_FLEXNERI',
            'FAIL_STREPTOCOCCUS_PNEUMONIAE',
            'FAIL_SHIGELLA_SONNEI',
        }

        for idx, row in self.results.iterrows():
            sample_name = row['sample_name']
            outcome = row['qc_outcome']

            with self.subTest(sample=sample_name):
                for single_outcome in outcome.split(','):
                    single_outcome = single_outcome.strip()
                    self.assertIn(single_outcome, valid_outcomes,
                        f"Sample {sample_name} has invalid outcome: "
                        f"{single_outcome}")

    def test_action_consistency(self):
        """Test that qc_action matches the highest-priority outcome."""
        for idx, row in self.results.iterrows():
            sample_name = row['sample_name']
            outcomes = set(row['qc_outcome'].split(','))
            action = row['qc_action']

            with self.subTest(sample=sample_name):
                if outcomes == {'PASS', 'PASS_GENERAL'}:
                    self.assertEqual(action, 'none')
                elif 'FAIL' in outcomes or 'FAIL_GENERAL' in outcomes or any(
                        o.startswith('FAIL_') for o in outcomes):
                    self.assertEqual(action, 'reject')
                elif 'WARN' in outcomes:
                    self.assertEqual(action, 'review')


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

        required_columns = ['sample_name', 'species', 'GC', 'N50',
                            'coverage_x', 'contamination_percent',
                            'q30_fraction', 'mean_read_length_bp',
                            'duplication_rate', 'number_of_genomes']
        for col in required_columns:
            self.assertIn(col, data.columns,
                f"Required column {col} missing from example_run_data.tsv")

        # Test QC_rules.tsv
        rules_path = self.test_dir / "data" / "QC_rules.tsv"
        rules = pd.read_csv(rules_path, sep='\t')

        required_rule_columns = ['rule_id', 'species', 'assembly_type',
                                 'software', 'field', 'operator', 'value']
        for col in required_rule_columns:
            self.assertIn(col, rules.columns,
                f"Required column {col} missing from QC_rules.tsv")


if __name__ == '__main__':
    # Change to test directory so relative paths work
    test_dir = Path(__file__).parent
    os.chdir(test_dir.parent)

    # Run tests
    unittest.main(verbosity=2)
