"""Portable persistence contract for account identity and device sessions."""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class IdentityRepository(Protocol):
    """Own user records, profile mutations, and authentication session state."""

    def add_user(self, username: str, email: Optional[str], password_hash: Optional[str]) -> Optional[str]: ...
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]: ...
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]: ...
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    def update_last_login(self, user_id: str) -> None: ...
    def update_user_profile(
        self,
        user_id: str,
        *,
        email: Optional[str],
        username: Optional[str],
        learning_goal: Optional[str],
        specialization: Optional[str],
    ) -> bool: ...
    def update_user_password(self, user_id: str, password_hash: str, changed_at: str) -> bool: ...
    def get_user_stats(self, user_id: str) -> Dict[str, Any]: ...
    def create_auth_session(
        self,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: str,
        created_at: str,
        user_agent: Optional[str],
        ip_address: Optional[str],
    ) -> None: ...
    def get_auth_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]: ...
    def rotate_auth_session(
        self,
        session_id: str,
        user_id: str,
        expected_refresh_hash: str,
        replacement_refresh_hash: str,
        expires_at: str,
        used_at: str,
    ) -> bool: ...
    def revoke_auth_session(self, session_id: str, user_id: str, revoked_at: str) -> bool: ...
    def revoke_all_auth_sessions(self, user_id: str, revoked_at: str) -> int: ...
