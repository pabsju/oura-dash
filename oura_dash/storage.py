import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


class Storage:
    def __init__(self, db_path: Path | str) -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                collection TEXT NOT NULL,
                id TEXT NOT NULL,
                day TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY (collection, id)
            )
            """
        )
        self._conn.commit()

    def upsert(self, collection: str, rows: list[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            rid = row.get("id")
            if rid is None:
                continue
            self._conn.execute(
                "INSERT OR REPLACE INTO records (collection, id, day, payload) "
                "VALUES (?, ?, ?, ?)",
                (collection, rid, row.get("day"), json.dumps(row)),
            )
            count += 1
        self._conn.commit()
        return count

    def read(self, collection: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT payload FROM records WHERE collection = ? ORDER BY day",
            (collection,),
        )
        return [json.loads(r["payload"]) for r in cur.fetchall()]

    def last_day(self, collection: str) -> date | None:
        cur = self._conn.execute(
            "SELECT MAX(day) AS d FROM records WHERE collection = ? AND day IS NOT NULL",
            (collection,),
        )
        row = cur.fetchone()
        return date.fromisoformat(row["d"]) if row and row["d"] else None

    def close(self) -> None:
        self._conn.close()
