# Transformation registry — 01-doc formulas vs implementation

> Every formula from `01_architecture_and_vision.md` §10 + Qubic metrics,
> each marked LIVE (code + provenance) or QUEUED (blocker named).
> A formula graduates only with measured inputs on both sides.

## Cross-chain factor table (§10)

| Factor | Status | Implementation |
|---|---|---|
| `issuance_usd_24h` | LIVE | fundamentals / engine emission × STATE mid (`factors.py`) |
| `issuance_to_mcap` | QUEUED | needs circulating-supply series per asset |
| `issuance_to_volume` | LIVE | emission / venue trade notional (`factors.py`) |
| `issuance_to_bid_depth` (burden) | LIVE | emission / top-20 resting notional (`signals.py` v1) |
| `miner_profit_margin` | LIVE | cards v2 network-share (`v1_live_cards.py`); KAS gated |
| `hashrate_growth` | QUEUED | needs 7d+ hashrate series (polling; lands within days) |
| `price_hashrate_divergence` | QUEUED | needs price + hashrate history (CG backfill + polls) |
| `miner_to_exchange_flow` | QUEUED | needs pool graph (pearld syncing) |
| `compute_units` | PARTIAL | Qubic tx/volume totals, Nock proof-rate; per-unit cost queued |
| `subsidy_per_compute` | QUEUED | needs compute_units everywhere first |
| `compute_growth` | PARTIAL | Qubic demand deltas accumulate (need 24h span) |
| `book_imbalance` | LIVE | per-snapshot + WS ticks |
| `aggressive_flow` | LIVE | venue trades with sides (`flow_pressure_v1`) |
| `protocol_event` | PARTIAL | releases/commits collected; detection rules queued |
| `developer_activity` | LIVE | commit rows per repo (`collect_releases.py`) |

## Derived composites (§10)

| Composite | Status | Notes |
|---|---|---|
| `ABSORPTION_PRESSURE` | LIVE | as `burden_vs_book` |
| `MINER_STRESS` | QUEUED | electricity input per region missing |
| `COMPUTE_EFFICIENCY` | QUEUED | needs external compute price + subsidy/unit |
| `FUNDAMENTAL_MOMENTUM` | QUEUED | needs compute + mcap time series |
| `REFLEXIVITY` | QUEUED | needs lag-tested correlations (backtest grows into this) |
| `required_buy_flow_zero_return` | LIVE | `required_flow_v1` (limit add/cancel unmeasured, disclosed) |

## Qubic metrics (01 §2)

| Metric | Status | Notes |
|---|---|---|
| `net_issuance_usd_day` | LIVE | epoch engine: 1T gross × (1 − 0.7875 burn) (`qubic_epoch.py`) |
| `burn_ratio` | LIVE | schedule-derived 78.75% (live burn total queued: archiver endpoints) |
| `net_dilution_rate` | QUEUED | needs circulating series |
| `emission_absorption` (venue volume / net issuance) | LIVE | adapted to CoinEx+Gate+MEXC (SafeTrade blocked) |
| `exchange_balance_delta` | QUEUED | needs exchange labels (pearld-side work for PRL; Qubic static labels 403) |
| `epoch_return` / `return_since_epoch_start` | QUEUED | needs CG Qubic history (id found: `qubic-network`; loader supports it) |
| `computor concentration` | QUEUED | archiver endpoints |
| `price / net_emission`, `FDV / net_emission` | LIVE | computable from STATE + fundamentals on demand |

## Rules

1. No formula ships on a single hardcoded constant without a source.
2. Every derived value cites inputs + code version + date.
3. Queued items name their blocker; blockers live in `failures.md`.
