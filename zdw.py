#!/usr/bin/env python3
"""Top-level entry point for the Zero Day Warranty solution.

Run ``python zdw.py`` for the framework overview, or a subcommand
(``run`` · ``calc`` · ``validate``). This shim makes the ``src/`` package
importable without an install, mirroring APEX's top-level ``apex.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from zero_day_warranty.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
