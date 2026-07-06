# PROGRESS — forward-only step oracle

Rules: a task's box is checked **only** after its tests pass (`pytest` green for
that task's test file). Do not start a task until every box above it is checked.

- [x] Task 0 — Scaffold, tooling, oracle (`pytest` runs; `oura-dash --help` works)
- [x] Task 1 — config.py (`tests/test_config.py`)
- [x] Task 2 — models.py (`tests/test_models.py`)
- [x] Task 3 — collections.py registry (`tests/test_collections.py`)
- [x] Task 4 — client.py (`tests/test_client.py`)
- [x] Task 5 — storage.py (`tests/test_storage.py`)
- [x] Task 6 — sync.py (`tests/test_sync.py`)
- [x] Task 7 — metrics.py (`tests/test_metrics.py`)
- [x] Task 8 — stats.py (`tests/test_stats.py`)
- [x] Task 9 — cli.py (`tests/test_cli.py`)
- [x] Task 10 — app.py (`tests/test_app.py`)
- [x] Task 11 — integration + docs (`tests/test_integration_sandbox.py`, README)
