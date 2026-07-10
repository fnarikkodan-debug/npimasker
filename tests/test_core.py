import csv
import os

import pytest

from npimasker.crypto import WrongKeyError, derive_key, generate_passphrase
from npimasker.csv_processor import process_csv, read_headers
from npimasker.sensitive_fields import detect_sensitive_columns

HEADERS = ["ID", "Full Name", "Email", "Phone Number", "Address", "Notes"]
ROWS = [
    ["1", "Jane Doe", "jane@example.com", "555-1234", "12 Elm St", "vip"],
    ["2", "John Smith", "john@example.com", "", "88 Oak Ave", ""],
]


def _write_sample_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(ROWS)


def test_detect_sensitive_columns():
    indices = detect_sensitive_columns(HEADERS)
    assert indices == [1, 2, 3, 4]  # Name, Email, Phone Number, Address
    assert 0 not in indices  # ID
    assert 5 not in indices  # Notes


def test_read_headers(tmp_path):
    path = tmp_path / "in.csv"
    _write_sample_csv(path)
    assert read_headers(str(path)) == HEADERS


def test_encrypt_decrypt_round_trip(tmp_path):
    input_path = tmp_path / "in.csv"
    encrypted_path = tmp_path / "encrypted.csv"
    decrypted_path = tmp_path / "decrypted.csv"
    _write_sample_csv(input_path)

    key = derive_key("correct-horse-battery-staple")
    sensitive_cols = detect_sensitive_columns(HEADERS)

    process_csv(str(input_path), str(encrypted_path), key, "encrypt", sensitive_cols)

    with open(encrypted_path, newline="", encoding="utf-8") as f:
        enc_rows = list(csv.reader(f))
    assert enc_rows[0] == HEADERS
    # Sensitive cells changed, non-sensitive cells untouched.
    assert enc_rows[1][1] != "Jane Doe"
    assert enc_rows[1][0] == "1"  # ID
    assert enc_rows[1][5] == "vip"  # Notes
    assert enc_rows[2][3] == ""  # empty Phone Number cell stays empty, not encrypted

    process_csv(str(encrypted_path), str(decrypted_path), key, "decrypt", sensitive_cols)

    with open(decrypted_path, newline="", encoding="utf-8") as f:
        dec_rows = list(csv.reader(f))
    assert dec_rows[0] == HEADERS
    assert dec_rows[1:] == ROWS


def test_wrong_key_raises_clear_error(tmp_path):
    input_path = tmp_path / "in.csv"
    encrypted_path = tmp_path / "encrypted.csv"
    decrypted_path = tmp_path / "decrypted.csv"
    _write_sample_csv(input_path)

    right_key = derive_key("right-key")
    wrong_key = derive_key("wrong-key")
    sensitive_cols = detect_sensitive_columns(HEADERS)

    process_csv(str(input_path), str(encrypted_path), right_key, "encrypt", sensitive_cols)

    with pytest.raises(WrongKeyError):
        process_csv(str(encrypted_path), str(decrypted_path), wrong_key, "decrypt", sensitive_cols)


def test_generate_passphrase_is_random_and_derives_stable_key():
    p1 = generate_passphrase()
    p2 = generate_passphrase()
    assert p1 != p2
    assert derive_key(p1) == derive_key(p1)
    assert derive_key(p1) != derive_key(p2)
