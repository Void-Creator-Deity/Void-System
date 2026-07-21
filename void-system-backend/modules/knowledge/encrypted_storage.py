"""Authenticated encryption for knowledge source files at rest."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.runtime_settings import RuntimeSettings


class KnowledgeSourceCipher:
    """Encrypt and decrypt source bytes without exposing the key to API clients.

    Inputs:
        RuntimeSettings with DOCUMENT_ENCRYPTION_KEY or a local key-file location.
    Outputs:
        Authenticated ciphertext for source files and original bytes for trusted ingestion workers.
    Called by:
        PersonalKnowledgeDocumentManager when persisting or reading a private source.
    Side effects:
        In development, creates a stable local key file once when an explicit key is absent.
    Security:
        The Fernet key is never stored in SQLite, Chroma, API responses, or browser storage.
    """

    VERSION = "fernet-v1"
    _TOKEN_PREFIX = b"gAAAA"

    def __init__(self, settings: Optional[RuntimeSettings], storage_root: Path) -> None:
        self._settings = settings
        self._storage_root = storage_root
        self._fernet = Fernet(self._resolve_key())

    def _resolve_key(self) -> bytes:
        configured = str(getattr(self._settings, "DOCUMENT_ENCRYPTION_KEY", "") or "").strip()
        if configured:
            try:
                Fernet(configured.encode("ascii"))
                return configured.encode("ascii")
            except (ValueError, UnicodeEncodeError) as exc:
                raise RuntimeError("DOCUMENT_ENCRYPTION_KEY must be a valid Fernet key") from exc
        if self._settings is not None and self._settings.is_production():
            raise RuntimeError("Production requires DOCUMENT_ENCRYPTION_KEY for private knowledge files")
        configured_file = str(getattr(self._settings, "DOCUMENT_ENCRYPTION_KEY_FILE", "") or "").strip()
        base_dir = Path(getattr(self._settings, "BASE_DIR", self._storage_root))
        canonical_file = base_dir / ".keys" / "document-fernet.key"
        legacy_file = self._storage_root / ".keys" / "document-fernet.key"
        key_file = Path(configured_file) if configured_file else canonical_file
        if not configured_file and not canonical_file.exists() and legacy_file.exists():
            # One-time key-location migration. Runtime never keeps a fallback
            # reference to the retired user_documents/.keys location.
            canonical_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(legacy_file, canonical_file)
            except OSError as exc:
                raise RuntimeError("Could not migrate the retired local knowledge key location") from exc
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists():
            key = key_file.read_bytes().strip()
            try:
                Fernet(key)
                return key
            except ValueError as exc:
                raise RuntimeError("Local knowledge encryption key is invalid") from exc
        key = Fernet.generate_key()
        temporary = key_file.with_suffix(".tmp")
        temporary.write_bytes(key + b"\n")
        os.replace(temporary, key_file)
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass
        return key

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        try:
            return self._fernet.decrypt(data)
        except InvalidToken as exc:
            raise RuntimeError("Knowledge source encryption key cannot decrypt this file") from exc

    def encrypt_text(self, value: str) -> str:
        """Return UTF-8 text encrypted for application-owned persistence."""
        return self.encrypt(str(value).encode("utf-8")).decode("ascii")

    def decrypt_text(self, value: str) -> str:
        """Return text encrypted by encrypt_text without exposing the Fernet key."""
        return self.decrypt(str(value).encode("ascii")).decode("utf-8")

    @classmethod
    def appears_encrypted(cls, data: bytes) -> bool:
        """Identify Fernet-shaped persisted bytes before a legacy migration rewrites them."""
        return bytes(data or b"").startswith(cls._TOKEN_PREFIX)
