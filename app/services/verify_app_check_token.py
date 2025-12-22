import os
from typing import Any, Dict, Optional, Tuple

import firebase_admin
import jwt
from firebase_admin import app_check, credentials
from firebase_admin.exceptions import FirebaseError


def initialize_firebase() -> None:
    sa_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE")
    if sa_path:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()


def normalize_app_check_token(raw_value: str) -> str:
    if not raw_value:
        return ""
    token = raw_value.strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    return token


def safe_token_debug(token: str) -> str:
    if not token:
        return "missing"
    return f"length={len(token)} segments={len(token.split('.'))}"


def is_jwt_like(token: str) -> bool:
    return bool(token) and token.count(".") == 2


def verify_app_check_token(token: str) -> Dict[str, Any]:
    initialize_firebase()
    return app_check.verify_token(token)


def verify_app_check_token_safe(
    raw_token: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Safe wrapper that:
    - normalizes the input (handles optional 'Bearer ')
    - rejects obvious non-token input (wrong segment count)
    - returns (claims, error_message)

    This avoids raising exceptions in your calling code.

    Args:
      raw_token: Raw token string from client/header/storage.

    Returns:
      (claims, None) on success
      (None, error_message) on failure
    """
    token = normalize_app_check_token(raw_token)

    if not token:
        return None, "Missing App Check token"

    if not is_jwt_like(token):
        return (
            None,
            f"Token is not JWT-like (expected 3 segments). {safe_token_debug(token)}",
        )

    try:
        claims = verify_app_check_token(token)
        return claims, None
    except (ValueError, jwt.exceptions.DecodeError, FirebaseError) as e:
        return None, f"Invalid App Check token: {e}"
