"""SQL Server persistence layer for Smokey's Radio.

Connection details come from env vars (see .env.example). All public functions
are async wrappers around blocking pyodbc calls dispatched to the default
executor. The module is fail-soft: if the DB is unreachable at startup it
disables itself and every helper becomes a no-op (or returns an empty result),
so DB outages never break playback.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Iterable, Optional

import pyodbc

logger = logging.getLogger("smokeys_radio.db")

# pyodbc enables connection pooling by default; leave it on.
pyodbc.pooling = True

_conn_str: Optional[str] = None
_enabled: bool = False


def _build_conn_str() -> Optional[str]:
    """Assemble a connection string from env vars. Returns None if disabled."""
    if os.getenv("SMOKEYS_DB_DISABLED", "").lower() in ("1", "true", "yes"):
        return None

    raw = os.getenv("SMOKEYS_DB_CONN")
    if raw:
        return raw

    driver = os.getenv("SMOKEYS_DB_DRIVER", "ODBC Driver 17 for SQL Server")
    server = os.getenv("SMOKEYS_DB_SERVER", "localhost")
    database = os.getenv("SMOKEYS_DB_NAME", "SmokeysRadio")
    trusted = os.getenv("SMOKEYS_DB_TRUSTED", "yes").lower() in ("1", "true", "yes")

    parts = [f"DRIVER={{{driver}}}", f"SERVER={server}", f"DATABASE={database}"]
    if trusted:
        parts.append("Trusted_Connection=yes")
    else:
        user = os.getenv("SMOKEYS_DB_USER")
        password = os.getenv("SMOKEYS_DB_PASSWORD")
        if not user or not password:
            logger.warning(
                "SMOKEYS_DB_TRUSTED is false but SMOKEYS_DB_USER/PASSWORD not set; DB disabled"
            )
            return None
        parts.append(f"UID={user}")
        parts.append(f"PWD={password}")
    return ";".join(parts) + ";"


def init() -> bool:
    """Probe the DB connection. Sets module-level state. Returns True on success."""
    global _conn_str, _enabled
    _conn_str = _build_conn_str()
    if not _conn_str:
        logger.info("Database is disabled (no connection string)")
        _enabled = False
        return False
    try:
        with pyodbc.connect(_conn_str, timeout=5) as c:
            c.cursor().execute("SELECT 1").fetchone()
        _enabled = True
        logger.info("Database connection OK")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e} - stats logging disabled")
        _enabled = False
        return False


def is_enabled() -> bool:
    return _enabled


def _query(sql: str, params: Iterable[Any] = ()) -> list[tuple]:
    """Run a read statement and materialize the rows."""
    with pyodbc.connect(_conn_str, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [tuple(r) for r in cur.fetchall()]


async def _run(fn, *args, **kwargs):
    """Dispatch a blocking pyodbc call to the default thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ---------- Writers ----------

_UPSERT_USER = """
MERGE dbo.users AS t
USING (SELECT ? AS discord_user_id, ? AS username, ? AS display_name) AS s
ON t.discord_user_id = s.discord_user_id
WHEN MATCHED THEN UPDATE SET
    username = s.username,
    display_name = s.display_name,
    last_seen = SYSUTCDATETIME()
WHEN NOT MATCHED THEN
    INSERT (discord_user_id, username, display_name)
    VALUES (s.discord_user_id, s.username, s.display_name);
"""

_UPSERT_GUILD = """
MERGE dbo.guilds AS t
USING (SELECT ? AS guild_id, ? AS name) AS s
ON t.guild_id = s.guild_id
WHEN MATCHED THEN UPDATE SET name = COALESCE(s.name, t.name)
WHEN NOT MATCHED THEN INSERT (guild_id, name) VALUES (s.guild_id, s.name);
"""

_UPSERT_SONG = """
SET NOCOUNT ON;
MERGE dbo.songs AS t
USING (SELECT ? AS youtube_id, ? AS title, ? AS uploader, ? AS duration_seconds, ? AS thumbnail_url) AS s
ON t.youtube_id = s.youtube_id
WHEN MATCHED THEN UPDATE SET
    title            = s.title,
    uploader         = COALESCE(s.uploader,         t.uploader),
    duration_seconds = COALESCE(s.duration_seconds, t.duration_seconds),
    thumbnail_url    = COALESCE(s.thumbnail_url,    t.thumbnail_url)
WHEN NOT MATCHED THEN
    INSERT (youtube_id, title, uploader, duration_seconds, thumbnail_url)
    VALUES (s.youtube_id, s.title, s.uploader, s.duration_seconds, s.thumbnail_url);
"""

_SELECT_SONG_ID = "SELECT song_id FROM dbo.songs WHERE youtube_id = ?;"


def _log_command_sync(command_name, user_id, username, display_name, guild_id, guild_name, success, args, error):
    with pyodbc.connect(_conn_str, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(_UPSERT_USER, (user_id, username, display_name))
        if guild_id is not None:
            cur.execute(_UPSERT_GUILD, (guild_id, guild_name))
        cur.execute(
            "INSERT INTO dbo.commands (command_name, user_id, guild_id, success, args, error_message) VALUES (?, ?, ?, ?, ?, ?)",
            (command_name, user_id, guild_id, 1 if success else 0, args, error),
        )
        conn.commit()


async def log_command(
    command_name: str,
    user_id: int,
    username: str,
    display_name: Optional[str],
    guild_id: Optional[int],
    guild_name: Optional[str],
    success: bool = True,
    args: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    if not _enabled:
        return
    try:
        await _run(
            _log_command_sync,
            command_name, user_id, username, display_name,
            guild_id, guild_name, success,
            (args[:500] if args else None),
            (error[:1000] if error else None),
        )
    except Exception as e:
        logger.warning(f"log_command failed: {e}")


def _log_play_sync(youtube_id, title, uploader, duration, thumbnail,
                   user_id, username, display_name,
                   guild_id, guild_name, source, method, search_query):
    with pyodbc.connect(_conn_str, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(_UPSERT_USER, (user_id, username, display_name))
        cur.execute(_UPSERT_GUILD, (guild_id, guild_name))
        cur.execute(_UPSERT_SONG, (
            youtube_id,
            title[:500],
            (uploader[:200] if uploader else None),
            duration,
            (thumbnail[:500] if thumbnail else None),
        ))
        cur.execute(_SELECT_SONG_ID, (youtube_id,))
        song_id = cur.fetchone()[0]
        # OUTPUT clause returns the inserted play_id in a single round trip
        cur.execute(
            """
            INSERT INTO dbo.plays
                (song_id, user_id, guild_id, source, extraction_method, search_query, outcome)
            OUTPUT inserted.play_id
            VALUES (?, ?, ?, ?, ?, ?, 'started')
            """,
            (song_id, user_id, guild_id, source, method, (search_query[:500] if search_query else None)),
        )
        play_id = cur.fetchone()[0]
        conn.commit()
        return int(play_id)


async def log_play(
    youtube_id: str,
    title: str,
    duration_seconds: Optional[int],
    thumbnail_url: Optional[str],
    user_id: int,
    username: str,
    display_name: Optional[str],
    guild_id: int,
    guild_name: Optional[str],
    source: Optional[str] = None,
    extraction_method: Optional[str] = None,
    uploader: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Optional[int]:
    """Insert a play row and return the new play_id, or None on failure / when DB is disabled."""
    if not _enabled or not youtube_id:
        return None
    try:
        return await _run(
            _log_play_sync,
            youtube_id, title, uploader, duration_seconds, thumbnail_url,
            user_id, username, display_name,
            guild_id, guild_name, source, extraction_method, search_query,
        )
    except Exception as e:
        logger.warning(f"log_play failed: {e}")
        return None


def _update_play_outcome_sync(play_id, outcome, listened_seconds):
    with pyodbc.connect(_conn_str, timeout=10) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE dbo.plays SET outcome = ?, listened_seconds = ? WHERE play_id = ?",
            (outcome, listened_seconds, play_id),
        )
        conn.commit()


async def update_play_outcome(play_id: int, outcome: str, listened_seconds: Optional[int]) -> None:
    """Mark a play as completed/skipped/error with how long it actually played."""
    if not _enabled or play_id is None:
        return
    try:
        await _run(_update_play_outcome_sync, play_id, outcome, listened_seconds)
    except Exception as e:
        logger.warning(f"update_play_outcome failed: {e}")


# ---------- Readers ----------

_PERIOD_FILTERS = {
    "day":   "AND p.played_at >= DATEADD(day,   -1, SYSUTCDATETIME())",
    "week":  "AND p.played_at >= DATEADD(day,   -7, SYSUTCDATETIME())",
    "month": "AND p.played_at >= DATEADD(day,  -30, SYSUTCDATETIME())",
    "all":   "",
}


def _period_clause(period: str) -> str:
    return _PERIOD_FILTERS.get(period.lower(), "")


async def top_songs(period: str = "all", limit: int = 10, guild_id: Optional[int] = None) -> list[tuple]:
    """Returns [(title, youtube_id, play_count), ...] ordered by play_count DESC."""
    if not _enabled:
        return []
    where_guild = "AND p.guild_id = ?" if guild_id is not None else ""
    sql = f"""
        SELECT TOP (?) s.title, s.youtube_id, COUNT(*) AS plays
        FROM dbo.plays p
        JOIN dbo.songs s ON s.song_id = p.song_id
        WHERE 1=1 {_period_clause(period)} {where_guild}
        GROUP BY s.title, s.youtube_id
        ORDER BY plays DESC
    """
    params: list[Any] = [limit]
    if guild_id is not None:
        params.append(guild_id)
    try:
        return await _run(_query, sql, tuple(params))
    except Exception as e:
        logger.warning(f"top_songs failed: {e}")
        return []


async def top_users(period: str = "all", limit: int = 10, guild_id: Optional[int] = None) -> list[tuple]:
    """Returns [(user_id, display_name, play_count), ...]."""
    if not _enabled:
        return []
    where_guild = "AND p.guild_id = ?" if guild_id is not None else ""
    sql = f"""
        SELECT TOP (?) u.discord_user_id, COALESCE(u.display_name, u.username) AS name, COUNT(*) AS plays
        FROM dbo.plays p
        JOIN dbo.users u ON u.discord_user_id = p.user_id
        WHERE 1=1 {_period_clause(period)} {where_guild}
        GROUP BY u.discord_user_id, u.display_name, u.username
        ORDER BY plays DESC
    """
    params: list[Any] = [limit]
    if guild_id is not None:
        params.append(guild_id)
    try:
        return await _run(_query, sql, tuple(params))
    except Exception as e:
        logger.warning(f"top_users failed: {e}")
        return []


async def user_history(user_id: int, limit: int = 10) -> list[tuple]:
    """Returns [(title, youtube_id, played_at), ...] for a single user, newest first."""
    if not _enabled:
        return []
    sql = """
        SELECT TOP (?) s.title, s.youtube_id, p.played_at
        FROM dbo.plays p
        JOIN dbo.songs s ON s.song_id = p.song_id
        WHERE p.user_id = ?
        ORDER BY p.played_at DESC
    """
    try:
        return await _run(_query, sql, (limit, user_id))
    except Exception as e:
        logger.warning(f"user_history failed: {e}")
        return []


async def totals() -> dict:
    """Returns aggregate counts for /stats display."""
    if not _enabled:
        return {}
    try:
        rows = await _run(
            _query,
            """SELECT
                (SELECT COUNT(*) FROM dbo.plays)    AS total_plays,
                (SELECT COUNT(*) FROM dbo.songs)    AS unique_songs,
                (SELECT COUNT(*) FROM dbo.users)    AS unique_users,
                (SELECT COUNT(*) FROM dbo.commands) AS total_commands""",
            (),
        )
        if not rows:
            return {}
        r = rows[0]
        return {"total_plays": r[0], "unique_songs": r[1], "unique_users": r[2], "total_commands": r[3]}
    except Exception as e:
        logger.warning(f"totals failed: {e}")
        return {}
