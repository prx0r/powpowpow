# pow.systems — live runbook

Public dashboard for XMR / BTC / QUBIC live tick pricing and mining data.

- Public URL: `https://pow.systems/` — no token needed for reads.
- Analyst chat (POST `/api/chat`) still requires a site token.
- Token source (server only, mode 600): `~/.config/powpowpow/site.env`
- Legacy token page (only needed if you want to use chat): `https://pow.systems/access.html`

## Architecture

```
SafeTrade WS ──▶ collectors/l2_archival.py ──┐
QUBIC/XMR/BTC REST ─▶ collectors/chain_state.py ─┼─▶ warehouse/ ──▶ site/server.py (127.0.0.1:8795)
QUBIC epoch/computors timers ────────────────────┘         │                │
R2 verified backup ◀── scripts/r2_upload.py ◀──────────────┘                ▼
                                                      Cloudflare Tunnel ─▶ pow.systems
```

- Origin stays on loopback; only Cloudflare Tunnel exposes it.
- Reads (dashboard + market/mining APIs) are public; analyst chat is token-gated.
- Chat token is remembered per browser via `access.html`.
- Every normalized row carries `raw_event_id` back to an immutable raw observation.

## Home tab (`/`)

Rendered from a single `GET /api/home` payload:

| Section | Source |
|---|---|
| NETWORKS (price, new $/day, hashrate/epoch/height, freshness) | `chains/network_state.json` + `chains/factors/cross_chain_factors.json` + `signals.load_emission` |
| COLLECTION (services, heartbeat age, disk, STATE/signals counts, health) | `systemctl --user`, `warehouse/*_heartbeat.json`, `shutil.disk_usage`, `scripts/health_check.py` |
| MARKET (price, new $/day, burden) | `chains/factors/cross_chain_factors.json` |
| SIGNALS (asset, signal, z, strength, source) | `warehouse/normalized/derived_signal/` |

The home view refreshes every 60s while active. Signals are shown as numeric
z-scores with their evidence source — no directional language in the UI.

## Daily STATE chain

`pow-daily-state.timer` runs hourly at :25 UTC:

```bash
python3 scripts/build_daily_state.py --date $YESTERDAY
python3 scripts/build_daily_state.py --date $TODAY
python3 signals.py --date $YESTERDAY
python3 signals.py --date $TODAY
python3 factors.py --date $TODAY
python3 scripts/build_insights.py --date $TODAY
```

Rollups are idempotent: `core.purge_normalized(table, field, value)` removes
the previous output for that date before rebuilding, so an hourly rerun
replaces rows instead of duplicating them.

## Insight metrics vs price

`transforms/` holds pure, versioned, I/O-free metric functions;
`scripts/build_insights.py` reads the warehouse, computes them and writes
`warehouse/insights.json`. Served at `GET /api/insights` and rendered as the
**INSIGHT VS PRICE** table on the home tab.

| Family | Metric | Source history |
|---|---|---|
| Miner revenue | `puell_multiple` | `price_history` × daily emission, 365d window |
| Security | `security_spend_ratio` | `blockchain.info` supply × price × emission |
| Divergence | `price_hashrate_divergence` | `price_history` vs `chain_snapshot` hashrate |
| Tick quality | `tick_quality_ribbon` | `qubic_stats` snapshots (needs ≥13) |
| Addresses | `active_address_growth` | `qubic_stats` snapshots |
| Burns | `burn_epoch_total`, `burn_deviation_vs_schedule`, `burn_concentration_at_epoch_start`, `burn_trickle_rate` | `getEventLogs` `logType=8` |
| Holdings | `exchange_reserve`, `wealth_concentration`, `exchange_share_of_top_holders` | `static.qubic.org` exchanges × `live/v1/balances`, `/v1/rich-list` |
| Activity | `measured_active_addresses`, `transfer_rate`, `exchange_netflow`, `whale_share_of_volume` | `getEventLogs` `logType=0` (`quTransfer`) |
| Price fit | `metric_vs_price_corr` | metric series vs daily closes (needs ≥30) |

Every metric carries `n`, `min_n`, `source`, `window` and `version`. When a
metric cannot be computed honestly it returns `refused: true` with a reason
instead of a number — the dashboard renders those rows as `REFUSED` with the
reason, never as `—`.

Burn structure discovered while building this: the epoch's burn is two large
contract burns at the first tick of the epoch (≈99.8% of the total) followed by
a long trickle of small deductions. A uniform QU-per-tick average would be
meaningless, which is why burn is reported as four separate metrics.
`burn_deviation_vs_schedule` currently reads ~0.996×, i.e. observed burn is
within 0.4% of `gross_per_week × burn_rate` — an independent check that the
emission model in `network_state` is right.

## powops monitoring

`scripts/pipeline_status.py` emits the powops contract (see
`/root/powstock/POWOPS_INTEGRATION.md`): a heartbeat artifact plus one
`collector_run`-shaped row per source.

| Artifact | Contract |
|---|---|
| `warehouse/powpowpow_heartbeat.json` | `heartbeat_at`, `mode`, `total_records`, `sources_run`, `sources_failed`, `results` |
| `warehouse/collector_run.json` | `source_id`, `started_at`, `status`, `error`, `duration_seconds`, `source_records_new`, `raw_new` |

Status values follow powops: `ok` · `stale` · `error` · `unknown` · `not_installed`.

Fourteen sources are tracked: `safetrade_l2`, `chain_state`, `qubic_epoch`,
`qubic_stats`, `qubic_holdings`, `qubic_transfers`, `qubic_computors`, `daily_state`,
`derived_signals`, `cross_chain_factors`, `insights`, `mining_analytics`,
`r2_sync`, `pow_site`.

- `GET /powops` — human page (public, SSE-free, no token)
- `GET /powops.json` — machine payload, cached 60s
- Home tab → `PIPELINE` stat links to it

`pow-health.service` runs `pipeline_status.py` **then** `health_check.py`, so a
dead `pow-daily-state.timer` now fails the 5-minute health check instead of
passing silently. `health_check.CHECKS` covers `daily_state`,
`derived_signals`, `factors`, `computor_snapshot`, `pipeline_status` and
`r2_sync` in addition to collector/analytics freshness.

## QUBIC official stats (added 2026-09-25)

Three unauthenticated endpoints, verified live. Collected by
`collectors/qubic_stats.py` (service `pow-qubic-stats`, 300s cadence):

| Endpoint | Metric families |
|---|---|
| `GET rpc.qubic.org/v1/latest-stats` | circulating supply, **active addresses**, price, market cap, epoch/tick, **epoch + last-10k tick quality**, **burned QUs** |
| `POST rpc.qubic.org/query/v1/getEventLogs` (`logType=8`) | per-event burn records for the current epoch |
| `GET rpc.qubic.org/v1/rich-list?page&page_size` | top holders, 100 per snapshot |

Tables: `qubic_stats`, `qubic_burn_event`, `qubic_rich_list` — all classified
`ephemeral` (our own point-in-time observations, never pruned as
"re-fetchable"). `network_state.QUBIC` gains `active_addresses`,
`epoch_tick_quality`, `last10000_tick_quality`, `burned_qus`,
`circulating_supply`, `market_cap`, `price_usd`.

Burn rows are **purged and re-written per epoch** so each pass is idempotent
(`purge_normalized('qubic_burn_event', 'event_time', epoch)`), up to 5 pages ×
1000 events. Older events stay reachable in the archived raw responses.

### Upstream intel (from `qubic/integration`)

- Epoch transition is **Wednesday 12:00 UTC**; network data is pruned each
  epoch. Our normalized rows are never pruned — archive in-process or lose it.
- **Archiver API is deprecated and removed by end of 2026.** Migrate to the
  Query API (`integration/Partners/migration.md:42`). `chain_state.poll_qubic`
  still reads `/v1/status` — that is the next migration target.
- Per-epoch burn/deduction summaries are blocked upstream
  (`qubic/integration#102`); we reconstruct from `BURNING` (logType 8) events.

### Canonical source registry

Full list of every QUBIC endpoint probed today, what works, what is dead and
what is collected — including exchange-label and balance endpoints — lives in
`docs/qubic-sources.md`.

### Cloned sources

`/root/qubic-sources/` (outside this repo, not committed):

| Repo | What it gave us |
|---|---|
| `qubic/qubic-stats-service` | the `/v1/latest-stats` + `/v1/rich-list` contract (its own swagger says `host: rpc.qubic.org`) |
| `qubic/integration` | Query API OpenAPI, migration table, epoch/pruning rules |
| `fyllepo/qubic-mcp` | reference MCP surface — study before designing our own |
| `tomaspozo/qubic-metrics` | historical analytics (needs a token) |
| `Pickle-Pixel/qubic-dashboard` | pool metrics → needs JWT via `api.qubic.li/Auth/Login`; `stats-test.qubic.li` unreachable from this box |
| `qubic/go-data-publisher` | Go message-broker publishers; streaming alternative to polling, not wired |

Not cloned: the repo containing `SOURCES.md`/`TRANSFORMS.md`/
`transforms/puell.py` was described but no URL was given.

## Systemd units (user scope)

| Unit | Role | Schedule |
|---|---|---|
| `pow-safetrade-l2.service` | SafeTrade WS depth/trades/tickers | always, restart |
| `pow-chain-state.service` | QUBIC/XMR/BTC polls, 300s cadence | always, restart |
| `pow-qubic-stats.service` | QUBIC official stats: active addresses, tick quality, burned QUs, burn events, rich list | always, restart, 300s |
| `pow-qubic-epoch.service/.timer` | Epoch, burn, tick rate | every 10 min |
| `pow-qubic-holdings.service` | QUBIC exchange reserves + wealth concentration | always, restart, 300s (rich list every 6h) |
| `pow-qubic-transfers.service` | QUBIC transfer activity: measured addresses, exchange netflow | always, restart, 300s |
| `pow-qubic-computors.service/.timer` | Computor set + DOGE leg | hourly |
| `pow-daily-state.service/.timer` | STATE + signals + factors rebuild | hourly :25 |
| `pow-mining-analytics.service/.timer` | XMR/QUBIC/BTC context + backtest | every 6 h |
| `pow-r2-upload.service/.timer` | Verified R2 sync + retention | hourly |
| `pow-warehouse-compact.service/.timer` | Closed-date Parquet compaction | daily 00:12 UTC |
| `pow-health.service/.timer` | pipeline status + freshness checks, fails loudly | every 5 min |
| `pow-site.service` | Dashboard origin | always, restart |
| `pow-cloudflared.service` | Tunnel daemon | always, restart |

## R2 backup and retention

- Bucket `powpowpow-warehouse`, prefix `powpowpow/`; `chains/` snapshots under `powpowpow/chains/`.
- Uploads are SHA-256 + size verified after PUT; byte-identical objects get server-side metadata copies.
- Local deletion happens only after a fresh remote HEAD check:
  `raw` 24h, `normalized` 30h, `parquet` 168h. `chains/` is never deleted.
- Credentials live in the `oracle` vault (`CLOUDFLARE_R2_*`); units fetch names only, never embed values.

## Cloudflare

- Tunnel ID `2131eb3e-f087-44c2-bde5-fdc32d9f98bb`, config `/root/.cloudflared/config.yml`.
- Ingress: `pow.systems → http://127.0.0.1:8795`.
- DNS: apex `CNAME @ → <tunnel-id>.cfargotunnel.com`, proxied.
- TLS is terminated by Cloudflare; origin is plain HTTP on loopback only.

## Token handling

- Tokens are per-boot random unless `POW_SITE_TOKEN` is set in `site.env`.
- After any suspected leak: generate a new token, `chmod 600` the file, restart `pow-site`.
- Never commit tokens; keep the repo secret-scan pattern enabled (token prefixes).

## Verification

```bash
systemctl --user list-units 'pow-*' --all --no-pager
python3 scripts/health_check.py
python3 -m pytest tests/ -q
```

Public checks (no token required for reads):

- `GET https://pow.systems/` → 200 dashboard.
- `GET https://pow.systems/api/health` → `{"ok": true, …}`.
- `GET https://pow.systems/api/ticks?symbols=btcusdt,xmrusdt,qubicusdt` → SSE stream.
- `GET https://pow.systems/api/chain?symbol=XMR|QUBIC|BTC` → 200 with fresh `as_of`.
- `GET https://pow.systems/api/home` → 200 with `chains`, `ops`, `storage`, `signals`, `state`, `health`, `pipeline`.
- `GET https://pow.systems/api/insights` → 200 with `chains`, `summary` (`computed` / `refused`), `version`.
- `GET https://pow.systems/powops` → 200 HTML pipeline page; `/powops.json` → 200 with 14 sources.
- `POST https://pow.systems/api/chat` without token → 403 (chat remains gated).

## Troubleshooting

- Chat rejected: open `/access.html`, paste the current token from `site.env`; the browser remembers it. Rotate the token if it was ever shared or leaked, then restart `pow-site`.
- Reads return 403: a token requirement regressed — GET must stay public. Only `do_POST` may be gated.
- Stale mining numbers: check `pow-health.service` output and `chains/network_state.json` `as_of` timestamps.
- Disk pressure: collectors pause below `POW_MIN_FREE_BYTES` (2 GiB); R2 sync must be completing hourly.
- Known test failure: `test_garden.py::test_lineage_resolves` (isolation bug, pre-existing).
