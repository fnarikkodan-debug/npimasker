"""Key generation/derivation and per-value encryption for NPIMasker.

Keys are arbitrary user-supplied strings (a passphrase, or a random string
from `generate_passphrase`). They are run through PBKDF2 with a fixed,
application-level salt to produce a Fernet-compatible key. The fixed salt
is a deliberate simplicity trade-off for a local, single-user tool: it
means the same key string always derives the same encryption key without
needing to store/transmit a per-file salt. Per-value randomness still
comes from Fernet's own IV, so identical cells don't produce identical
ciphertext.
"""

import base64
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_APP_SALT = b"npimasker-v1-fixed-salt"
_KDF_ITERATIONS = 480_000


class WrongKeyError(Exception):
    """Raised when a value can't be decrypted with the given key."""


def generate_passphrase() -> str:
    """Generate a strong random key string for the user to save."""
    return secrets.token_urlsafe(32)


def derive_key(passphrase: str) -> bytes:
    """Derive a Fernet-compatible key from an arbitrary passphrase string."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_APP_SALT,
        iterations=_KDF_ITERATIONS,
    )
    derived = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


def encrypt_value(value: str, key: bytes) -> str:
    """Encrypt a single cell value. Empty values pass through unchanged."""
    if value == "":
        return value
    return Fernet(key).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str, key: bytes) -> str:
    """Decrypt a single cell value. Empty values pass through unchanged."""
    if token == "":
        return token
    try:
        return Fernet(key).decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise WrongKeyError(
            "Wrong key or corrupted file: could not decrypt a value."
        ) from exc
