"""Shared SQLite connection factory type for application-owned adapters."""
from __future__ import annotations

import sqlite3
from typing import Callable


ConnectionFactory = Callable[[], sqlite3.Connection]
