# Oura Dashboard — Design Spec

**Date:** 2026-07-06
**Status:** Approved (pending spec review)

## Goal

Personal web dashboard for Oura Ring data. View metrics through the day, updated
hourly. Pull all historical data. Benchmark whether an intervention period
(**2026-06-16 → 2026-09-16**) shows statistically significant differences in any
metric versus baseline (all history before 2026-06-16).

Public repo → well-tested throughout. A forward-only markdown step tracker acts as
the test oracle: a step is only marked done when its tests pass.

## API reality (from live OpenAPI spec v1.35)

Determines what "throughout the day" can mean:

| Metric | Granularity | Source endpoint |
|---|---|---|
| **Heart rate** | True intraday (all-day bpm samples) | `heartrate` (needs Gen3 ring — confirmed present) |
| **HRV** | Nightly only (`average_hrv` + intraday samples *during sleep*) | `sleep` |
| **Stress** | Daily only (`stress_high`, `recovery_high` seconds; `day_summary` enum) | `daily_stress` |
| Everything else | Daily summaries or per-event | see below |

- **Auth:** Personal Access Token (single `Authorization: Bearer <token>` header).
  OAuth2 exists but is unnecessary for single-user.
- **Pagination:** `next_token` cursor on collection endpoints.
- **Sandbox:** `/v2/sandbox/usercollection/*` returns real-shaped example payloads
  with *any* bearer string. Used for CI integration tests — no secret required.
- **Interim caveat:** today is 2026-07-06; intervention window closes 2026-09-16,
  so the benchmark is an interim result until then.

### Collections tracked

**Benchmarkable (daily numeric time series):**
- `daily_activity` — steps, active/total/target calories, MET minutes, high/med/low
  activity time, sedentary time, activity score, equivalent walking distance
- `daily_readiness` — score, temperature deviation, contributors
- `daily_sleep` — sleep score
- `daily_spo2` — average SpO2 %, breathing disturbance index
- `daily_stress` — stress_high, recovery_high (seconds)
- `daily_resilience` — level (ordinal), contributors
- `daily_cardiovascular_age` — vascular age
- `sleep` (nightly) — average_hrv, average/lowest heart rate, efficiency, latency,
  stage durations, time in bed
- `vO2_max` — VO₂ max
- `workout` — aggregated to daily count / duration / calories
- `session` — aggregated to daily count / duration
- `heartrate` — intraday bpm (also yields daily resting/min HR)

**Contextual (stored, flagged, NOT benchmarked):**
- `tag`, `enhanced_tag` — user annotations; potential confounders shown alongside
- `rest_mode_period` — illness/travel; flagged in analysis, optionally excluded
- `personal_info` — static demographics
- `ring_configuration`, `ring_battery_level` — device metadata

## Architecture

Small, single-purpose modules with clear interfaces:

| Module | Responsibility | Depends on |
|---|---|---|
| `models.py` | Pydantic models mirroring API schemas | — |
| `client.py` | HTTP client: bearer auth, **generic paginated collection fetcher** parameterized by (endpoint, model), 429 backoff, date-chunking | models |
| `storage.py` | SQLite: one table per collection, idempotent upsert by `id`/`day`, read helpers → pandas DataFrames | models |
| `sync.py` | Orchestrates `backfill` (all history) + `incremental` (since last stored row) across the collection registry | client, storage |
| `stats.py` | Benchmark engine (below) | storage |
| `config.py` | pydantic-settings: `OURA_TOKEN`, DB path, window dates | — |
| `cli.py` | typer CLI: `backfill`, `sync`, `stats`, `serve` | all |
| `app.py` | Streamlit dashboard | storage, stats |

### Collection registry

A single registry maps each collection → (endpoint path, pydantic model, primary
key, date-param style). `client` and `sync` iterate the registry, so adding a
metric is one entry, not new code. `daily_*` endpoints use `start_date`/`end_date`;
`heartrate` uses `start_datetime`/`end_datetime`.

## Data flow

```
cron (hourly) → `oura-dash sync` → client → pydantic models → SQLite
                                                                  │
                          Streamlit app  ◄──────────────────────┤ (read-only)
                          stats engine   ◄──────────────────────┘
```

Hourly refresh documented in README (cron line + systemd-timer alternative).
`sync` is idempotent: re-running never duplicates rows.

## Dashboard (Streamlit + Plotly)

- **Today** — intraday heart-rate chart; latest daily stress + nightly HRV; last-sync badge.
- **Trends** — daily time series for every benchmarkable metric, with the
  intervention window shaded.
- **Benchmark** — per-metric stat table (baseline vs intervention: n, medians,
  effect size + CI, p, q) and before/after distribution plots.

## Statistics

Per benchmarkable metric:
1. Split into baseline (`day < 2026-06-16`) vs intervention (`06-16 ≤ day ≤ 09-16`).
2. **Mann-Whitney U** (non-parametric; robust to non-normal wearable data).
3. **Benjamini-Hochberg FDR** across all metrics → q-values.
4. Effect size: **Cliff's delta** with bootstrap CI. Report n, medians both groups.

Statistical honesty surfaced in output and UI:
- **Interim warning** while today < 2026-09-16 (window incomplete).
- **Autocorrelation caveat**: daily wearable series are not iid; p-values are
  approximate. (Block-bootstrap left as a documented future extension.)
- Effect sizes + CIs reported alongside p/q, never p-values alone.
- Rest-mode / tagged days flagged; option to exclude from analysis.

## Testing (TDD)

- **Unit:** model validation (nulls, edge fields); client pagination / backoff /
  date-chunking (respx mocks); storage upsert idempotency (in-memory SQLite);
  stats correctness vs hand-computed fixtures (known U/p, known Cliff's delta,
  BH-FDR ordering).
- **Integration:** hit the live **sandbox** with a dummy token — verifies real API
  shape end-to-end, CI-safe, no secret.
- **Edge:** empty date ranges; missing intraday (non-Gen3 fallback); incomplete
  intervention window (interim result); collections returning zero rows.

## Test oracle — `docs/PROGRESS.md`

Ordered, gated checklist. Forward-only: each step is checked off *only* when its
tests are green, and later steps stay locked until earlier ones complete. Serves as
both progress tracker and the "moves forward only when earlier steps complete"
oracle.

## Tech stack

Python 3.11+ · httpx · pydantic + pydantic-settings · typer · sqlite3 (stdlib) ·
pandas · scipy · statsmodels · streamlit · plotly · pytest + respx · ruff · mypy ·
conda `environment.yml` (+ `requirements.txt` fallback).

## Config & secrets

`.env` (gitignored) holds `OURA_TOKEN`. `.env.example` committed. Window dates and
DB path overridable via env / CLI flags. No secrets in repo or CI.

## Out of scope (YAGNI)

OAuth2 multi-user; webhook subscriptions (polling is simpler for single-user);
cloud hosting; write-back to Oura; block-bootstrap CIs (documented as future work).
