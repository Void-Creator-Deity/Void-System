"""Identity workflow: registration, sessions, profile, and password rotation."""
from __future__ import annotations

import hmac
import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from core.identity_contracts import IdentityRepository
from core.runtime_settings import RuntimeSettings
from adapters.sqlite.identity_repository import SQLiteIdentityRepository
from database import Database
from errors import ErrorCode, VoidSystemException, create_auth_error
from middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    token_digest,
    utc_now,
    utc_timestamp,
    verify_password,
)
from tools.utils import sanitize_string


logger = logging.getLogger(__name__)


class UserService:
    """Own the account lifecycle behind stable HTTP-facing operations."""

    def __init__(
        self,
        repository: IdentityRepository,
        settings: Optional[RuntimeSettings] = None,
    ):
        self.repository = repository
        self.settings = settings or RuntimeSettings.from_environment()

    def register_user(self, email: str, password: str, username: str) -> Dict[str, Any]:
        username = sanitize_string(username, 50).strip()
        email = email.strip().lower()
        if not username:
            raise VoidSystemException.from_error_code(ErrorCode.INVALID_REQUEST)
        if self.repository.get_user_by_email(email):
            raise VoidSystemException.from_error_code(ErrorCode.EMAIL_IN_USE)
        if self.repository.get_user_by_username(username):
            raise VoidSystemException.from_error_code(ErrorCode.USERNAME_IN_USE)

        user_id = self.repository.add_user(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
        )
        if not user_id:
            # The database unique constraints remain authoritative under concurrent requests.
            if self.repository.get_user_by_email(email):
                raise VoidSystemException.from_error_code(ErrorCode.EMAIL_IN_USE)
            raise VoidSystemException.from_error_code(ErrorCode.USERNAME_IN_USE)
        return {"user_id": user_id, "username": username, "email": email, "role": "user"}

    def authenticate_user(
        self,
        identifier: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        identifier = identifier.strip()
        if "@" in identifier:
            user = self.repository.get_user_by_email(identifier.lower())
        else:
            user = self.repository.get_user_by_username(identifier)
        if not user or not verify_password(password, user.get("password_hash") or ""):
            raise create_auth_error(ErrorCode.INVALID_CREDENTIALS)
        if not user.get("is_active", True):
            raise create_auth_error(ErrorCode.USER_INACTIVE)

        self.repository.update_last_login(user["user_id"])
        session_id = secrets.token_urlsafe(24)
        token_result = self._issue_token_pair(user, session_id)
        self.repository.create_auth_session(
            session_id=session_id,
            user_id=user["user_id"],
            refresh_token_hash=token_digest(token_result["refresh_token"]),
            expires_at=token_result["refresh_expires_at"],
            created_at=utc_timestamp(),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        logger.info("Login succeeded for user_id=%s", user["user_id"])
        return self._public_token_result(token_result, user)

    def refresh_user_token(self, refresh_token: str) -> Dict[str, Any]:
        payload = decode_token(refresh_token, "refresh", self.settings)
        user_id = str(payload["sub"])
        session_id = str(payload["sid"])
        user = self.repository.get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            raise create_auth_error(ErrorCode.TOKEN_INVALID)
        if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
            raise create_auth_error(ErrorCode.TOKEN_INVALID)

        session = self.repository.get_auth_session(session_id, user_id)
        refresh_hash = token_digest(refresh_token)
        if (
            not session
            or session.get("revoked_at")
            or not hmac.compare_digest(session["refresh_token_hash"], refresh_hash)
        ):
            if session and not session.get("revoked_at"):
                self.repository.revoke_auth_session(session_id, user_id, utc_timestamp())
            raise create_auth_error(ErrorCode.TOKEN_INVALID)

        token_result = self._issue_token_pair(user, session_id)
        if not self.repository.rotate_auth_session(
            session_id=session_id,
            user_id=user_id,
            expected_refresh_hash=refresh_hash,
            replacement_refresh_hash=token_digest(token_result["refresh_token"]),
            expires_at=token_result["refresh_expires_at"],
            used_at=utc_timestamp(),
        ):
            raise create_auth_error(ErrorCode.TOKEN_INVALID)
        logger.info("Refresh succeeded for user_id=%s", user_id)
        return self._public_token_result(token_result, user)

    def logout(self, user_id: str, session_id: str, all_sessions: bool = False) -> int:
        revoked_at = utc_timestamp()
        if all_sessions:
            return self.repository.revoke_all_auth_sessions(user_id, revoked_at)
        return int(self.repository.revoke_auth_session(session_id, user_id, revoked_at))

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)
        return self._public_user(user)

    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

        email = update_data.get("email")
        username = update_data.get("username")
        if email is not None:
            email = str(email).strip().lower()
            existing_user = self.repository.get_user_by_email(email)
            if existing_user and existing_user["user_id"] != user_id:
                raise VoidSystemException.from_error_code(ErrorCode.EMAIL_IN_USE)
        if username is not None:
            username = sanitize_string(str(username), 50).strip()
            existing_user = self.repository.get_user_by_username(username)
            if existing_user and existing_user["user_id"] != user_id:
                raise VoidSystemException.from_error_code(ErrorCode.USERNAME_IN_USE)

        changed = self.repository.update_user_profile(
            user_id=user_id,
            email=email,
            username=username,
            learning_goal=update_data.get("learning_goal"),
            specialization=update_data.get("specialization"),
        )
        if not changed:
            raise VoidSystemException.from_error_code(ErrorCode.INVALID_REQUEST)
        return self.get_user_profile(user_id)

    def change_user_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)
        if not verify_password(old_password, user.get("password_hash") or ""):
            raise create_auth_error(ErrorCode.INVALID_CREDENTIALS)
        if verify_password(new_password, user.get("password_hash") or ""):
            raise VoidSystemException.from_error_code(
                ErrorCode.PASSWORD_POLICY_VIOLATION,
                details={"reason": "新密码不能与当前密码相同"},
            )

        changed_at = utc_timestamp()
        if not self.repository.update_user_password(user_id, get_password_hash(new_password), changed_at):
            raise VoidSystemException.from_error_code(ErrorCode.SYSTEM_ERROR)
        self.repository.revoke_all_auth_sessions(user_id, changed_at)
        logger.info("Password rotated for user_id=%s", user_id)
        return True

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)
        return self.repository.get_user_stats(user_id)

    @staticmethod
    def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
        excluded = {"password_hash", "token_version", "password_changed_at"}
        return {key: value for key, value in user.items() if key not in excluded}

    def _issue_token_pair(self, user: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        version = int(user.get("token_version", 0))
        claims = {"sub": user["user_id"], "sid": session_id, "ver": version}
        now = utc_now()
        refresh_expires_at = now + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)
        return {
            "access_token": create_access_token(claims, self.settings),
            "refresh_token": create_refresh_token(claims, self.settings),
            "token_type": "bearer",
            "expires_in": self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_expires_at": utc_timestamp(refresh_expires_at),
        }

    def _public_token_result(self, token_result: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "access_token": token_result["access_token"],
            "refresh_token": token_result["refresh_token"],
            "token_type": token_result["token_type"],
            "expires_in": token_result["expires_in"],
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "level": user.get("level", 1),
                "role": user.get("role", "user"),
            },
        }


def get_user_service(
    db: Optional[Database] = None,
    settings: Optional[RuntimeSettings] = None,
) -> UserService:
    active_settings = settings or RuntimeSettings.from_environment()
    database = db or Database(active_settings.get_database_path())
    return UserService(SQLiteIdentityRepository(database.get_connection), active_settings)
