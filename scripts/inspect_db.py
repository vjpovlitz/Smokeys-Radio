#!/usr/bin/env python3
"""Quick read-only inspector for the SmokeysRadio database.

Usage:
    python scripts/inspect_db.py              # show last 20 plays + last 20 commands
    python scripts/inspect_db.py plays 50     # last 50 plays
    python scripts/inspect_db.py commands 50  # last 50 commands
    python scripts/inspect_db.py top          # /topsongs and /topusers preview
    python scripts/inspect_db.py raw          # raw row counts per table
"""
import os
import sys

import pyodbc

CONN = os.getenv(
    "SMOKEYS_DB_CONN",
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SmokeysRadio;Trusted_Connection=yes;",
)


def _print_table(headers, rows):
    if not rows:
        print("  (no rows)")
        return
    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt.format(*[str(c) if c is not None else "-" for c in r]))


def show_plays(cur, limit):
    cur.execute(
        f"""
        SELECT TOP ({limit})
            p.play_id, p.played_at, COALESCE(u.display_name, u.username) AS who,
            s.title, s.uploader, p.source, p.extraction_method,
            p.outcome, p.listened_seconds, s.duration_seconds, p.search_query
        FROM dbo.plays p
        JOIN dbo.songs s ON s.song_id = p.song_id
        JOIN dbo.users u ON u.discord_user_id = p.user_id
        ORDER BY p.played_at DESC
        """
    )
    rows = [
        (r[0], r[1].strftime("%Y-%m-%d %H:%M:%S"), r[2], (r[3] or "")[:40], (r[4] or "-")[:25],
         r[5] or "-", r[6] or "-", r[7], r[8], r[9], (r[10] or "-")[:30])
        for r in cur.fetchall()
    ]
    print(f"\n=== Last {limit} plays ===")
    _print_table(
        ["id", "played_at (UTC)", "user", "title", "uploader", "src", "method", "outcome", "listen", "dur", "query"],
        rows,
    )


def show_commands(cur, limit):
    cur.execute(
        f"""
        SELECT TOP ({limit})
            c.command_id, c.executed_at, COALESCE(u.display_name, u.username) AS who,
            c.command_name, c.success, c.args, c.error_message
        FROM dbo.commands c
        JOIN dbo.users u ON u.discord_user_id = c.user_id
        ORDER BY c.executed_at DESC
        """
    )
    rows = [
        (r[0], r[1].strftime("%Y-%m-%d %H:%M:%S"), r[2], r[3], "ok" if r[4] else "FAIL",
         (r[5] or "-")[:40], (r[6] or "-")[:50])
        for r in cur.fetchall()
    ]
    print(f"\n=== Last {limit} commands ===")
    _print_table(["id", "executed_at (UTC)", "user", "command", "result", "args", "error"], rows)


def show_top(cur):
    print("\n=== Top songs (all-time) ===")
    cur.execute(
        """
        SELECT TOP 10 s.title, s.uploader, COUNT(*) AS plays,
            SUM(CASE WHEN p.outcome = 'completed' THEN 1 ELSE 0 END) AS completed,
            SUM(CASE WHEN p.outcome = 'skipped'   THEN 1 ELSE 0 END) AS skipped
        FROM dbo.plays p JOIN dbo.songs s ON s.song_id = p.song_id
        GROUP BY s.title, s.uploader ORDER BY plays DESC
        """
    )
    _print_table(["title", "uploader", "plays", "completed", "skipped"],
                 [((r[0] or "")[:40], (r[1] or "-")[:25], r[2], r[3], r[4]) for r in cur.fetchall()])

    print("\n=== Top users (all-time) ===")
    cur.execute(
        """
        SELECT TOP 10 COALESCE(u.display_name, u.username) AS who, COUNT(*) AS plays
        FROM dbo.plays p JOIN dbo.users u ON u.discord_user_id = p.user_id
        GROUP BY u.display_name, u.username ORDER BY plays DESC
        """
    )
    _print_table(["user", "plays"], [(r[0], r[1]) for r in cur.fetchall()])

    print("\n=== Most-skipped songs (>=3 plays) ===")
    cur.execute(
        """
        SELECT TOP 10 s.title,
            COUNT(*) AS plays,
            SUM(CASE WHEN p.outcome = 'skipped' THEN 1 ELSE 0 END) AS skips,
            CAST(100.0 * SUM(CASE WHEN p.outcome = 'skipped' THEN 1 ELSE 0 END) / COUNT(*) AS INT) AS skip_pct
        FROM dbo.plays p JOIN dbo.songs s ON s.song_id = p.song_id
        GROUP BY s.title HAVING COUNT(*) >= 3
        ORDER BY skip_pct DESC, plays DESC
        """
    )
    _print_table(["title", "plays", "skips", "skip%"],
                 [((r[0] or "")[:40], r[1], r[2], r[3]) for r in cur.fetchall()])


def show_counts(cur):
    print("\n=== Row counts ===")
    for t in ("users", "guilds", "songs", "plays", "commands"):
        cur.execute(f"SELECT COUNT(*) FROM dbo.{t}")
        print(f"  {t:<10} {cur.fetchone()[0]}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "default"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    with pyodbc.connect(CONN) as c:
        cur = c.cursor()
        if cmd == "plays":
            show_plays(cur, n)
        elif cmd == "commands":
            show_commands(cur, n)
        elif cmd == "top":
            show_top(cur)
        elif cmd == "raw":
            show_counts(cur)
        else:
            show_counts(cur)
            show_plays(cur, n)
            show_commands(cur, n)


if __name__ == "__main__":
    main()
