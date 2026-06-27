"""
backend/database.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — Database shim (NO-OP)

This module exists solely so that legacy imports of `backend.database` in
settings.py and any other frontend file do not raise ImportError.

The application uses NO SQLite or any database layer.  All job tracking is
purely in-memory (see queue_manager.py) and all persistent data is stored
as JSON (see template_store.py).

If you previously had a database-backed version and are migrating, replace
any db.* calls with the appropriate calls to backend.template_store.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from backend.logger import get_logger

log = get_logger(__name__)

# ── Public no-op stubs ─────────────────────────────────────────────────────
# These are named to match common patterns that settings.py or other files
# may call.  They all silently do nothing.


def init() -> None:
    """No-op: database initialisation is not used in this architecture."""
    log.debug("database.init() called — no-op (JSON-only architecture)")


def close() -> None:
    """No-op."""
    pass


def get_setting(key: str, default=None):
    """No-op stub — returns *default*."""
    log.debug("database.get_setting('%s') → returning default", key)
    return default


def set_setting(key: str, value) -> None:
    """No-op stub."""
    log.debug("database.set_setting('%s', ...) — ignored", key)


def get_all_settings() -> dict:
    """No-op stub — returns empty dict."""
    return {}


def save_template(name: str, hashtags: list) -> None:
    """
    Redirect to the real JSON-based template store.

    Provided so that any legacy code calling `db.save_template(...)` still
    works without modification.
    """
    from backend.template_store import HashtagTemplate, save_template as _save
    log.debug("database.save_template() — redirecting to template_store")
    _save(HashtagTemplate(name=name, hashtags=hashtags))


def load_templates() -> list:
    """
    Redirect to the real JSON-based template store.

    Returns a list of dicts: [{"name": ..., "hashtags": [...]}, ...]
    """
    from backend.template_store import list_templates
    log.debug("database.load_templates() — redirecting to template_store")
    return [t.as_dict() for t in list_templates()]


def delete_template(name: str) -> bool:
    """Redirect to the real JSON-based template store."""
    from backend.template_store import delete_template as _delete
    log.debug("database.delete_template('%s') — redirecting to template_store", name)
    return _delete(name)
