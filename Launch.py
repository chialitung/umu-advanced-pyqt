#!/usr/bin/env python3
"""Launch the UMU Advanced PyQt6 GUI directly."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on the path so the gui package is importable
SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gui.main import main

if __name__ == "__main__":
    main()
