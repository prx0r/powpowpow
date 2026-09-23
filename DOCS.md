# PowPowPow — Complete Documentation

## 1. What is PowPowPow

PowPowPow is a continuously growing, provenance-preserving historical model of how computational resources are valued, allocated and transformed into economic output.

It is NOT a trading system, NOT a crypto dashboard, NOT a content site.

It IS a data garden: fragmented reality (network state, hashrate, difficulty, burns, prices, order books, hardware benchmarks, electricity prices) transformed through a canonical resource graph into persistent compute-economic state, with provenance on every derived number.

The garden loop:
```
COLLECT
  archive raw bytes (lossless, append-only)
NORMALIZE
  timestamp, lineage, source roles
TRANSFORM
  versioned formulas with measured inputs
DERIVE
  signals, factors, analytics
BACKTEST
  empirical distribution vs forward outcomes
PUBLISH
  dashboard, MCP, briefs, pages
```

Every day the garden grows by one unit. Nobody can reconstruct yesterday's order book.

## 2. Principles

**Core invariant**: every derived fact is reproducible from immutable raw bytes plus a versioned transformation.

**Seesaw filter**: a system qualifies only if observable demand creates a binding constraint with a measurable shadow price, capital allocates, and supply responds through observable resources.

**No opinions**: the site shows numbers, not BULL/BEAR. Emission/dollar is a number. Burden ratio is a number. Sell pressure coverage is a number. Let users draw conclusions.

**Epistemic ladder**: OBSERVATION -> METRIC -> SIGNAL -> HYPOTHESIS -> BACKTEST RESULT -> DECISION. Assumptions never masquerade as measured data.

**Storage doctrine**: hot JSONL 7 days -> Parquet forever (25-30x compressed) -> raw append-only forever -> derived tables KBs. Chain bytes (pearld) extract-and-release, never hoarded.

**No TA, no sentiment, no crypto horoscope**: physical/resource causality only. Price is the thing PowPowPow tries to explain, not the primary thing used to explain price.

## 3. How to start everything

**Prerequisites**: Python 3.12+, venv at `/home/ubuntu/.venvs/powpowpow`

```bash
# activate venv
source /home/ubuntu/.venvs/powpowpow/bin/activate

# run tests (should be all green)
python -m pytest tests/ -q

# check what's running
systemctl --user status pow-venue-l2 pow-venue-ws pow-chain-state pow-site

# view collector logs
journalctl --user -u pow-chain-state -n 30

# open the site
# local:  http://localhost:8795/?token=<TOKEN>
# public: https://pow.moltwork.com/?token=<TOKEN>
# token: grep POW_SITE_TOKEN ~/.config/systemd/user/pow-site.service
```

**To restart a service**:
```bash
systemctl --user restart pow-venue-l2   # REST book/ticker/trades
systemctl --user restart pow-venue-ws   # WS tick archive
systemctl --user restart pow-chain-state # QUBIC/XMR/KAS/Nockscan poller
systemctl --user restart pow-site        # consumer site
systemctl --user restart pow-pearld      # pearld node (when syncing)
```

**To run one-shot scripts**:
```bash
python scripts/qubic_epoch.py          # compute QUBIC epoch + burn
python scripts/qubic_computors.py      # snapshot computor set
python scripts/qubic_analytics.py      # build QUBIC analytics bundle
python scripts/xmr_analytics.py        # build XMR analytics bundle
python scripts/build_daily_state.py --date 2026-09-19
python scripts/snapshot_cards.py       # snapshot miner margins
python scripts/compact_stream.py --all-seeds  # compact all Parquet
python scripts/load_cg_history.py --coins XMR,QUBIC
python scripts/collect_releases.py     # GitHub releases
python scripts/powdaily.py             # generate daily brief
python backtest.py QUBIC               # run backtest
```

## 4. Architecture

**Four layers**, each downstream of the previous:

```
RAW COLLECTION
  venue_l2.py    -> REST book/ticker/trades every 60s (CoinEx/Gate/MEXC)
  venue_ws.py    -> WebSocket tick archive (CoinEx/Gate)
  chain_state.py -> QUBIC RPC + XMR localmonero + KAS + Nockscan every 5min
  qubic_epoch.py -> epoch engine every 10min (burn schedule)
  qubic_computors.py -> computor set + Doge tasks every hour
  l2_archival.py -> SafeTrade STAGED (geo-blocked)
  All raw responses archived via core.fetch_json before parsing (lossless)

NORMALIZATION
  warehouse/raw/venue/ -> auto-archived JSON, one file per API response
  warehouse/normalized/ -> partitioned JSONL tables (chain/date/hour)
  warehouse/parquet/    -> compacted Parquet (25-30x, permanent)

TRANSFORMATION
  signals.py        -> miner_pressure_v1, flow_pressure_v1, required_flow_v1
  qubic_epoch.py    -> net emission from burn schedule
  qubic_computors.py -> churn vs prior epoch
  build_daily_state.py -> cross-venue daily aggregates
  snapshot_cards.py -> miner margin history

ANALYTICS / PUBLISH
  qubic_analytics.py -> supply curve, epoch returns, computor economics
  xmr_analytics.py   -> emission value, miner cost benchmarks
  site/server.py     -> REST API + Pi chat
  site/static/index.html -> consumer dashboard
  scripts/powdaily.py -> daily brief
```

**Data flows**:
```
APIs -> core.fetch_json (archive raw) -> collectors normalize -> warehouse
warehouse -> build_daily_state -> Parquet compact -> trim (7d hot)
warehouse -> signals.py -> derived_signal table
warehouse -> analytics scripts -> JSON snapshots
warehouse -> backtest.py -> forward return analysis
warehouse -> site/server.py -> dashboard + MCP
```

## 5. What we collect

**Live venue L2** (every 60s):
- 19 markets: CoinEx (11), Gate (8), MEXC (11 via discovery)
- Per market: orderbook snapshot (20 levels), ticker, trades
- Gap detection, sequence tracking, event-time vs receive-time

**Chain telemetry** (every 5min):
- QUBIC: tick, epoch, peer count (rpc.qubic.org), analytics.qubic.li demand totals
- XMR: difficulty, hashrate, height (localmonero), fee market + p2pool (xmrchain, p2pool.observer)
- KAS: hashrate + price (api.kaspa.org)
- NOCK: height + proof-rate (nockscan)

**QUBIC specials** (hourly/10min):
- Epoch engine: 78.75% burn schedule, net 30.4B/day, 28.96M ticks/epoch
- Computor set: 676 identities, churn vs prior epoch (archive Query API)
- Doge mining tasks: 3 active tasks, 676 sharers

**GitHub** (weekly):
- Releases + commits for 12 repos with auto-classification

**Price history** (monthly Tardis drip + daily CoinGecko):
- 365 days of closes for all core assets
- First-of-month L2 snapshots for KAS/CLORE/FLUX/AKT/NOCK/NOS

## 6. Data warehouse layout

```
warehouse/
  raw/venue/          # Auto-archived raw JSON (every API call)
  raw/qubic/          # QUBIC chain raw
  normalized/         # Partitioned JSONL tables
    orderbook_snapshot/   # chain=venue, date=YYYY-MM-DD, hour=HH.jsonl
    trade/                # same layout
    ticker/
    daily_state/          # cross-venue aggregates
    derived_signal/       # miner_pressure_v1, flow_pressure_v1, etc.
    chain_snapshot/       # QUBIC/XMR/KAS/Nockscan
    network_demand/       # QUBIC tx/transfer/volume
    computor_snapshot/    # QUBIC epoch computor set
    external_mining/      # Doge mining tasks
    miner_card/           # nightly margin snapshots
    fee_market/           # XMR fee rates
    pool_snapshot/        # XMR p2pool
    price_history/        # CoinGecko daily closes
    universe_event/       # listing/delist log
    protocol_event/       # GitHub releases
    repo_commit/          # GitHub commits
  parquet/               # Compacted (permanent, 25-30x smaller)
  qubic_analytics.json   # QUBIC snapshot
  xmr_analytics.json     # XMR snapshot
```

## 7. Metrics and formulas

### Burden (emission pressure)
```
burden = daily_emission_usd / top20_bid_depth
```
Over 1x means one day of printing exceeds visible buy orders.

### Net emission (QUBIC)
```
gross_per_week = 1,000,000,000,000  # constant
burn_rate = 0.7875  # post-epoch-227
net_per_week = gross * (1 - burn)
net_per_day = net_per_week / 7  = 30,357,142,857 QU/day
```

### Net emission (XMR)
```
block_reward = 0.6 XMR  # forever (tail emission)
blocks_per_day = 720     # 2-minute blocks
daily_emission = 432 XMR/day
```

### Miner margin (network-share)
```
rig_coins_day = rig_hashrate / network_hashrate * daily_emission
revenue_usd_day = rig_coins_day * price
net_profit = revenue - electricity - hardware_depreciation
```

### Burden (sell pressure proxy)
```
burden_vs_book = emission_usd / bid_notional_20_sum
```
Disclosed: this is structural creation load, NOT observed miner selling.

### Flow imbalance
```
imbalance = (buy_usd - sell_usd) / (buy_usd + sell_usd)
sell_load = sell_usd / bid_notional_20_sum
```

### Required buy flow
```
required = emission_usd + sell_usd - buy_usd  (floored to 0)
coverage = buy_usd / (emission_usd + sell_usd)
```
Disclosed: limit add/cancel flow unmeasured at daily grain.

## 8. The site

**pow.moltwork.com** — token-gated, black/white/grey, chunky borders.

**Left rail**: HOME (screener), QUBIC, XMR, PRL, KAS, NOCK, XEL, CHAT

**HOME**: burden table sorted by emission-vs-book ratio across core coins.

**QUBIC subtabs**:
- Overview: price, net supply/day, burden, epoch, tick rate, transactions, Doge tasks
- Epoch: progress, 676 computors, burn rate, 52-week return series, supply projection
- Flow: per-venue buy/sell tables, net flow bars, demand totals
- Mining: computor economics table, supply curve, 365d distribution
- Signals: derived signals with drivers and assumptions

**XMR same pattern**: price, emission, hashrate, p2pool miners, fee rate, 365d percentile, Seesaw check, miner cost benchmarks.

**Chat**: Pi harness + opencode-go, garden context injected, data-only fallback.

**Bottom panel**: collector ops + signals, auto-refreshes every 60s.

**Style**: site/STYLE.md — black/grey/white only, chunky 2px borders, monospace numbers, no opinions.

## 9. What's blocked

| Blocker | Status | Unblocks |
|---------|--------|----------|
| SafeTrade geo-block | **FIXED 2026-09-23** — was Cloudflare bot detection, not geo | venue-of-truth for PRL, QUBIC |
| pearld sync | paused (disk triage) | PRL pool->miner->exchange graph |
| KAS hashrate units | unconfirmed | KAS money math |
| AKT/NOS/CLORE endpoints | unreachable from box | rental demand half |
| Tardis paid history | $249/mo needed | historical L2 for QUBIC |

## 10. Current focus

1. QUBIC: complete example coin. All data wired, analytics live, site has 5 subtabs.
2. XMR: same pattern, has p2pool + hashrate + fee market + Seesaw correlation.
3. Every other coin earns its way back through data quality.
4. Backtest grows as STATE accumulates (need 7+ days for meaningful stats).
5. SafeTrade unblock is the single highest-leverage action.

## 11. Design research index

| File | Content |
|------|---------|
| 01_architecture_and_vision.md | System design, universal schema, per-chain data sources |
| 02_pressure_equation_research.md | Academic references, Seesaw formulas, OFI, two-timescale model |
| 03_seesaw_filter.md | Inclusion criteria (7 requirements + 2 bonus) |
| 04_canonical_universe_v1.md | 16 candidate systems, V1 admission rules |
| 05_extended_coin_research.md | TAO/KAS/QRL/ZEPH/ALPH/ERG/XTM + indices |
| 06_moat_strategy.md | Moat theory (historical causal record, 8 moat layers) |
| 07_coin_categories.md | Category system + cross-category comparisons |
| transforms.md | Formula registry: live vs queued with blockers |
| failures.md | Every thing tried, what broke, what unblocks |
| devplancurrent.md | Full garden thesis |
| TODO.md | Current work list with progress |
| site/STYLE.md | Visual design rules |
| HANDOVER.md | Next-agent quick reference |
