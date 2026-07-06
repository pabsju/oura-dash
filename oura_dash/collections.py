from dataclasses import dataclass


@dataclass(frozen=True)
class Collection:
    name: str
    endpoint: str


_NAMES = [
    "daily_activity", "daily_readiness", "daily_sleep", "daily_spo2",
    "daily_stress", "daily_resilience", "daily_cardiovascular_age",
    "sleep", "vO2_max", "workout", "session",
    "enhanced_tag", "rest_mode_period",
]

COLLECTIONS = [Collection(n, f"/v2/usercollection/{n}") for n in _NAMES]
by_name = {c.name: c for c in COLLECTIONS}


def collection_names() -> list[str]:
    return [c.name for c in COLLECTIONS]
