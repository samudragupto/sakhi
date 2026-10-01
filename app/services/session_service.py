"""Anonymous session management service.

Implements Cloud Firestore with a 24-hour TTL and safe local in-memory fallback.
Ensures zero PII is persisted.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger
from app.models.session import SessionDoc

# In-memory dictionary store for local development, offline mode, and testing
_LOCAL_SESSIONS: dict[str, SessionDoc] = {}
_LOCAL_SESSION_MAX_SIZE = 1024


def _store_local_session(session: SessionDoc) -> None:
    """Store a session while expiring stale entries and bounding fallback memory."""
    now = datetime.now(UTC)
    expired_ids = [
        session_id for session_id, cached in _LOCAL_SESSIONS.items() if cached.expire_at <= now
    ]
    for session_id in expired_ids:
        del _LOCAL_SESSIONS[session_id]
    if (
        session.session_id not in _LOCAL_SESSIONS
        and len(_LOCAL_SESSIONS) >= _LOCAL_SESSION_MAX_SIZE
    ):
        _LOCAL_SESSIONS.pop(next(iter(_LOCAL_SESSIONS)))
    _LOCAL_SESSIONS[session.session_id] = session


def _get_firestore_client() -> Any | None:
    """Safely obtain Firestore client if configured and reachable."""
    settings = get_settings()
    if settings.app_env in ("development", "test"):
        return None
    try:
        from google.cloud import firestore

        return firestore.Client(
            project=settings.gcp_project_id, database=settings.firestore_database
        )
    except Exception:
        logger.warning(
            "Firestore unavailable, falling back to in-memory store",
            extra={"event": "firestore_fallback"},
        )
        return None


async def get_or_create_session(session_id: str) -> SessionDoc:
    """Retrieve existing session or instantiate a new anonymous session with 24h TTL."""
    settings = get_settings()
    now = datetime.now(UTC)
    expiry = now + timedelta(hours=settings.firestore_session_ttl_hours)

    db = _get_firestore_client()
    if db is not None:
        try:
            doc_ref = db.collection("sessions").document(session_id)
            doc = await asyncio.to_thread(doc_ref.get, timeout=5.0)
            if doc.exists:
                return SessionDoc(**doc.to_dict())
            new_session = SessionDoc(session_id=session_id, expire_at=expiry)
            await asyncio.to_thread(doc_ref.set, new_session.model_dump(), timeout=5.0)
            return new_session
        except Exception:
            pass  # Fall back to in-memory

    if session_id in _LOCAL_SESSIONS:
        # Check expiry
        if _LOCAL_SESSIONS[session_id].expire_at > now:
            return _LOCAL_SESSIONS[session_id]

    new_session = SessionDoc(session_id=session_id, expire_at=expiry)
    _store_local_session(new_session)
    return new_session


async def update_session(session: SessionDoc) -> None:
    """Save updated session progress."""
    db = _get_firestore_client()
    if db is not None:
        try:
            doc_ref = db.collection("sessions").document(session.session_id)
            await asyncio.to_thread(doc_ref.set, session.model_dump(), timeout=5.0)
            return
        except Exception:
            pass

    _store_local_session(session)


async def delete_session(session_id: str) -> bool:
    """Instantly delete session data for shared phone privacy mode."""
    deleted = False
    db = _get_firestore_client()
    if db is not None:
        try:
            doc_ref = db.collection("sessions").document(session_id)
            await asyncio.to_thread(doc_ref.delete, timeout=5.0)
            deleted = True
        except Exception:
            pass

    if session_id in _LOCAL_SESSIONS:
        del _LOCAL_SESSIONS[session_id]
        deleted = True

    return deleted
