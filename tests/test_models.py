from oura_dash.models import CollectionResponse


def test_parses_envelope_and_next_token():
    payload = {
        "data": [{"id": "x", "day": "2024-01-01", "stress_high": 340}],
        "next_token": "abc",
    }
    r = CollectionResponse.model_validate(payload)
    assert r.next_token == "abc"
    assert r.data[0]["stress_high"] == 340


def test_missing_next_token_defaults_none():
    r = CollectionResponse.model_validate({"data": []})
    assert r.next_token is None
    assert r.data == []
