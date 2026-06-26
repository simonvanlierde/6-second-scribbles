"""Password hashing helpers.

Use Argon2id for password hashing and verification.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

_ARGON2_PREFIX = "$argon2"


class PasswordService:
    """Hash and verify passwords using Argon2id."""

    def __init__(self) -> None:
        self._argon2 = PasswordHasher()

    def hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        return self._argon2.hash(password)

    def verify_password(self, password: str, password_hash: str | None) -> bool:
        """Verify a password against a stored hash."""
        if not password_hash or not password_hash.startswith(_ARGON2_PREFIX):
            return False

        try:
            return self._argon2.verify(password_hash, password)
        except VerificationError:
            return False


password_service = PasswordService()
