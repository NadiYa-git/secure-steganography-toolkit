import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_SIZE = 16
KDF_ITERATIONS = 390000


def _derive_key(password, salt):
    if not password:
        raise ValueError("Password cannot be empty.")
    if not isinstance(salt, (bytes, bytearray)) or len(salt) != SALT_SIZE:
        raise ValueError("Encryption salt is invalid.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_bytes(plain_bytes, password):
    if not password:
        raise ValueError("Password cannot be empty.")
    if plain_bytes is None:
        raise ValueError("No data provided for encryption.")

    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(bytes(plain_bytes))
    return salt + token


def decrypt_bytes(encrypted_bytes, password):
    if not password:
        raise ValueError("Password cannot be empty.")
    if not encrypted_bytes or len(encrypted_bytes) <= SALT_SIZE:
        raise ValueError("Encrypted data is corrupted or incomplete.")

    salt = encrypted_bytes[:SALT_SIZE]
    token = encrypted_bytes[SALT_SIZE:]
    key = _derive_key(password, salt)

    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Wrong password or corrupted data.") from exc
