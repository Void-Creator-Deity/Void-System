"""Repair or reset a local SQLite administrator account without exposing stored hashes."""
from __future__ import annotations

import argparse
from getpass import getpass
import os
from pathlib import Path
import sqlite3
import sys
from typing import Optional


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.runtime_settings import RuntimeSettings
from database import Database
from middleware.auth import get_password_hash, utc_timestamp


def _database_path(value: Optional[str]) -> Path:
    if value:
        path = Path(value).expanduser()
        return path if path.is_absolute() else (Path.cwd() / path).resolve()
    settings = RuntimeSettings.from_environment(base_dir=BACKEND_ROOT)
    return Path(settings.get_database_path()).resolve()


def _validate_password(password: str) -> None:
    encoded_length = len(password.encode("utf-8"))
    if len(password) < 8 or encoded_length > 72:
        raise ValueError("密码必须至少包含 8 个字符，且不能超过 72 个字节")


def _find_admin(conn: sqlite3.Connection, identifier: Optional[str]) -> Optional[sqlite3.Row]:
    if identifier:
        return conn.execute(
            """SELECT * FROM users
               WHERE role = 'admin'
                 AND (user_id = ? OR username = ? OR lower(email) = lower(?))
               LIMIT 1""",
            (identifier, identifier, identifier),
        ).fetchone()
    return conn.execute(
        """SELECT * FROM users
           WHERE role = 'admin'
           ORDER BY CASE WHEN user_id = '0000' THEN 0 ELSE 1 END, created_at
           LIMIT 1"""
    ).fetchone()


def reset_local_admin(
    database_path: Path,
    password: str,
    *,
    identifier: Optional[str] = None,
    username: str = "admin",
    email: str = "admin@void-system.com",
) -> dict[str, str]:
    """Reset one existing local administrator and revoke all of its sessions."""
    _validate_password(password)
    username = username.strip()
    email = email.strip().lower()
    if not username or len(username) > 50:
        raise ValueError("管理员用户名必须包含 1 到 50 个字符")
    if not email or "@" not in email:
        raise ValueError("请提供有效的管理员邮箱")
    if not database_path.exists():
        raise FileNotFoundError(f"数据库不存在：{database_path}")

    Database(str(database_path)).close()
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        admin = _find_admin(conn, identifier)
        if admin is None:
            target = f"：{identifier}" if identifier else ""
            raise LookupError(f"没有找到管理员账号{target}")

        duplicate = conn.execute(
            """SELECT user_id FROM users
               WHERE user_id != ? AND (username = ? OR lower(email) = lower(?))
               LIMIT 1""",
            (admin["user_id"], username, email),
        ).fetchone()
        if duplicate:
            raise ValueError("新的用户名或邮箱已被其他账号使用")

        changed_at = utc_timestamp()
        with conn:
            conn.execute(
                """UPDATE users
                   SET username = ?, email = ?, password_hash = ?, role = 'admin',
                       is_active = 1, password_changed_at = ?,
                       token_version = COALESCE(token_version, 0) + 1
                   WHERE user_id = ?""",
                (username, email, get_password_hash(password), changed_at, admin["user_id"]),
            )
            conn.execute(
                """UPDATE auth_sessions
                   SET revoked_at = COALESCE(revoked_at, ?)
                   WHERE user_id = ?""",
                (changed_at, admin["user_id"]),
            )
        return {"user_id": str(admin["user_id"]), "username": username, "email": email}
    finally:
        conn.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="重置本地 SQLite 数据库中的管理员账号，并撤销旧登录会话。"
    )
    parser.add_argument("--database", help="SQLite 数据库路径；默认读取当前后端配置")
    parser.add_argument("--identifier", help="现有管理员的用户编号、用户名或邮箱")
    parser.add_argument("--username", default="admin", help="重置后的管理员用户名")
    parser.add_argument("--email", default="admin@void-system.com", help="重置后的管理员邮箱")
    parser.add_argument(
        "--password-env",
        default="VOID_ADMIN_PASSWORD",
        help="读取新密码的环境变量名；未设置时安全地交互输入",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    password = os.environ.get(args.password_env) or getpass("新管理员密码：")
    if args.password_env not in os.environ:
        confirmation = getpass("再次输入：")
        if password != confirmation:
            raise SystemExit("两次输入的密码不一致")
    try:
        result = reset_local_admin(
            _database_path(args.database),
            password,
            identifier=args.identifier,
            username=args.username,
            email=args.email,
        )
    except (FileNotFoundError, LookupError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"管理员已重置：{result['username']} ({result['email']})，旧会话已撤销。")


if __name__ == "__main__":
    main()
