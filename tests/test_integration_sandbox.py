from datetime import date

import pytest

from oura_dash.client import OuraClient

SANDBOX = "https://api.ouraring.com/v2/sandbox"


@pytest.mark.integration
def test_sandbox_daily_stress_shape():
    client = OuraClient("sandbox", base_url=SANDBOX)
    rows = client.fetch("/usercollection/daily_stress", date(2024, 1, 1), date(2024, 1, 5))
    assert rows, "sandbox returned no rows"
    r = rows[0]
    assert "id" in r and "day" in r
    assert "stress_high" in r


@pytest.mark.integration
def test_sandbox_sleep_has_hrv():
    client = OuraClient("sandbox", base_url=SANDBOX)
    rows = client.fetch("/usercollection/sleep", date(2024, 1, 1), date(2024, 1, 8))
    assert rows
    assert any("average_hrv" in r for r in rows)
