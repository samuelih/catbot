"""Root conftest for pytest."""

import sys
import os

# Ensure 'src' imports work without installing the package
sys.path.insert(0, os.path.dirname(__file__))
