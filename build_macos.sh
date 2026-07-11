#!/bin/bash
# Run this on macOS to build NPIMasker.app locally for fast dev-loop testing.
#
# Uses Homebrew's python-tk (modern Tcl/Tk 8.6+/9) instead of Apple's system
# Python, whose bundled Tcl/Tk 8.5 is deprecated and renders blank windows on
# recent macOS. Install once with: brew install python@3.12 python-tk@3.12
set -e

PYTHON_BIN="/opt/homebrew/bin/python3.12"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/local/bin/python3.12"  # Intel Homebrew prefix
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Homebrew python3.12 not found. Install it with:"
  echo "  brew install python@3.12 python-tk@3.12"
  exit 1
fi

cd "$(dirname "$0")"
"$PYTHON_BIN" -m venv .venv
.venv/bin/pip install -r requirements.txt pyinstaller
.venv/bin/pyinstaller --windowed --name NPIMasker main.py

echo
echo "Done. Find NPIMasker.app in the dist/ folder."
