import csv
import os

import pytest

from npimasker.crypto import (
    WrongKeyError,
    decrypt_text_spans,
    derive_key,
    encrypt_text_spans,
    generate_passphrase,
)
from npimasker.csv_processor import process_csv, read_headers
from npimasker.pii_detect import find_pii_spans
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


def test_find_pii_spans_regex_detectors():
    text = "Contact me at jane.doe@example.com re: SSN 123-45-6789, DOB 03/14/1990"
    spans = find_pii_spans(text)
    found = {text[start:end] for start, end in spans}
    assert "jane.doe@example.com" in found
    assert "123-45-6789" in found
    assert "03/14/1990" in found


def test_find_pii_spans_detects_embedded_person_name():
    text = "a person have walked in and his name is Kang Li"
    spans = find_pii_spans(text)
    found = [text[start:end] for start, end in spans]
    assert "Kang Li" in found
    # Everything else in the sentence is untouched by detection.
    assert text[: text.index("Kang Li")] == "a person have walked in and his name is "


def test_find_pii_spans_catches_name_mislabeled_as_org():
    # The small NER model tags "Lilly" as ORG (not PERSON) and leaves
    # "petlock" unlabeled entirely; ORG inclusion + rightward extension
    # must still cover the full name.
    text = "working on case for Lilly petlock"
    spans = find_pii_spans(text)
    found = [text[start:end] for start, end in spans]
    assert "Lilly petlock" in found


def test_find_pii_spans_extension_stops_at_other_entities():
    # "yesterday" is a DATE entity and must not be swallowed into the name.
    text = "spoke with Kang Li yesterday"
    spans = find_pii_spans(text)
    found = [text[start:end] for start, end in spans]
    assert "Kang Li" in found
    assert all("yesterday" not in f for f in found)


def test_encrypt_decrypt_text_spans_round_trip():
    key = derive_key("span-key")
    text = "a person have walked in and his name is Kang Li"
    start = text.index("Kang Li")
    end = start + len("Kang Li")

    encrypted = encrypt_text_spans(text, [(start, end)], key)
    assert "Kang Li" not in encrypted
    assert encrypted.startswith("a person have walked in and his name is [[ENC:")
    assert encrypted.endswith("]]")

    decrypted = decrypt_text_spans(encrypted, key)
    assert decrypted == text


def test_encrypt_text_spans_no_spans_is_a_no_op():
    key = derive_key("span-key")
    text = "nothing sensitive here"
    assert encrypt_text_spans(text, [], key) == text
    assert decrypt_text_spans(text, key) == text


def test_free_text_column_only_encrypts_detected_pii(tmp_path):
    headers = ["ID", "Notes"]
    sentence = "a person have walked in and his name is Kang Li"
    rows = [["1", sentence]]

    input_path = tmp_path / "in.csv"
    with open(input_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    key = derive_key("notes-key")
    encrypted_path = tmp_path / "encrypted.csv"
    decrypted_path = tmp_path / "decrypted.csv"

    process_csv(str(input_path), str(encrypted_path), key, "encrypt", [1])

    with open(encrypted_path, newline="", encoding="utf-8") as f:
        enc_rows = list(csv.reader(f))
    encrypted_notes = enc_rows[1][1]
    assert "Kang Li" not in encrypted_notes
    # The rest of the sentence, up to the name, is untouched.
    assert encrypted_notes.startswith("a person have walked in and his name is ")

    process_csv(str(encrypted_path), str(decrypted_path), key, "decrypt", [1])

    with open(decrypted_path, newline="", encoding="utf-8") as f:
        dec_rows = list(csv.reader(f))
    assert dec_rows[1][1] == sentence


def test_whole_cell_categories_still_used_for_name_phone_address():
    from npimasker.sensitive_fields import is_whole_cell_header

    assert is_whole_cell_header("Full Name")
    assert is_whole_cell_header("Phone Number")
    assert is_whole_cell_header("Address")
    assert not is_whole_cell_header("Email")
    assert not is_whole_cell_header("Notes")
