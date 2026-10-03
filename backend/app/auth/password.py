"""
Phase 10.2 — Password Hashing Service.

Uses passlib + bcrypt for secure password storage.
- Plaintext passwords are NEVER logged or stored.
- password_hash is NEVER returned in API responses.
"""

import bcrypt

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        plain_password: The user's plaintext password.

    Returns:
        The bcrypt hash string — safe to store in the database.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: The password submitted by the user.
        hashed_password: The hash stored in the database.

    Returns:
        True if the password matches; False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except ValueError:
        return False
