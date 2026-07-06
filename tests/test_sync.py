from datetime import date

from oura_dash.collections import Collection
from oura_dash.config import Settings
from oura_dash.storage import Storage
from oura_dash import sync


class FakeClient:
    def __init__(self, rows_by_endpoint):
        self.rows_by_endpoint = rows_by_endpoint
        self.calls = []

    def fetch(self, endpoint, start, end):
        self.calls.append((endpoint, start, end))
        return self.rows_by_endpoint.get(endpoint, [])


def _settings():
    return Settings(token="x", today=date(2026, 7, 6), history_start=date(2020, 1, 1))


def test_backfill_stores_rows():
    cols = [Collection("daily_stress", "/v2/usercollection/daily_stress")]
    client = FakeClient({"/v2/usercollection/daily_stress": [{"id": "a", "day": "2020-05-01"}]})
    with Storage(":memory:") as st:
        counts = sync.backfill(client, st, _settings(), collections=cols)
        assert counts["daily_stress"] == 1
        assert client.calls[0] == ("/v2/usercollection/daily_stress", date(2020, 1, 1), date(2026, 7, 6))
        assert len(st.read("daily_stress")) == 1


def test_incremental_starts_from_last_day():
    cols = [Collection("daily_stress", "/v2/usercollection/daily_stress")]
    client = FakeClient({"/v2/usercollection/daily_stress": [{"id": "a", "day": "2026-06-30"}]})
    with Storage(":memory:") as st:
        st.init_schema()
        st.upsert("daily_stress", [{"id": "a", "day": "2026-06-30"}])
        sync.incremental(client, st, _settings(), collections=cols)
        assert client.calls[0][1] == date(2026, 6, 30)  # re-fetches last stored day
        assert client.calls[0][2] == date(2026, 7, 6)


def test_incremental_empty_starts_from_history():
    cols = [Collection("daily_stress", "/v2/usercollection/daily_stress")]
    client = FakeClient({})
    with Storage(":memory:") as st:
        sync.incremental(client, st, _settings(), collections=cols)
        assert client.calls[0][1] == date(2020, 1, 1)
