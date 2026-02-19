#!/usr/bin/env python3
"""
Full test suite for madOS Bluetooth.

Run all Bluetooth tests together.
"""

import sys
import os
import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    suite.addTests(loader.loadTestsFromName("tests.test_bluetooth_backend"))
    suite.addTests(loader.loadTestsFromName("tests.test_bluetooth_frontend"))
    suite.addTests(loader.loadTestsFromName("tests.test_bluetooth_integration"))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
