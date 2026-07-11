@echo off
REM Run this on a Windows machine with Python installed to build NPIMasker.exe locally.
pip install -r requirements.txt pyinstaller
REM --collect-all bundles spaCy's dynamic language modules and the
REM en_core_web_sm model data, which PyInstaller can't discover on its own.
pyinstaller --onefile --windowed --name NPIMasker --collect-all spacy --collect-all en_core_web_sm main.py
echo.
echo Done. Find NPIMasker.exe in the dist\ folder.
