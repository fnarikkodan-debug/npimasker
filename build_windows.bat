@echo off
REM Run this on a Windows machine with Python installed to build NPIMasker.exe locally.
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name NPIMasker main.py
echo.
echo Done. Find NPIMasker.exe in the dist\ folder.
