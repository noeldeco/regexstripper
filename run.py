#!/usr/bin/env python
"""
Launcher script for Regex Stripper
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.app import main

if __name__ == "__main__":
    sys.exit(main())

