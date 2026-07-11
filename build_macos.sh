#!/bin/bash
# Run this on macOS to build NPIMasker.app locally for fast dev-loop testing.
set -e
pip3 install -r requirements.txt pyinstaller
pyinstaller --windowed --name NPIMasker main.py
echo
echo "Done. Find NPIMasker.app in the dist/ folder."
