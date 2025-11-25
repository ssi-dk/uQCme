#!/usr/bin/env python3
"""
Unit tests for uQCme QCProcessor class methods.

These tests focus on individual methods and components
rather than full integration workflows.
"""

import unittest
import sys
from pathlib import Path

import pandas as pd

# Add the src directory to sys.path to import uQCme package
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from uQCme.cli import QCProcessor


class TestQCProcessor(unittest.TestCase):
    """Unit tests for QCProcessor class methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent.parent
        self.config_path = self.test_dir / "fixtures" / "config_example.yaml"
        self.processor = QCProcessor(str(self.config_path))

    def test_load_config(self):
        """Test configuration loading."""
        self.assertIsInstance(self.processor.config, dict)
        self.assertIn('qc', self.processor.config)
        self.assertIn('input', self.processor.config['qc'])
        self.assertIn('output', self.processor.config['qc'])

    def test_apply_operator(self):
        """Test operator application logic."""
        # Test numeric comparisons
        self.assertTrue(self.processor._apply_operator(5, '>=', 3))
        self.assertFalse(self.processor._apply_operator(2, '>=', 3))
        self.assertTrue(self.processor._apply_operator(10, '<=', 15))
        self.assertFalse(self.processor._apply_operator(20, '<=', 15))
        self.assertTrue(self.processor._apply_operator(7, '>', 5))
        self.assertFalse(self.processor._apply_operator(3, '>', 5))
        self.assertTrue(self.processor._apply_operator(4, '<', 8))
        self.assertFalse(self.processor._apply_operator(10, '<', 8))
        
        # Test string equality
        self.assertTrue(self.processor._apply_operator('test', '=', 'test'))
        self.assertFalse(self.processor._apply_operator('test', '=', 'other'))

    def test_get_sample_attributes(self):
        """Test sample attribute extraction."""
        sample_data = pd.Series({
            'species': 'Escherichia coli',
            'assembly_type': 'short',
            'other_field': 'value'
        })
        
        # Load QC overrides first
        self.processor.load_input_files()
        
        attributes = self.processor._get_sample_attributes(sample_data)
        
        self.assertEqual(attributes['species'], 'Escherichia coli')
        self.assertIn('assembly_type', attributes)

    def test_rule_matches_criteria(self):
        """Test rule matching logic."""
        # Load input files to get QC overrides
        self.processor.load_input_files()
        
        # Test rule that matches all species
        rule = pd.Series({
            'species': 'all',
            'assembly_type': 'all',
            'software': 'checkm'
        })
        
        sample_attributes = {
            'species': 'Escherichia coli',
            'assembly_type': 'short'
        }
        
        self.assertTrue(
            self.processor._rule_matches_criteria(rule, sample_attributes)
        )
        
        # Test rule that doesn't match species
        rule_specific = pd.Series({
            'species': 'Salmonella enterica',
            'assembly_type': 'all',
            'software': 'checkm'
        })
        
        self.assertFalse(
            self.processor._rule_matches_criteria(
                rule_specific, sample_attributes
            )
        )


class TestFieldMapping(unittest.TestCase):
    """Unit tests for field mapping functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent.parent
        self.config_path = self.test_dir / "fixtures" / "config_example.yaml"
        self.processor = QCProcessor(str(self.config_path))
        self.processor.load_input_files()

    def test_build_field_mapping(self):
        """Test field mapping construction."""
        field_mapping = self.processor._build_field_mapping()
        
        self.assertIsInstance(field_mapping, dict)
        # Should have some mappings from our test data
        self.assertGreater(len(field_mapping), 0)

    def test_field_mapping_consistency(self):
        """Test that field mapping is consistent."""
        mapping1 = self.processor._build_field_mapping()
        mapping2 = self.processor._build_field_mapping()
        
        self.assertEqual(mapping1, mapping2)


if __name__ == '__main__':
    # Change to project root directory so relative paths work
    test_dir = Path(__file__).parent.parent
    import os
    os.chdir(test_dir.parent)
    
    # Run tests
    unittest.main(verbosity=2)
