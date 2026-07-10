"""CSV reading/writing and encrypt/decrypt orchestration for NPIMasker."""

import csv

from npimasker.crypto import WrongKeyError, decrypt_value, encrypt_value


def read_headers(input_path: str) -> list[str]:
    """Read just the header row of a CSV, for building a column checklist."""
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        return next(reader, [])


def process_csv(
    input_path: str,
    output_path: str,
    key: bytes,
    mode: str,
    selected_columns: list[int],
) -> None:
    """Encrypt or decrypt the selected columns of a CSV, row by row.

    Columns not in `selected_columns` are copied through unchanged.
    Raises WrongKeyError (with row/column context) if a decrypt fails.
    """
    if mode not in ("encrypt", "decrypt"):
        raise ValueError(f"Unknown mode: {mode!r}")
    transform = encrypt_value if mode == "encrypt" else decrypt_value
    selected = set(selected_columns)

    with open(input_path, newline="", encoding="utf-8-sig") as infile, open(
        output_path, "w", newline="", encoding="utf-8"
    ) as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        headers = next(reader, None)
        if headers is None:
            raise ValueError("Input CSV is empty.")
        writer.writerow(headers)

        for row_num, row in enumerate(reader, start=2):
            new_row = list(row)
            for idx in selected:
                if idx >= len(new_row):
                    continue
                try:
                    new_row[idx] = transform(new_row[idx], key)
                except WrongKeyError as exc:
                    column_name = headers[idx] if idx < len(headers) else str(idx)
                    raise WrongKeyError(
                        f"{exc} (row {row_num}, column '{column_name}')"
                    ) from exc
            writer.writerow(new_row)
