"""Authentication primitives shared by the HTTP identity workflow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from core.runtime_settings import RuntimeSettings
from database import Database
from errors import ErrorCode, VoidSystemException


logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token", auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: Optional[datetime] = None) -> str:
    return (value or utc_now()).isoformat()


def token_digest(token: str) -> str:
    """Return a non-reversible digest suitable for refresh-token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_token(
    data: Dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
    settings: Any = None,
) -> str:
    active_settings = settings or RuntimeSettings.from_environment()
    payload = data.copy()
    now = utc_now()
    payload.pop("expires_delta", None)
    payload["type"] = token_type
    payload.setdefault("iat", now)
    payload.setdefault("jti", secrets.token_urlsafe(18))
    payload.setdefault("exp", now + expires_delta)
    return jwt.encode(payload, active_settings.SECRET_KEY, algorithm=active_settings.ALGORITHM)


def create_access_token(data: Dict[str, Any], settings: Any = None) -> str:
    """Create a short-lived access token with an explicit purpose claim."""
    active_settings = settings or RuntimeSettings.from_environment()
    expires_delta = data.get("expires_delta") or timedelta(
        minutes=active_settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _create_token(data, "access", expires_delta, active_settings)


def create_refresh_token(data: Dict[str, Any], settings: Any = None) -> str:
    """Create a long-lived refresh token with an explicit purpose claim."""
    active_settings = settings or RuntimeSettings.from_environment()
    expires_delta = data.get("expires_delta") or timedelta(
        days=active_settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return _create_token(data, "refresh", expires_delta, active_settings)


def decode_token(token: str, expected_type: str, settings: Any = None) -> Dict[str, Any]:
    """Decode one JWT and reject tokens minted for another purpose."""
    active_settings = settings or RuntimeSettings.from_environment()
    try:
        payload = jwt.decode(
            token,
            active_settings.SECRET_KEY,
            algorithms=[active_settings.ALGORITHM],
        )
    except JWTError as exc:
        logger.info("JWT decode rejected: %s", exc)
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID) from exc

    if payload.get("type") != expected_type:
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    if not payload.get("sub") or not payload.get("sid"):
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    return payload


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError) as exc:
        logger.warning("Password verification rejected: %s", exc)
        return False


def get_password_hash(password: str) -> str:
    if not password or len(password.encode("utf-8")) > 72:
        raise VoidSystemException.from_error_code(
            ErrorCode.PASSWORD_POLICY_VIOLATION,
            details={"reason": "密码必须为 1 到 72 个字节"},
        )
    try:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception as exc:
        logger.exception("Password hashing failed")
        raise VoidSystemException.from_error_code(
            ErrorCode.SYSTEM_ERROR,
            details={"operation": "password_hashing"},
        ) from exc


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Database = Depends(lambda: Database(RuntimeSettings.from_environment().get_database_path())),
) -> Optional[Dict[str, Any]]:
    """Legacy dependency retained for callers outside the application factory."""
    if not token:
        return None
    payload = decode_token(token, "access")
    user = db.get_user_by_id(str(payload["sub"]))
    if not user or not user.get("is_active", True):
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    session = db.get_auth_session(str(payload["sid"]), user["user_id"])
    if not session or session.get("revoked_at"):
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_INVALID)
    user["auth_session_id"] = str(payload["sid"])
    return user


def require_authentication(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> Dict[str, Any]:
    if current_user is None:
        raise VoidSystemException.from_error_code(ErrorCode.TOKEN_MISSING)
    return current_user


def require_admin_role(
    current_user: Dict[str, Any] = Depends(require_authentication),
) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise VoidSystemException.from_error_code(
            ErrorCode.INSUFFICIENT_PERMISSIONS,
            details={"required_role": "admin", "user_role": current_user.get("role")},
        )
    return current_user
