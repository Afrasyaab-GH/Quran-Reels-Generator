"""
Database layer — SQLite schema, initialization, and all CRUD operations.

Improvements:
  1. Context manager (`_cursor`) eliminates repeated connect/close boilerplate.
  2. Column allowlists in update helpers prevent SQL-injection via dynamic kwargs.
  3. Versioned migration system (schema_versions table) replaces fragile try/except probing.
  4. All DB operations are wrapped in try/except with meaningful error logging.
  5. Timestamps stored as ISO-8601 UTC strings for human-readability and SQLite date functions.
"""

import os
import logging
import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from flask import g
from config import DB_PATH

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (e.g. '2026-05-17T06:00:00+00:00')."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _cursor(commit: bool = False):
    """
    Context manager that opens a fresh SQLite connection, yields its cursor,
    optionally commits, then always closes the connection — even on error.

    Usage::
        with _cursor(commit=True) as c:
            c.execute("INSERT INTO ...", (...))
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        c = conn.cursor()
        yield c
        if commit:
            conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        log.error("Database error: %s", exc, exc_info=True)
        raise
    finally:
        conn.close()


def _build_set_clause(kwargs: dict, allowed_columns: set) -> tuple[str, list]:
    """
    Validate update kwargs against *allowed_columns* and build a safe SET clause.
    Raises ValueError if any key is not in the allowlist (prevents SQL injection).
    Returns (set_clause_str, values_list).
    """
    bad_keys = set(kwargs) - allowed_columns
    if bad_keys:
        raise ValueError(f"Attempted update on disallowed column(s): {bad_keys}")
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    return set_clause, values


# ---------------------------------------------------------------------------
# Allowed column sets (SQL-injection guard for dynamic UPDATE helpers)
# ---------------------------------------------------------------------------

_JOB_COLUMNS = {
    "status", "percent", "eta", "output_path", "error",
    "should_stop", "completed_at", "config_json", "workspace", "session_id",
}

_BATCH_COLUMNS = {
    "status", "total_jobs", "completed_jobs", "failed_jobs",
    "current_job_id", "current_job_index", "config_json",
    "started_at", "completed_at", "avg_video_time",
}

_BATCH_ITEM_COLUMNS = {
    "status", "output_path", "error", "video_started_at",
}


# ---------------------------------------------------------------------------
# Flask request-scoped connection (for use inside routes)
# ---------------------------------------------------------------------------

def get_db():
    """Get a request-scoped database connection (Flask g object)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    """Close request-scoped connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Schema versioning & migrations
# ---------------------------------------------------------------------------

# Each entry is (version, description, sql_statement).
# Append new entries here instead of adding more try/except blocks.
_MIGRATIONS: list[tuple[int, str, str]] = [
    (1, "Create jobs table", """
        CREATE TABLE IF NOT EXISTS jobs (
            id          TEXT PRIMARY KEY,
            status      TEXT NOT NULL DEFAULT 'pending',
            percent     INTEGER DEFAULT 0,
            eta         TEXT DEFAULT '--:--',
            output_path TEXT,
            error       TEXT,
            should_stop INTEGER DEFAULT 0,
            created_at  TEXT,
            completed_at TEXT,
            config_json TEXT,
            workspace   TEXT,
            session_id  TEXT
        )"""),
    (2, "Create history table", """
        CREATE TABLE IF NOT EXISTS history (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id            TEXT,
            title             TEXT,
            reciter           TEXT,
            surah             INTEGER,
            start_ayah        INTEGER,
            end_ayah          INTEGER,
            quality           TEXT,
            fps               TEXT,
            download_filename TEXT,
            created_at        TEXT,
            session_id        TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )"""),
    (3, "Create batch_jobs table", """
        CREATE TABLE IF NOT EXISTS batch_jobs (
            id                TEXT PRIMARY KEY,
            status            TEXT NOT NULL DEFAULT 'pending',
            total_jobs        INTEGER DEFAULT 0,
            completed_jobs    INTEGER DEFAULT 0,
            failed_jobs       INTEGER DEFAULT 0,
            current_job_id    TEXT,
            current_job_index INTEGER DEFAULT 0,
            config_json       TEXT,
            created_at        TEXT,
            started_at        TEXT,
            completed_at      TEXT,
            avg_video_time    REAL
        )"""),
    (4, "Create batch_items table", """
        CREATE TABLE IF NOT EXISTS batch_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id         TEXT,
            job_id           TEXT,
            position         INTEGER,
            surah            INTEGER,
            start_ayah       INTEGER,
            end_ayah         INTEGER,
            status           TEXT DEFAULT 'pending',
            output_path      TEXT,
            error            TEXT,
            video_started_at REAL,
            created_at       TEXT,
            FOREIGN KEY (batch_id) REFERENCES batch_jobs(id),
            FOREIGN KEY (job_id)   REFERENCES jobs(id)
        )"""),
    (5, "Add media hub download tracking columns", """
        ALTER TABLE history ADD COLUMN download_count INTEGER DEFAULT 0
    """),
    (6, "Add downloaded_at column", """
        ALTER TABLE history ADD COLUMN downloaded_at TEXT
    """),
]


def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version stored in the DB (0 if never set)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version     INTEGER PRIMARY KEY,
            description TEXT,
            applied_at  TEXT NOT NULL
        )""")
    row = conn.execute("SELECT MAX(version) FROM schema_versions").fetchone()
    return row[0] or 0


def init_db():
    """
    Initialize the database and apply any pending migrations in order.
    Safe to call multiple times; only un-applied migrations are executed.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        current = _get_schema_version(conn)
        pending = [(v, d, s) for v, d, s in _MIGRATIONS if v > current]

        for version, description, sql in pending:
            log.info("Applying migration v%d: %s", version, description)
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_versions (version, description, applied_at) VALUES (?, ?, ?)",
                (version, description, _now_iso()),
            )
            conn.commit()
            print(f"✅ Migration v{version} applied: {description}")

        if not pending:
            log.debug("Database schema is up-to-date (v%d).", current)

        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        log.error("Failed to initialize database: %s", exc, exc_info=True)
        raise
    finally:
        conn.close()

    print("✅ Database initialized successfully!")


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------

def db_create_job(job_id: str, workspace: str, config=None, session_id=None):
    """Insert a new job row."""
    with _cursor(commit=True) as c:
        c.execute(
            """INSERT INTO jobs
               (id, status, percent, created_at, workspace, config_json, session_id)
               VALUES (?, 'pending', 0, ?, ?, ?, ?)""",
            (job_id, _now_iso(), workspace, json.dumps(config) if config else None, session_id),
        )


def db_update_job(job_id: str, **kwargs):
    """Update one or more columns on a job row (safe: only allowed columns accepted)."""
    if not kwargs:
        return
    set_clause, values = _build_set_clause(kwargs, _JOB_COLUMNS)
    with _cursor(commit=True) as c:
        c.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values + [job_id])


def db_get_job(job_id: str) -> Optional[dict]:
    """Fetch a single job by ID, or None if not found."""
    with _cursor() as c:
        c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = c.fetchone()
    return dict(row) if row else None


def db_get_job_for_session(job_id: str, session_id: str) -> Optional[dict]:
    """Fetch a single job by ID only if it belongs to the provided session."""
    if not session_id:
        return None
    with _cursor() as c:
        c.execute(
            "SELECT * FROM jobs WHERE id = ? AND session_id = ?",
            (job_id, session_id),
        )
        row = c.fetchone()
    return dict(row) if row else None


def db_get_all_jobs(status: Optional[str] = None, limit: int = 50, session_id=None) -> list[dict]:
    """Return all jobs, optionally filtered by status and session."""
    with _cursor() as c:
        if status and session_id:
            c.execute(
                "SELECT * FROM jobs WHERE status = ? AND session_id = ? ORDER BY created_at DESC LIMIT ?",
                (status, session_id, limit),
            )
        elif status:
            c.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        elif session_id:
            c.execute(
                "SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            )
        else:
            c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = c.fetchall()
    return [dict(r) for r in rows]


def db_get_pending_jobs() -> list[dict]:
    """Return all pending/processing jobs (used for crash recovery)."""
    with _cursor() as c:
        c.execute("SELECT * FROM jobs WHERE status IN ('pending', 'processing')")
        rows = c.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# History CRUD
# ---------------------------------------------------------------------------

def db_add_history(
    job_id, title, reciter, surah, start_ayah, end_ayah,
    quality, fps, filename, session_id=None,
):
    """Insert a history record."""
    with _cursor(commit=True) as c:
        c.execute(
            """INSERT INTO history
               (job_id, title, reciter, surah, start_ayah, end_ayah,
                quality, fps, download_filename, created_at, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, title, reciter, surah, start_ayah, end_ayah,
             quality, fps, filename, _now_iso(), session_id),
        )


def db_get_history(limit: int = 20, session_id=None) -> list[dict]:
    """Fetch history records, optionally scoped to a session."""
    with _cursor() as c:
        if session_id:
            c.execute(
                """SELECT h.*, j.output_path, j.status
                   FROM history h
                   LEFT JOIN jobs j ON h.job_id = j.id
                   WHERE h.session_id = ?
                   ORDER BY h.created_at DESC LIMIT ?""",
                (session_id, limit),
            )
        else:
            c.execute(
                """SELECT h.*, j.output_path, j.status
                   FROM history h
                   LEFT JOIN jobs j ON h.job_id = j.id
                   ORDER BY h.created_at DESC LIMIT ?""",
                (limit,),
            )
        rows = c.fetchall()
    return [dict(r) for r in rows]


def db_get_history_item_for_session(history_id: int, session_id: str) -> Optional[dict]:
    """Fetch a single history record only if it belongs to the provided session."""
    if not session_id:
        return None
    with _cursor() as c:
        c.execute(
            "SELECT * FROM history WHERE id = ? AND session_id = ?",
            (history_id, session_id),
        )
        row = c.fetchone()
    return dict(row) if row else None


def db_mark_downloaded(job_id: str, session_id=None):
    """Mark a history item as downloaded from UI and increment download counter."""
    now = _now_iso()
    with _cursor(commit=True) as c:
        if session_id:
            c.execute(
                """UPDATE history
                   SET download_count = COALESCE(download_count, 0) + 1,
                       downloaded_at = ?
                   WHERE id = (
                       SELECT id FROM history
                       WHERE job_id = ? AND session_id = ?
                       ORDER BY created_at DESC
                       LIMIT 1
                   )""",
                (now, job_id, session_id),
            )
            if c.rowcount == 0:
                c.execute(
                    """UPDATE history
                       SET download_count = COALESCE(download_count, 0) + 1,
                           downloaded_at = ?
                       WHERE id = (
                           SELECT id FROM history
                           WHERE job_id = ?
                           ORDER BY created_at DESC
                           LIMIT 1
                       )""",
                    (now, job_id),
                )
        else:
            c.execute(
                """UPDATE history
                   SET download_count = COALESCE(download_count, 0) + 1,
                       downloaded_at = ?
                   WHERE id = (
                       SELECT id FROM history
                       WHERE job_id = ?
                       ORDER BY created_at DESC
                       LIMIT 1
                   )""",
                (now, job_id),
            )


def db_cleanup_old_jobs(hours: int = 24):
    """
    Delete completed/failed jobs older than *hours* hours and remove
    their associated workspace directories and output video files.
    """
    threshold = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() - hours * 3600, tz=timezone.utc
    ).isoformat()

    with _cursor(commit=True) as c:
        c.execute(
            """SELECT id, workspace, output_path FROM jobs
               WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')""",
            (threshold,),
        )
        old_jobs = c.fetchall()

        for job in old_jobs:
            if job["workspace"] and os.path.exists(job["workspace"]):
                shutil.rmtree(job["workspace"], ignore_errors=True)
            if job["output_path"] and os.path.exists(job["output_path"]):
                try:
                    os.remove(job["output_path"])
                except OSError as exc:
                    log.warning("Could not delete output file %s: %s", job["output_path"], exc)

        c.execute(
            "DELETE FROM jobs WHERE created_at < ? AND status IN ('complete', 'error', 'cancelled')",
            (threshold,),
        )
        c.execute("DELETE FROM history WHERE created_at < ?", (threshold,))

    log.info("🧹 Cleaned up %d old job(s) and their files.", len(old_jobs))
    print(f"🧹 Cleaned up {len(old_jobs)} old jobs and their video files")


# ---------------------------------------------------------------------------
# Batch CRUD
# ---------------------------------------------------------------------------

def db_create_batch(batch_id: str, total_jobs: int, config: dict):
    """Insert a new batch_jobs row."""
    with _cursor(commit=True) as c:
        c.execute(
            """INSERT INTO batch_jobs
               (id, status, total_jobs, completed_jobs, failed_jobs, config_json, created_at)
               VALUES (?, 'pending', ?, 0, 0, ?, ?)""",
            (batch_id, total_jobs, json.dumps(config), _now_iso()),
        )


def db_update_batch(batch_id: str, **kwargs):
    """Update one or more columns on a batch_jobs row (safe: only allowed columns accepted)."""
    if not kwargs:
        return
    set_clause, values = _build_set_clause(kwargs, _BATCH_COLUMNS)
    with _cursor(commit=True) as c:
        c.execute(f"UPDATE batch_jobs SET {set_clause} WHERE id = ?", values + [batch_id])


def db_get_batch(batch_id: str) -> Optional[dict]:
    """Fetch a batch by ID, or None."""
    with _cursor() as c:
        c.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_id,))
        row = c.fetchone()
    return dict(row) if row else None


def db_get_batch_for_session(batch_id: str, session_id: str) -> Optional[dict]:
    """Fetch a batch only if it is associated with the provided session via its jobs."""
    if not session_id:
        return None
    with _cursor() as c:
        c.execute(
            """SELECT DISTINCT b.*
               FROM batch_jobs b
               JOIN batch_items bi ON bi.batch_id = b.id
               JOIN jobs j ON j.id = bi.job_id
               WHERE b.id = ? AND j.session_id = ?
               LIMIT 1""",
            (batch_id, session_id),
        )
        row = c.fetchone()
    return dict(row) if row else None


def db_add_batch_item(
    batch_id: str, job_id: str, position: int,
    surah: int, start_ayah: int, end_ayah: int,
):
    """Insert a batch_items row."""
    with _cursor(commit=True) as c:
        c.execute(
            """INSERT INTO batch_items
               (batch_id, job_id, position, surah, start_ayah, end_ayah, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (batch_id, job_id, position, surah, start_ayah, end_ayah, _now_iso()),
        )


def db_update_batch_item(batch_id: str, job_id: str, **kwargs):
    """Update columns on a batch_items row (safe: only allowed columns accepted)."""
    if not kwargs:
        return
    set_clause, values = _build_set_clause(kwargs, _BATCH_ITEM_COLUMNS)
    with _cursor(commit=True) as c:
        c.execute(
            f"UPDATE batch_items SET {set_clause} WHERE batch_id = ? AND job_id = ?",
            values + [batch_id, job_id],
        )


def db_get_batch_items(batch_id: str) -> list[dict]:
    """Return all items in a batch, ordered by position."""
    with _cursor() as c:
        c.execute(
            "SELECT * FROM batch_items WHERE batch_id = ? ORDER BY position",
            (batch_id,),
        )
        rows = c.fetchall()
    return [dict(r) for r in rows]


def db_get_pending_batches() -> list[dict]:
    """Return all pending/running batches (used for crash recovery)."""
    with _cursor() as c:
        c.execute("SELECT * FROM batch_jobs WHERE status IN ('pending', 'running')")
        rows = c.fetchall()
    return [dict(r) for r in rows]
