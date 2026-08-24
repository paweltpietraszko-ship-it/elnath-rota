from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading

from rota.persistence.db import connect


def test_t027_connection_supports_sequential_fastapi_style_thread_handoff(tmp_path) -> None:
    """A request-scoped connection may be opened, used and closed by
    different worker threads, but is never accessed concurrently."""

    database = tmp_path / "rota.db"

    def open_connection() -> tuple[sqlite3.Connection, int]:
        return connect(database), threading.get_ident()

    def use_connection(connection: sqlite3.Connection) -> int:
        connection.execute("INSERT INTO calendar_days(date, holiday) VALUES (?, ?)", ("2026-08-24", 0))
        connection.commit()
        assert connection.execute(
            "SELECT holiday FROM calendar_days WHERE date = ?", ("2026-08-24",)
        ).fetchone() == (0,)
        return threading.get_ident()

    def close_connection(connection: sqlite3.Connection) -> int:
        connection.close()
        return threading.get_ident()

    # Keep all three single-worker pools alive together so their worker thread
    # identities cannot be recycled between lifecycle stages.
    with (
        ThreadPoolExecutor(max_workers=1) as opener,
        ThreadPoolExecutor(max_workers=1) as user,
        ThreadPoolExecutor(max_workers=1) as closer,
    ):
        connection, open_thread = opener.submit(open_connection).result()
        use_thread = user.submit(use_connection, connection).result()
        close_thread = closer.submit(close_connection, connection).result()

    assert len({open_thread, use_thread, close_thread}) == 3
