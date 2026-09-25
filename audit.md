> **STALE 2026-09-25 — verification lines are reversed in places.**
> `pow-r2-upload.timer` is **enabled and hourly** (this file says disabled);
> `derived_signal` **does** rebuild hourly (this says manual); `pow-venue-l2`
> / `pow-venue-ws` are **not installed** (this says verified); the
> `pow-opportunity`/`pow-miner-cards`/`pow-daily-brief`/`pow-provenance`
> timers are **not armed**; `/home/box/powpowpow/.venv` and `r2.env` are
> **not present** despite the ✓; "no off-box exposure" is false
> (`pow.systems` is public); disk/warehouse numbers are from 09-23.
> §4 code inventory and the "still accurate" notes remain valid.

# PowPowPow Audit — full inventory 2026-09-23

> Method: live inspection (systemd, warehouse, API responses, import graph,
> test run). Nothing below is assumed. Stale items are annotated with the
> exact reason, never deleted. See `threads.md` for what to do next and
> `agents.md` for operating rules.

## 1. Live systems

### Collectors (systemd, all `active (running)`, verified)

| Service | What | Cadence | Evidence |
|---|---|---|---|
| pow-venue-l2 | REST L2 CoinEx+Gate+MEXC, 21 markets incl BTC | 60s daemon | heartbeat fresh, 19→21 markets |
| pow-venue-ws | WS tick archive CoinEx+Gate | daemon | running |
| pow-chain-state | QUBIC/XMR/KAS/AKT/NOCK/BTC poller | 300s daemon | heartbeat `[PASS]`, btc: 5 |
| pow-safetrade-l2 | SafeTrade WS depth+trades, 27 markets | daemon | 55 streams, btcusdt tracked |
| pow-site | Dashboard+API :8795, token-gated | daemon | 22 routes 200 |

### Timers (all enabled, verified)

| Timer | Schedule | Status |
|---|---|---|
| pow-qubic-epoch | every 10min | firing |
| pow-qubic-computors | hourly | firing |
| pow-daily-state | 00:30 UTC | armed |
| pow-opportunity | 01:00 UTC | armed (first run done manually) |
| pow-miner-cards | 01:30 UTC | armed (first run done manually) |
| pow-daily-brief | 02:00 UTC | armed (first brief served) |
| pow-provenance | 02:30 UTC | armed (manifest+universe 09-23 done) |
| pow-r2-upload.timer | daily | **DISABLED — never enabled after secrets moved to env file** |

### Pipeline (verified end-to-end today)

```
APIs → core.fetch_json (raw archive) → collectors → warehouse/normalized
→ build_daily_state (42 market-states) → signals (12+21+11) → factors (34 symbols)
→ analytics (XMR/QUBIC/BTC) → site+MCP+R2
```

## 2. Data inventory (all tables 2026-09-23 only)

19 normalized tables live. STATE depth = **1 day** (backtest refuses until 2+).

| Table | Rows (approx) | Source | Gaps |
|---|---|---|---|
| price_history | XMR/QUBIC/BTC 366d | CoinGecko backfill | PRL/KAS/etc parked (rate limits) |
| chain_snapshot | BTC 6153 (355d backfill) + polls | blockchain.info charts + polls | XMR thin (hours) |
| fee_market | XMR 16/d, BTC 1+/d | xmrchain, Blockstream | — |
| mempool_snapshot | XMR 16/d, BTC live | xmrchain, Blockstream | — |
| pool_snapshot | XMR live (fixed today), BTC 5d | p2pool-observer, blockchain.info pools | was 0 rows (Cloudflare UA) |
| orderbook_snapshot/trade/ticker | today only | venue+safetrade daemons | no history (ephemeral by design) |
| daily_state | 42 market-states | builder | 1 day only |
| derived_signal | miner/flow/required | signals.py (manual!) | **no timer — rebuilds manually** |
| opportunity_snapshot | 6 archetypes | snapshot_opportunity (timer) | — |
| miner_card | 10 rows | snapshot_cards (timer as of today) | was 0 rows (mapping bug) |
| btc_history fields | inside chain_snapshot | 10-chart backfill, 4725 rows | — |
| qubic_epoch/computor/network_demand/external_mining | live | epoch engine + computors | — |
| proof_rate, gap_event, universe_event | live | collectors | — |

Derived artifacts: `warehouse/{xmr,qubic}_analytics.json`, `btc_context.json` (all rebuilt manually — **no timers**), `chains/network_state.json` (live), `chains/factors/cross_chain_factors.json` (rebuilt manually — **no timer**), `briefs/2026-09-23.md` (first), manifests+universe 09-23 (first since 09-19).

## 3. API + MCP surface

22 REST routes, all 200 (verified). 13 MCP tools via `opencode.json` stdio (verified listing).

Dead paths (code present, always fails):
- `/api/chat` → Pi harness at `/home/ubuntu/qpbot`, which **does not exist on this box**. Always falls back to data-only answers. # STALE PATH: predates the VPS move; either vendor the harness or delete the branch and document data-only chat.
- `/api/page` → `pages/` directory **does not exist** (`compile_coins.py` never run). Always 404. # STALE: seed content never generated.
- `/api/brief` → was empty until today; now serves 09-23 (timer armed going forward).

## 4. Code inventory

### Live (imported by running code)
- `core.py` (+ `core/__init__.py` re-export — see gotcha below)
- `collectors/{chain_state,venue_l2,venue_ws,l2_archival}.py`
- `v1_live_cards.py` (cards, opportunity, homelab, MCP, site)
- `homelab.py`, `scripts/{snapshot_opportunity,homelab,build_daily_state,snapshot_cards,powdaily,xmr_analytics,qubic_analytics,btc_context,load_cg_history,load_btc_history,qubic_epoch,qubic_computors,r2_upload}.py`
- `site/server.py`, `mcp_server.py`, `manifest.py`, `universe.py`, `factors.py`, `signals.py`, `emission.py` (via signals)

### Manual-only scripts (work, but no timer — freshness decays until run)
- `signals.py`, `factors.py`, `btc_context.py`, `xmr_analytics.py`, `qubic_analytics.py`, `load_cg_history.py`, `load_btc_history.py`, `collect_releases.py`, `compile_coins.py`, `backtest.py`, `compact_stream.py`, `trim_jsonl.py`, `tardis_drip.py`, `backfill_trades.py`, `collect_chain_stats.py`, `collect_github.py`, `collect_miner_revenue.py`, `collect_mining.py`, `dedupe_seed.py`, `seed_rebuild.py`, `download_*` (safetrade repo, different tree)
- # NOTE: the nightly chain covers STATE→opportunity→cards→brief→provenance. Signals/factors/analytics/btc_context are rebuilt by hand after. Next automation gap (see threads.md P0).

### Orphaned root modules (nothing imports them — do NOT delete, reasons noted)
- `api.py` — # STALE: pre-site REST attempt; superseded by `site/server.py` (22 routes vs api.py's handful). Keep as reference for endpoint ideas.
- `daemon.py` — # STALE AMBITION: "full-plant daemon" per TODO §2; superseded by per-collector systemd units which work. Keep until TODO §2 is rewritten.
- `live_cards.py` — # STALE: predecessor of `v1_live_cards.py`. Keep for diff history.
- `v1_pipeline.py`, `warehouse.py` — # COMPAT SHIMS per HANDOVER; `warehouse.py` still imported by normalize/moat/nock_collector. Keep.
- `registry.py` — # SUPERSEDED by `v1_registry.py` as runtime truth; still the documented "candidate pool". Keep.
- `content_system.py` — # PARKED: content loop not started (needs 30d history). Keep; it is the spec when Phase content begins.
- `backtest.py` — CLI entry point (fine unimported); honestly refuses until 2+ STATE days. Keep.
- `ofi.py`, `pressure.py`, `two_timescale.py` — # STALE INPUTS per TODO §3: run on stale file inputs, need rewire to STATE tables. Keep; rewire is threads.md P2.

### Parked research trees (zero live references — do NOT delete)
- `experiments/legacy/` — # PARKED: early dataset/pressure experiments. Keep for methodology archaeology.
- `seesaw_backtests/` (base + a..k) — # PARKED: backtest harness predating warehouse STATE. Keep; design feeds the future Seesaw panel.
- `moat/{alph,erg,kas,qrl,tao,zeph,benchmarks.py,qubic_archival.py}` — # PARKED: per-coin moat notes. Keep; qubic_archival may revive for historical computors.
- `datagarden/` — # SEPARATE PROJECT: shared garden primitives + ideology docs. Zero imports from powpowpow. Keep; do not merge without a plan (see threads.md).
- `core/{panel,primitives,warehouse_core,backtest_harness,btc_baseline}.py` — # SCAFFOLD: imported only via package init or not at all. `btc_baseline` unrealized until panel exists. Keep.

### Parked collectors (~20 one-shots — do NOT wire without a named transformation)
`akt, clore, flux, gnk, kas, nock, nos, pha, prl, qrl, quan, qubic, tao, theta, tig, tsc, la, mcm, external, compute_benchmark, coinex, gate, xmr_collector` — # PARKED per BLOCKERS.md #5: superseded (coinex/gate/xmr/qubic/prl) or no reachable endpoint / no venue-of-truth. XMR+QUBIC+BTC focus holds.

### Gotchas file (read before touching imports)
- `core/` package shadows `core.py`: `core/__init__.py` re-exports via importlib. It works — do not "simplify" without testing every importer.
- Cloudflare UA matrix (verified): SafeTrade needs browser UA; p2pool.observer needs short `Mozilla/5.0`; mempool.space is connection-blocked — use Blockstream. See `core.fetch_json(user_agent=...)`.
- blockchain.info `total_fees_btc` returns negatives; `miners_revenue_usd` returns 0.0 — both dropped as untrustworthy, documented in code.
- BTC hashrate unit from stats endpoint is ASSUMED GH/s from scale — labeled UNCONFIRMED.
- Shell `&` in curl URLs backgrounds the call — quote URLs with query strings.

## 5. Docs inventory

| Doc | Status | Note |
|---|---|---|
| HANDOVER.md | LIVE (today) | ops truth; fixed tunnel claim, paths, token location |
| TODO.md | LIVE (today) | progress log; §2/§3 partially stale (daemon.py, OFI rewire still open) |
| BLOCKERS.md | LIVE (today) | 10 blockers + fix log |
| VISION.md | LIVE (today) | canonical thesis; Layer 2 at prediction-log stage |
| devplanresponse.md | LIVE (today) | 18-thread audit; gaps list aging — refresh after Seesaw panel lands |
| README.md | LIVE (today) | +R2 line; still claims venv path? verified `/home/box/powpowpow/.venv` |
| DOCS.md | LIVE (today) | principles incl. no-opinions rule the code violated (now fixed) |
| agents.md | LIVE-ish (09-21) | Cloudflare creds + **needs PowPowPow section (threads.md task)** |
| failures.md | LIVE (09-21) | probe-backed failure log; SafeTrade entry outdated (says geo-block — actually bot-detection, fixed) |
| transforms.md | AGING (09-21) | formula registry; BTC rows + v2 signals not reflected — refresh needed |
| unsure.md | REFERENCE | mostly resolved; Q11/Q12 still open (powdaily timer fixed since; API exposure = tunnel blocker) |
| devplancurrent.md | LIVE | garden thesis, still accurate |
| devmap.md | LIVE | engineering order; steps 3-5 not started — next after timers |
| content.md | PARKED | spec for content phase (needs 30d history) |
| products.md | LIVE | 7-product sequence; product 1 read-only half now exists (homelab recommend) |
| todo.md (20 foundations) | LIVE | #13/#14 DONE (opportunity snapshots); #4/#5 DONE (manifests/universe timers); rest open |
| backfill.md | REFERENCE | ephemeral-vs-backfillable doctrine, still accurate |
| canonical.md, 04_canonical_universe_v1.md | SUPERSEDED by v1_registry.py | keep for history |
| tier2.md, 07_coin_categories.md | REFERENCE | editorial categories, still valid |
| 01/02/03/05/06 docs | REFERENCE | design research, still valid |
| pr1.md, pr2.md | HISTORICAL | Sep 18 hardening PRs, both landed |
| API_DOCUMENTATION.md | **STALE** | documents api.powpowpow.dev/v1 which does not exist; real API is localhost:8795 (see HANDOVER). Keep for endpoint ideas only. |
| QUICKSTART.md | **STALE PATHS** | `/home/ubuntu/...` paths wrong on this box (`/home/box/powpowpow/.venv`); systemd commands still valid. Fix paths, keep. |
| datacollection.md | REFERENCE | durable-benchmark guidance, still valid |

## 6. Tests

`pytest tests/`: 13 passed, 1 failed — `test_garden.py::test_lineage_resolves`, verified pre-existing (fails on HEAD too, unrelated to recent work). `tests/test_homelab.py`: 6/6. pytest lives at system `/usr/local/bin/pytest`, NOT in `.venv` (venv lacks pytest — install or document).

## 7. Secrets / config hygiene (verified)

- Site token: `~/.config/powpowpow/site.env` (600) ✓
- R2 creds: `~/.config/powpowpow/r2.env` (600), unit file clean ✓
- Cloudflare tokens: `/home/box/Documents/safe/cloudflare3` (per agents.md) ✓
- Git remote embeds token (pre-existing; user-supplied) — rotate if shared.
- `chains/network_state.json`, `cross_chain_factors.json`, `*_analytics.json`, manifests, universe snapshots are COMMITTED runtime state (deliberate: public checkpoints + reviewable state).

## 8. Top risks

1. **1-day STATE depth.** Everything empirical (backtest, signals v1→v2 validation, causal tests) waits on time. Nothing to do but keep collectors alive.
2. **Manual rebuilds.** signals/factors/analytics/btc_context have no timers — served data goes stale between hand runs. threads.md P0.
3. **No off-box exposure.** Tunnel missing; powops can't reach dashboard/API. User-side DNS.
4. **Disk 134GB used.** Warehouse is 275MB — bloat is elsewhere on the box, not POW. R2 covers warehouse regardless.
5. **Single-vendor egress.** mempool.space, Coinbase, Binance blocked; SafeTrade/p2pool needed UA workarounds. Every new source needs a probe first (failures.md pattern).
