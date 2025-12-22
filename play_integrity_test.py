"""
Firebase App Check token verification helpers + a simple CLI test (no Flask/FastAPI).

Prereqs:
- pip install firebase-admin PyJWT
- Provide Firebase Admin credentials via ONE of:
  1) env var: GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json
  2) env var: FIREBASE_SERVICE_ACCOUNT_FILE=/path/to/serviceAccountKey.json

Usage:
- Verify a token:
    python play_integrity_test.py --token "<APP_CHECK_TOKEN>"
  or:
    python play_integrity_test.py --token "Bearer <APP_CHECK_TOKEN>"

Notes:
- App Check tokens are JWT-like and should have 3 dot-separated segments.
- This verifies Firebase App Check tokens (NOT Play Integrity tokens).
- This file intentionally contains no web framework code.
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Dict, Optional, Tuple

import firebase_admin
import jwt
from firebase_admin import app_check, credentials
from firebase_admin.exceptions import FirebaseError

FIREBASE_SERVICE_ACCOUNT_FILE = (
    "work-code-643cd-firebase-adminsdk-fbsvc-e362113862.json"
)


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK once (idempotent).

    Resolution order:
    - If FIREBASE_SERVICE_ACCOUNT_FILE is set, use it explicitly.
    - Otherwise rely on application default credentials (GOOGLE_APPLICATION_CREDENTIALS).
    """
    try:
        sa_path = FIREBASE_SERVICE_ACCOUNT_FILE
        if sa_path:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    except ValueError:
        # Already initialized in this process.
        pass


def normalize_app_check_token(raw_value: str) -> str:
    """
    Accept either:
      - "<token>"
      - "Bearer <token>"

    Returns:
      Normalized token string, or "" if missing/empty.
    """
    if not raw_value:
        return ""
    token = raw_value.strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    return token


def safe_token_debug(token: str) -> str:
    """
    Safe-to-log token summary (never logs token contents).
    """
    if not token:
        return "missing"
    return f"length={len(token)} segments={len(token.split('.'))}"


def is_jwt_like(token: str) -> bool:
    """
    App Check tokens are JWT-like (3 segments).
    """
    return bool(token) and token.count(".") == 2


def verify_app_check_token(token: str) -> Dict[str, Any]:
    """
    Verify an App Check token and return decoded claims.

    Raises:
      ValueError / jwt.exceptions.DecodeError / FirebaseError
    """
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


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Firebase App Check token (server-side)."
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("APP_CHECK_TOKEN", ""),
        help="App Check token string (or set APP_CHECK_TOKEN env var).",
    )
    args = parser.parse_args()

    claims, err = verify_app_check_token_safe(args.token)
    if err:
        print(err)
        return 1

    # Print a small, useful subset (avoid dumping everything unless you want to).
    app_id = claims.get("app_id", "<unknown>")
    exp = claims.get("exp")
    iat = claims.get("iat")
    print("App Check token verified.")
    print(f"app_id={app_id}")
    print(f"iat={iat}")
    print(f"exp={exp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
