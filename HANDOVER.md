# PowPowPow Handover

Live, continuously-collecting compute economics garden. Every derived number links to immutable raw bytes.

## Live services

- pow-venue-l2: REST polls 19 markets CoinEx+Gate+MEXC every 60s
- pow-venue-ws: WebSocket tick archive for same venues
- pow-safetrade-l2: SafeTrade WS depth+trades (25 streams, all tracked markets)
- pow-chain-state: QUBIC RPC + XMR localmonero + KAS + Nockscan every 5min
- pow-qubic-epoch: epoch engine every 10min (burn schedule, net emission)
- pow-qubic-computors: computor set + Doge tasks every hour
- pow-daily-state: STATE rollup + Parquet compact + trim at 00:30 UTC
- pow-site: consumer site on :8795 (token-gated, loopback)
- pow-tunnel: Cloudflare pow.moltwork.com to :8795
- pow-pearld: pearld syncing (paused during disk triage, resumable)

## Site

pow.moltwork.com, token-gated. Black/white/grey only, chunky borders, monospace numbers, no opinions. Style guide in site/STYLE.md. Left rail for HOME + coins + CHAT. Each coin: subtabs Overview/Epoch/Mining/Flow/Signals. Chat through Pi harness with garden context. Bottom panel auto-refreshes ops every 60s.

## Quick commands

Check collectors: systemctl --user status pow-venue-l2 pow-chain-state pow-safetrade-l2
View logs: journalctl --user -u pow-chain-state -n 20
View SafeTrade logs: journalctl --user -u pow-safetrade-l2 -n 20
Run tests: /home/ubuntu/.venvs/powpowpow/bin/python -m pytest tests/ -q
Rebuild state: /home/ubuntu/.venvs/powpowpow/bin/python scripts/build_daily_state.py --date 2026-09-19
Compact parquet: /home/ubuntu/.venvs/powpowpow/bin/python scripts/compact_stream.py --all-seeds
Refresh QUBIC analytics: /home/ubuntu/.venvs/powpowpow/bin/python scripts/qubic_analytics.py
Site token: grep POW_SITE_TOKEN /home/ubuntu/.config/systemd/user/pow-site.service

## File structure (what matters)

- core.py: THE transport layer (auto-archiving fetch_json, store_normalized, FetchResult lineage)
- warehouse.py / v1_pipeline.py: compat shims over core
- v1_registry.py: RUNTIME TRUTH (8 systems)
- registry.py: candidate pool (16+ systems, research universe)
- signals.py: miner_pressure_v1, flow_pressure_v1, required_flow_v1
- emission.py: researched emission schedules (CLORE/FLUX/NOS/TAO/NOCK)
- backtest.py: fundamentals backtest on 365d price + emission

Collectors:
- venue_l2.py: REST L2 CoinEx+Gate+MEXC discovery gap-safe
- venue_ws.py: WebSocket tick archive CoinEx+Gate
- chain_state.py: QUBIC/XMR/KAS/AKT/Nockscan poller
- l2_archival.py: SafeTrade STAGED geo-blocked
- prl_collector.py: PRL PearlTrack derived labels
- qubic_collector.py: QUBIC RPC tick+status
- xmr_collector.py: XMR localmonero+CoinGecko

Scripts:
- qubic_epoch.py: burn schedule net emission
- qubic_computors.py: computor set + Doge mining
- qubic_analytics.py: supply curve returns valuation
- xmr_analytics.py: emission value miner benchmarks
- build_daily_state.py: daily STATE rollup
- snapshot_cards.py: nightly margin snapshots
- compact_stream.py: Parquet compactor 25-30x
- trim_jsonl.py: 7-day hot window
- tardis_drip.py: monthly free-tier Tardis
- load_cg_history.py: CoinGecko 365d price
- collect_releases.py: GitHub releases + commits
- powdaily.py: daily brief generator

Warehouse (NOT in git): raw/venue/, normalized/, parquet/, analytics JSONs

## Key invariants

1. Raw archive is lossless: every API response before parsing, exact bytes preserved (zlib past 256KB), hash round-trip
2. Lineage resolves: every normalized row has raw_event_id back to source observation
3. UTC-only: all timestamps with timezone.utc, no local time
4. Source roles enforced: canonical vs enrichment never confused
5. Missing data stays missing: no default assumptions becoming measured facts
6. Observations vs opinions: signals carry hypotheses, versions, evidence IDs

## What is blocked (needs action)

- SafeTrade: ~~REST + WS return HTTP 403 (geo-block from this VPS).~~ **FIXED 2026-09-23.** Issue was (1) `PowPowPow/1.0` User-Agent triggering Cloudflare bot detection — fixed to browser UA in core.py, (2) missing `ssl=ssl_ctx` in websockets.connect, (3) `core/` package shadowing `core.py` causing silent import fallback to None. Collector running as `pow-safetrade-l2` systemd service.
- pearld: full node resyncing, paused during disk triage. Data extractable once synced. Needed for PRL miner graph.
- KAS emission: supply-delta measurement running but units unconfirmed on hashrate endpoint
- AKT/NOS/CLORE rental demand: endpoints unreachable from this box (DNS/SSL failures)
- Tardis full history: $249/mo for Gate.io QUBIC L2 history. Free tier has monthly snapshots only.

## Design research files

- 01_architecture_and_vision.md: system architecture
- 02_pressure_equation_research.md: academic references + formulas
- 03_seesaw_filter.md: inclusion criteria
- 06_moat_strategy.md: moat theory (historical causal record)
- transforms.md: formula registry live vs queued with blockers
- failures.md: every thing tried, what broke, what unblocks
- devplancurrent.md: full garden thesis
- TODO.md: current work list with progress notes
