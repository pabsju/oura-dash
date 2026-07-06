from typing import Protocol

from oura_dash.collections import COLLECTIONS, Collection
from oura_dash.config import Settings
from oura_dash.storage import Storage


class _Fetcher(Protocol):
    def fetch(self, endpoint: str, start, end) -> list[dict]: ...


def backfill(
    client: _Fetcher, storage: Storage, settings: Settings,
    collections: list[Collection] = COLLECTIONS,
) -> dict[str, int]:
    storage.init_schema()
    counts: dict[str, int] = {}
    for c in collections:
        rows = client.fetch(c.endpoint, settings.history_start, settings.current_day())
        counts[c.name] = storage.upsert(c.name, rows)
    return counts


def incremental(
    client: _Fetcher, storage: Storage, settings: Settings,
    collections: list[Collection] = COLLECTIONS,
) -> dict[str, int]:
    storage.init_schema()
    counts: dict[str, int] = {}
    for c in collections:
        start = storage.last_day(c.name) or settings.history_start
        rows = client.fetch(c.endpoint, start, settings.current_day())
        counts[c.name] = storage.upsert(c.name, rows)
    return counts
