# -*- coding: utf-8 -*-
"""
conftest.py for mreports.
"""

import pytest
import pathlib
import sys
from pypipegraph.testing.fixtures import new_pipegraph  # noqa:F401

root = pathlib.Path(".").parent.parent
sys.path.append(str(root / "src"))
