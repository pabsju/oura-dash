from datetime import date

import httpx
import respx

from oura_dash.client import OuraClient

BASE = "https://api.ouraring.com"
EP = "/v2/usercollection/daily_stress"


@respx.mock
def test_fetch_follows_pagination():
    route = respx.get(f"{BASE}{EP}")
    route.side_effect = [
        httpx.Response(200, json={"data": [{"id": "1"}], "next_token": "t2"}),
        httpx.Response(200, json={"data": [{"id": "2"}], "next_token": None}),
    ]
    rows = OuraClient("tok").fetch(EP, date(2024, 1, 1), date(2024, 1, 2))
    assert [r["id"] for r in rows] == ["1", "2"]
    # second request carried the next_token param
    assert "next_token=t2" in str(route.calls[1].request.url)


@respx.mock
def test_fetch_sends_auth_and_dates():
    route = respx.get(f"{BASE}{EP}").mock(
        return_value=httpx.Response(200, json={"data": [], "next_token": None})
    )
    OuraClient("secret").fetch(EP, date(2024, 1, 1), date(2024, 1, 31))
    req = route.calls[0].request
    assert req.headers["authorization"] == "Bearer secret"
    assert "start_date=2024-01-01" in str(req.url)
    assert "end_date=2024-01-31" in str(req.url)


@respx.mock
def test_fetch_retries_on_429():
    sleeps: list[float] = []
    route = respx.get(f"{BASE}{EP}")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(200, json={"data": [{"id": "ok"}], "next_token": None}),
    ]
    client = OuraClient("tok", sleep=sleeps.append)
    rows = client.fetch(EP, date(2024, 1, 1), date(2024, 1, 2))
    assert rows == [{"id": "ok"}]
    assert sleeps == [2.0]


@respx.mock
def test_fetch_raises_after_max_retries():
    respx.get(f"{BASE}{EP}").mock(return_value=httpx.Response(429, headers={"Retry-After": "0"}))
    client = OuraClient("tok", max_retries=2, sleep=lambda _s: None)
    try:
        client.fetch(EP, date(2024, 1, 1), date(2024, 1, 2))
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 429
