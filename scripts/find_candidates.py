#!/usr/bin/env python3
"""Stage 2 - Completeness-first candidate clause ledger.

This stage exists because of one specific, reproducible failure: a language model
reading a policy end to end finds the headline obligations and misses the clause
in the annexure, the proviso in a footnote, and the TAT hiding in a table cell.
Deterministic pattern matching has poor precision and excellent recall, which is
exactly the right trade here - it produces the denominator against which Stage 3
completeness is measured.

Two ledgers are produced:
  * sentence candidates - any sentence carrying binding, timing, governance or
    conditional language
  * numeric candidates  - every money value, percentage, duration, count and
    threshold anywhere in the document, including table cells

Every candidate must later carry a disposition: mapped / non_binding /
queued_for_review. `validate_pack.py` fails the run while any stay `pending`.

Usage:
    python3 find_candidates.py --kb ./kb --doc-id ALL

Exit codes: 0 = ledger written; 1 = source layer missing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from assert_live_version import assert_live
except Exception:  # pragma: no cover
    assert_live = None  # type: ignore
