# NPIMasker

A small local tool that encrypts sensitive columns (name, email, phone, address,
SSN, date of birth, NPI/medical record/insurance ID, etc.) in a CSV file, and
decrypts them back with the same key. Everything runs locally — no data is sent
anywhere.

## Using the Windows app

1. Get `NPIMasker.exe` (see "Building the .exe" below) and double-click it.
2. Choose **Encrypt** or **Decrypt**.
3. Click **Browse...** and pick your CSV file. The column list will show every
   column, with sensitive-looking ones (name, email, phone, address, etc.)
   already checked — untick/tick as needed.
4. Set the key:
   - First time: click **Generate & Save Key...** to create a strong random
     key and save it to a `.key` file. **Keep this file safe** — anyone who
     has it (and the encrypted CSV) can decrypt your data, and without it the
     data cannot be recovered by anyone, including you.
   - To decrypt later, or to encrypt more files with the same key: click
     **Load Key from File...** and pick that same `.key` file.
5. Confirm the output path (auto-filled next to the input file) and click
   **Run**.
6. Store or send the encrypted CSV and the `.key` file **separately** (e.g.
   don't email them in the same message).

If you decrypt with the wrong key, or a value got corrupted, NPIMasker shows
a clear error instead of silently producing garbage.

## Building the app

- **Windows (.exe):**
  - **GitHub Actions (recommended):** push this repo to GitHub. The workflow
    in `.github/workflows/build-exe.yml` builds `NPIMasker.exe` on a Windows
    runner automatically and attaches it as a downloadable artifact on the
    Actions run.
  - **Build it yourself on a Windows PC:** install Python 3.11+, then run
    `build_windows.bat` in this folder. The exe will be in `dist\NPIMasker.exe`.
- **macOS (.app), for testing locally while developing:**
  - Run `./build_macos.sh` in this folder (installs PyInstaller if needed).
    The app will be at `dist/NPIMasker.app` — double-click it, or `open
    dist/NPIMasker.app` from the terminal.
  - The same GitHub Actions workflow also builds `NPIMasker-macos` on a
    `macos-latest` runner and uploads it as an artifact on every push, so you
    don't have to build locally if you don't want to.

## Running from source (any OS, for development)

```
pip install -r requirements.txt
python main.py
```

**macOS note:** Apple's built-in `python3` (`/usr/bin/python3`) links against
the system Tcl/Tk 8.5, which is deprecated and known to render a **blank
window** on recent macOS versions. If you see a blank window or a
`DEPRECATION WARNING` about system Tk, install a Python build with a modern
Tk instead:

```
brew install python@3.12 python-tk@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

`build_macos.sh` already does this automatically (it creates its own `.venv`
using Homebrew's `python3.12`), so packaged `.app` builds aren't affected —
this only matters when running `main.py` directly with `python3`.

## Running the tests

```
pip install -r requirements.txt pytest
pytest tests/
```

## How the encryption works

- Each sensitive cell is encrypted independently with
  [Fernet](https://cryptography.io/en/latest/fernet/) (AES-128 + HMAC), so
  identical values in different cells produce different ciphertext.
- The key you provide (or generate) is run through PBKDF2-HMAC-SHA256 with a
  fixed, application-level salt to derive the actual encryption key. This is
  a deliberate simplicity trade-off for a local, single-user tool: it means
  a given key string always derives the same encryption key without needing
  to manage a separate salt file. If you need protection against attackers
  who might precompute keys for this fixed salt, don't reuse a weak/guessable
  key — use **Generate & Save Key** rather than typing your own passphrase.
- Only the columns you select are touched; everything else in the CSV is
  copied through unchanged.
