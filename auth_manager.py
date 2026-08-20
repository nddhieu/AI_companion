import hashlib
import os
import secrets
from typing import Dict, Optional, Any, List

DEFAULT_USER_ID = "default_user"
DEFAULT_USER_NAME = "default"
DEFAULT_DISPLAY_NAME = "My Space"

def hash_pin_or_password(secret: str, salt: Optional[str] = None) -> Dict[str, str]:
    """Hashes a user PIN or password with salt using SHA-256."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + secret).encode("utf-8")).hexdigest()
    return {"salt": salt, "hash": f"{salt}:{hashed}"}

def verify_pin_or_password(secret: str, stored_hash: str) -> bool:
    """Verifies a secret against a stored 'salt:hash' string."""
    if not stored_hash:
        return True  # No PIN set
    try:
        parts = stored_hash.split(":")
        if len(parts) != 2:
            return False
        salt, expected_hash = parts
        computed_hash = hashlib.sha256((salt + secret).encode("utf-8")).hexdigest()
        return secrets.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False
