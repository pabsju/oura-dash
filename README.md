# oura-dash

Personal Oura Ring daily-metrics dashboard and configurable-window statistical
benchmark. Pulls all historical daily data into SQLite, visualizes trends, and
tests whether a date window (default **2026-06-16 → 2026-09-01**) differs
significantly from baseline history (Mann-Whitney U + Benjamini-Hochberg FDR +
Cliff's delta).

## What the Oura API actually exposes

All tracked metrics are **daily**. Stress is daily (`stress_high`,
`recovery_high`); HRV and sleeping heart rate are **nightly** (`average_hrv`,
`average_heart_rate`, `lowest_heart_rate` from the `sleep` endpoint). No intraday
data is collected — the analysis operates on daily values.

## Setup

```bash
mamba env create -f environment.yml
mamba activate oura-dash
cp .env.example .env   # then paste your Personal Access Token
```

Get a Personal Access Token at https://cloud.ouraring.com/personal-access-tokens .

## Usage

```bash
oura-dash backfill   # one-time: pull all history
oura-dash sync       # incremental: new days since last sync
oura-dash stats      # print the benchmark table
oura-dash serve      # launch the Streamlit dashboard (http://localhost:8501)
```

Override the window without code changes:
```bash
oura-dash stats --window-start 2025-01-01 --window-end 2025-04-01
```

## Daily automatic sync

Cron (runs 06:00 daily):
```cron
0 6 * * * cd /path/to/oura_dash && /path/to/mamba run -n oura-dash oura-dash sync >> sync.log 2>&1
```

systemd timer alternative:
```ini
# ~/.config/systemd/user/oura-sync.service
[Service]
Type=oneshot
WorkingDirectory=%h/Projects/oura_dash
ExecStart=%h/mambaforge/envs/oura-dash/bin/oura-dash sync

# ~/.config/systemd/user/oura-sync.timer
[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true
[Install]
WantedBy=timers.target
```
Enable: `systemctl --user enable --now oura-sync.timer`.

## Statistical notes

- Effect sizes (Cliff's delta) and 95% bootstrap CIs are reported alongside
  p/q-values — never p-values alone.
- Daily wearable series are autocorrelated (not i.i.d.), so p-values are
  approximate. A moving-block bootstrap is documented future work.
- While today precedes the window end, results are flagged **interim**.

## Development

```bash
pytest              # unit tests (fast, no network)
pytest -m integration   # live-sandbox integration tests
ruff check . && mypy oura_dash
```

## Deviations & roadmap

Where the implementation intentionally differs from (or narrows) the original
design spec:

- **Nightly sleep metrics use only the main long sleep.** HRV, resting/average
  heart rate, and sleep efficiency are extracted only from `sleep` records
  with `type == "long_sleep"`; naps (`sleep`, `late_nap`, `rest` types) are
  excluded so they don't bias nightly averages.
- **Collections synced but not yet benchmarked.** `daily_resilience`,
  `workout`, and `session` are fetched and stored but don't have metric
  extractors yet (resilience is an ordinal level; workout/session would need
  per-event-to-daily aggregation). `enhanced_tag` and `rest_mode_period` are
  stored as intended covariates but aren't yet surfaced on the dashboard or
  used to flag/exclude days from the benchmark. These are roadmap items.
- **Statistical caveats.** Daily series are autocorrelated, so p-values are
  approximate (a moving-block bootstrap is future work). Cliff's-delta
  bootstrap CIs degenerate to a point interval when the two groups separate
  completely (|delta| = 1); treat such CIs as optimistic.
- **Benchmark window** is selectable in the dashboard's Benchmark tab and via
  `oura-dash stats --window-start/--window-end`; it defaults to
  **2026-06-16 → 2026-09-01**, and results are flagged interim until the
  window closes.

## License

MIT — see [LICENSE](LICENSE).
