# Threads — open work, ordered by opportunity cost

> Companion to `audit.md` (the state) and `agents.md` (the rules).
> Updated 2026-09-23. P0 = do next; P3 = do not touch yet.
> Nothing here deletes anything — cleanups are annotations, see §5.

## P0 — freshness automation (data rots without this)

- [ ] **T1. signals + factors timers.** Both rebuilt by hand; site/MCP serve them stale between runs. Add `pow-signals.timer` (~00:40 UTC) + `pow-factors.timer` (~00:50 UTC). 30 min work, removes the largest staleness vector. (audit §4, §8.2)
- [ ] **T2. analytics timers.** `xmr_analytics`, `qubic_analytics`, `btc_context` run by hand. Fold into one `pow-analytics.timer` (~00:55 UTC) or extend the nightly chain. Without it the dashboard's numbers age daily.
- [ ] **T3. Enable pow-r2-upload.timer.** Secrets moved, service verified — but the timer was never enabled. One command; turns the off-box doctrine real.
- [ ] **T4. compact + trim timers.** `pow-daily-state.service` runs ONLY the builder (HANDOVER overclaims compact+trim). Warehouse grows ~1GB/day raw. Wire `compact_stream.py` + `trim_jsonl.py` before disk pressure forces triage again.

## P1 — exposure + completeness

- [ ] **T5. Tunnel (user-side).** Dashboard/API localhost-only; no cloudflared process, no pow.moltwork.com ingress. Needs DNS/dashboard access from outside this box. Highest value IF powops needs remote access; otherwise correctly parked.
- [ ] **T6. `pages/` + compile_coins.** `/api/page` always 404s. Run once, verify, optionally timer. Unlocks the knowledge-compiler outlet (TODO §5).
- [ ] **T7. Chat harness path.** `/api/chat` always falls back (dead `/home/ubuntu/qpbot` path). Either vendor the harness or delete the branch and document data-only chat.
- [ ] **T8. transforms.md refresh.** Formula registry predates BTC rows + v2 direction-strip. Rebuild the live/queued table so it matches code again.

## P2 — research (needs history depth; scaffold now, judge later)

- [ ] **T9. Seesaw panel scaffold** (devmap step 3). Single canonical research table joining price/capacity/economics/liquidity. Thin with 1d STATE — build the shape now, fill with time.
- [ ] **T10. M0-vs-M1 test** (devmap step 4, todo #20). BTC betas exist (`btc_context.py`); wire into factors and run the first incremental-value regression. First empirical claim the garden can make.
- [ ] **T11. Backtest unlock watch.** Refuses until 2+ STATE days (~Sep 25 minimum, meaningful ~mid-Oct). No action — calendar item. Combined XMR/QUBIC/BTC once depth exists.
- [ ] **T12. OFI/two_timescale rewire** (TODO §3). Stale file inputs → STATE tables. Queued behind panel (needs the same shape).
- [ ] **T13. Hardware benchmarks measured** (todo #16). Registry still theoretical 09-18 seeds. First real measurement should come from a homelab box running the recommend loop, not a scraper.
- [ ] **T14. BTC pool distribution depth.** Have 5d top3/HHI; miningpoolstats.io probe for per-pool history. Cheap probe, do when touching pools.
- [ ] **T15. QUBIC static labels + live burn.** One probe (was 403) + archiver endpoints. Queued behind M0 work.

## P3 — parked by doctrine (do not start)

- Executor / bounded grants / XMR treasury / fleet / MPC (needs signal scars + outcome data).
- New collectors beyond XMR/QUBIC/BTC (needs a named transformation).
- ASIC registry entries (documented decision, BLOCKERS.md).
- Content videos (needs 30d history; commentary without data violates the canon).
- Stocks integration (context, not moat — devmap is explicit).
- `datagarden/` merge (separate project; needs its own plan).

## Blockers (external — need user or network, not code)

- [ ] **B1. DNS/tunnel** for pow.moltwork.com (see T5).
- [ ] **B2. pearld disk.** PRL chain-side needs sync-extract-drop; box at 134GB used (warehouse only 275MB — bloat is elsewhere, but triage risk stands).
- [ ] **B3. Egress blocks.** mempool.space, Coinbase, Binance fail from here; SafeTrade/p2pool needed UA workarounds. Probe-first rule for every new source (failures.md pattern).
- [ ] **B4. CoinGecko rate limits.** PRL/KAS/etc closes parked; backfill slowly or pay.
- [ ] **B5. Git remote embeds token.** Pre-existing; rotate if the URL is ever shared.

## Cleanups (annotate, never delete)

- [ ] **C1. `api.py`** — # STALE, superseded by site/server.py. Keep for endpoint ideas.
- [ ] **C2. `daemon.py`** — # STALE AMBITION until TODO §2 rewritten for per-collector units.
- [ ] **C3. `live_cards.py`** — # STALE predecessor of v1_live_cards.py. Keep for diff.
- [ ] **C4. `registry.py`** — # SUPERSEDED by v1_registry.py; documented candidate pool.
- [ ] **C5. `content_system.py`** — # PARKED until content phase.
- [ ] **C6. `API_DOCUMENTATION.md`** — # STALE (api.powpowpow.dev doesn't exist). Harvest endpoint ideas, then mark superseded-by-HANDOVER at top.
- [ ] **C7. `QUICKSTART.md`** — # STALE PATHS (`/home/ubuntu`). Fix 3 paths, keep.
- [ ] **C8. `failures.md` SafeTrade entry** — says geo-block; actually bot-detection, fixed. Amend the entry, keep the probe log.
- [ ] **C9. `v1_pipeline.py`** — # COMPAT SHIM, zero importers. Keep per HANDOVER.
- [ ] **C10. `experiments/legacy, seesaw_backtests, moat/*`** — # PARKED research. Keep; index from here, not code.
- [ ] **C11. pytest in `.venv`** — system pytest works, but README implies venv. `pip install pytest` in venv or fix README. 2 min.
- [ ] **C12. `test_garden.py::test_lineage_resolves`** — fails on HEAD (pre-existing). Fix or mark xfail with reason; red suites hide new red.
