from datetime import date

from oura_dash.storage import Storage


def test_upsert_is_idempotent():
    with Storage(":memory:") as s:
        s.init_schema()
        rows = [{"id": "a", "day": "2024-01-01", "v": 1}]
        assert s.upsert("daily_stress", rows) == 1
        s.upsert("daily_stress", [{"id": "a", "day": "2024-01-01", "v": 2}])
        stored = s.read("daily_stress")
        assert len(stored) == 1
        assert stored[0]["v"] == 2


def test_read_orders_by_day():
    with Storage(":memory:") as s:
        s.init_schema()
        s.upsert("daily_stress", [
            {"id": "b", "day": "2024-01-02", "v": 2},
            {"id": "a", "day": "2024-01-01", "v": 1},
        ])
        assert [r["day"] for r in s.read("daily_stress")] == ["2024-01-01", "2024-01-02"]


def test_last_day():
    with Storage(":memory:") as s:
        s.init_schema()
        assert s.last_day("daily_stress") is None
        s.upsert("daily_stress", [
            {"id": "a", "day": "2024-01-01"}, {"id": "b", "day": "2024-01-05"},
        ])
        assert s.last_day("daily_stress") == date(2024, 1, 5)


def test_rows_without_id_skipped():
    with Storage(":memory:") as s:
        s.init_schema()
        assert s.upsert("session", [{"day": "2024-01-01"}]) == 0


def test_upsert_uses_start_day_when_no_day():
    with Storage(":memory:") as s:
        s.init_schema()
        s.upsert("enhanced_tag", [{"id": "t1", "start_day": "2026-06-20"}])
        assert s.last_day("enhanced_tag") == date(2026, 6, 20)
