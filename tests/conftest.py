# -*- coding: utf-8 -*-
"""
conftest.py for mreports.
"""

import pytest
import pathlib
import sys
import pypipegraph2 as ppg2  # noqa: F401
import pypipegraph as ppg  # noqa: F401

from pypipegraph.testing.fixtures import new_pipegraph  # noqa:F401

root = pathlib.Path(".").parent.parent
sys.path.append(str(root / "src"))

ppg2.replace_ppg1()


@pytest.fixture
def new_pipegraph_no_qc(new_pipegraph):
    ppg.util.global_pipegraph._qc_keep_function = False
    return new_pipegraph
    # this really does not work :(


@pytest.fixture
def both_ppg_and_no_ppg_no_qc(both_ppg_and_no_ppg):
    if ppg.util.global_pipegraph is not None:
        ppg.util.global_pipegraph._qc_keep_function = False
    return both_ppg_and_no_ppg
