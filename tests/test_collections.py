from oura_dash.collections import COLLECTIONS, by_name, collection_names


def test_registry_has_core_collections():
    names = set(collection_names())
    for expected in {
        "daily_stress", "sleep", "daily_activity", "daily_readiness",
        "daily_sleep", "daily_spo2", "daily_resilience",
        "daily_cardiovascular_age", "vO2_max", "workout", "session",
        "enhanced_tag", "rest_mode_period",
    }:
        assert expected in names


def test_endpoints_are_usercollection_paths():
    for c in COLLECTIONS:
        assert c.endpoint == f"/v2/usercollection/{c.name}"


def test_by_name_lookup():
    assert by_name["daily_stress"].endpoint == "/v2/usercollection/daily_stress"
