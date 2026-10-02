"""Run the headless Blender tests.

From the repository root::

    blender -b --factory-startup --python tests/blender/run.py

Exits with status 1 if a test fails. The add-on is loaded from this checkout.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

suite = unittest.defaultTestLoader.discover(HERE, pattern="test_*.py", top_level_dir=HERE)
result = unittest.TextTestRunner(verbosity=2).run(suite)

import test_metrics  # noqa: E402
if test_metrics.MODULE_NAME in sys.modules:
    sys.modules[test_metrics.MODULE_NAME].unregister()  # registration must be reversible

sys.exit(0 if result.wasSuccessful() else 1)
