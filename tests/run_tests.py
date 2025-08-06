#!/usr/bin/env python3
"""
Test runner for uQCme

Simple script to run the uQCme test suite.
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run the uQCme test suite."""
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent
    
    print("🧪 Running uQCme Test Suite")
    print("=" * 50)
    
    # Change to root directory
    import os
    os.chdir(root_dir)
    
    # Run tests
    cmd = [sys.executable, '-m', 'pytest', 'tests/test_uQCme_outcomes.py', '-v']
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
