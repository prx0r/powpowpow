"""
PowPowPow Core — init

Re-exports from core.py (sibling) so `from core import X` works
regardless of whether Python finds the package or the module first.
"""

import importlib.util as _ilu
import os as _os
import sys as _sys

# Load core.py (sibling of this package) and merge its exports
_core_py_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'core.py')
if _os.path.exists(_core_py_path):
    _spec = _ilu.spec_from_file_location('_core_py_sibling', _core_py_path)
    _core = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_core)
    # Expose all public names + underscore-prefixed names from core.py
    for _name in dir(_core):
        if _name.startswith('_') and _name != '__all__':
            # Include _archive_raw and other private-but-used names
            if _name in ('_archive_raw',):
                globals()[_name] = getattr(_core, _name)
        elif not _name.startswith('_'):
            globals()[_name] = getattr(_core, _name)

from .primitives import *
from .warehouse_core import store_observation, read_observations
from .panel import store_panel_record, read_panel, PANEL_COLUMNS
from .btc_baseline import compute_btc_betas, compute_market_context
from .backtest_harness import BacktestHarness
