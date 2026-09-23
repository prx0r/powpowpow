# PowPowPow Handover

Live, continuously-collecting compute economics garden. Every derived number links to immutable raw bytes.

## Live services

- pow-venue-l2: REST polls 19 markets CoinEx+Gate+MEXC every 60s
- pow-venue-ws: WebSocket tick archive for same venues
- pow-safetrade-l2: SafeTrade WS depth+trades (25 streams, all tracked markets)
- pow-chain-state: QUBIC RPC + XMR localmonero + KAS + Nockscan + BTC (blockchain.info/Blockstream) every 5min
- pow-qubic-epoch: epoch engine every 10min (burn schedule, net emission)
- pow-qubic-computors: computor set + Doge tasks every hour
- pow-daily-state: STATE rollup + Parquet compact + trim at 00:30 UTC
- pow-site: consumer site on :8795 (token-gated, loopback, systemd `pow-site.service`, token in `~/.config/powpowpow/site.env`)
- pow-tunnel: BLOCKED — no cloudflared process running; `~/.cloudflared/config.yml` only routes agentcom.org. pow.moltwork.com not exposed. See BLOCKERS.md #1.
- pow-pearld: pearld syncing (paused during disk triage, resumable)

## Site

Localhost :8795, token-gated (token in `~/.config/powpowpow/site.env`). Public pow.moltwork.com NOT exposed — tunnel missing, see BLOCKERS.md #1. Black/white/grey only, chunky borders, monospace numbers, no opinions. Style guide in site/STYLE.md. Left rail for HOME + BTC + coins + CHAT. Each coin: subtabs Overview/Epoch/Mining/Flow/Signals. BTC tab: Overview (security spend, EH/s, difficulty, height, fees), Epoch (halving countdown + subsidy schedule), Flow (fee market — no venue listing), Mining (security/hashrate/difficulty charts + garden-computed hashprice), Signals (baseline role: XMR/QUBIC hooks). Live ticker polls `/api/live` every 5s. XMR Mining tab shows security spend, $/MH/day hashprice, hardware profitability, security-spend chart. Chat through Pi harness with garden context. Bottom panel auto-refreshes ops every 60s.

## API + MCP (what powops can query)

REST (token-gated): `/api/health /api/live /api/signals /api/factors /api/state /api/state_series /api/history /api/cards /api/cards_history /api/chain /api/analysis /api/analytics /api/xmr_full /api/opportunity /api/btc /api/epoch_series /api/brief /api/page /api/ops`, POST `/api/chat`.
MCP stdio (13 tools, via `opencode.json` → `mcp_server.py`): get_asset_state, get_signals, get_factors, compare_compute_routes, get_miner_pressure, get_brief, get_price_history, get_health, get_live, get_xmr_full, get_opportunity, get_btc_context, recommend_homelab. NOTE: MCP is stdio — do NOT run under systemd (`pow-mcp.service` disabled on purpose).

## Quick commands

Check collectors: systemctl --user status pow-venue-l2 pow-chain-state pow-safetrade-l2 pow-site
View logs: journalctl --user -u pow-chain-state -n 20
View SafeTrade logs: journalctl --user -u pow-safetrade-l2 -n 20
Run tests: /home/box/powpowpow/.venv/bin/python -m pytest tests/ -q
Rebuild state: /home/box/powpowpow/.venv/bin/python scripts/build_daily_state.py --date 2026-09-23
Compact parquet: /home/box/powpowpow/.venv/bin/python scripts/compact_stream.py --all-seeds
Refresh QUBIC analytics: /home/box/powpowpow/.venv/bin/python scripts/qubic_analytics.py
Refresh XMR analytics: /home/box/powpowpow/.venv/bin/python scripts/xmr_analytics.py
Site token: cat ~/.config/powpowpow/site.env
Live API: curl "http://127.0.0.1:8795/api/live?token=$(cat ~/.config/powpowpow/site.token)"
MCP tools: /home/box/powpowpow/.venv/bin/python -c "import sys; sys.path.insert(0,'.'); import mcp_server; print([t.name for t in mcp_server.mcp._tool_manager.list_tools()])"

## File structure (what matters)

- core.py: THE transport layer (auto-archiving fetch_json, store_normalized, FetchResult lineage)
- homelab.py: local hardware adapter — detect (CPU/GPU/RAM/disk with provenance) + match archetypes + recommend from opportunity log. Read-only, stdlib-only.
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
- l2_archival.py: SafeTrade WS depth+trades RUNNING as pow-safetrade-l2 (was STAGED)
- prl_collector.py: PRL PearlTrack derived labels (Phase-1 one-shot, superseded for chain by pearld plan)
- qubic_collector.py: QUBIC RPC tick+status (Phase-1 one-shot, superseded by chain_state + epoch engine)
- xmr_collector.py: XMR localmonero+CoinGecko (one-shot legacy, superseded by chain_state normalized tables)
- remaining collectors/ (akt, clore, flux, gnk, kas, nock, nos, pha, qrl, quan, tao, theta, tig, tsc, la, mcm, external, compute_benchmark, coinex, gate): one-shot/parked — see BLOCKERS.md #5. Focus is XMR+QUBIC.

Scripts:
- qubic_epoch.py: burn schedule net emission
- qubic_computors.py: computor set + Doge mining
- qubic_analytics.py: supply curve returns valuation
- xmr_analytics.py: emission value miner benchmarks
- build_daily_state.py: daily STATE rollup
- snapshot_cards.py: nightly margin snapshots (has market→asset mapping bug — see BLOCKERS)
- snapshot_opportunity.py: daily ranked opportunity set per hardware + prediction hashes (todo #13/#14)
- compact_stream.py: Parquet compactor 25-30x
- trim_jsonl.py: 7-day hot window
- tardis_drip.py: monthly free-tier Tardis
- load_cg_history.py: CoinGecko 365d price (XMR/QUBIC/BTC loaded)
- load_btc_history.py: 1yr BTC chain history via blockchain.info charts (hashrate/difficulty/revenue/fees, no key)
- btc_context.py: M0 baseline — rolling BTC betas, residuals, security spend, content hooks
- collect_releases.py: GitHub releases + commits
- powdaily.py: daily brief generator
- homelab.py: detect this machine + recommend from opportunity set (XMRBot-flow entry, read-only)
- r2_upload.py: Cloudflare R2 off-box backup with AWS SigV4

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
