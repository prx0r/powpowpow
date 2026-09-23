# Blockers — what's not wired up and why

> Updated 2026-09-23. Everything below is a known issue with a clear path.

## 1. `core/` package shadows `core.py` — FIXED

**Was:** `core/__init__.py` didn't re-export from `core.py`, so `from core import utcnow` silently fell back to `None` in every collector.

**Fix:** `core/__init__.py` now loads `core.py` via importlib and merges exports. All imports work.

**Status:** Fixed. All collectors, scripts, and site server import correctly.

## 2. Price history not collected — BLOCKED on CoinGecko

**What:** `price_history` table is empty. No 365d closes for any coin.

**Why:** `scripts/load_cg_history.py` needs to run but CoinGecko free tier has rate limits. Need to run once with backoff.

**Unblocks:** XMR 365d price position, emission valuation, analytics completeness.

**Fix:** Run `python3 scripts/load_cg_history.py --coins XMR,QUBIC,PRL` with retry logic.

## 3. Chain snapshots thin — collector just started

**What:** `chain_snapshot` table has limited XMR data (hashrate, difficulty, p2pool).

**Why:** `pow-chain-state` was just restarted. Needs 24h+ to build meaningful history.

**Unblocks:** Difficulty-price correlation, hashrate trends, p2pool metrics.

**Fix:** Time. Collector is running.

## 4. Derived signals thin — needs more daily_state history

**What:** Only 7 flow_pressure signals, no miner_pressure or required_flow.

**Why:** `miner_pressure` needs 4+ markets with emission data. `required_flow` needs emission + flow. Only 1 day of STATE exists.

**Unblocks:** Full signal board, cross-asset comparisons.

**Fix:** Time. Daily STATE builds at 00:30 UTC. After 3-4 days, all signals activate.

## 5. QUBIC epoch/computors — service created, timer armed

**What:** `pow-qubic-epoch` and `pow-qubic-computors` timers created.

**Status:** First run pending (next :10 and :00). Will populate QUBIC epoch data.

## 6. SafeTrade l2 archival — geo-blocked from this VPS

**What:** `collectors/l2_archival.py` ready but SafeTrade REST+WS return 403 from this box.

**Why:** IP-level geo-block (Canada). Code is complete and replay-verified.

**Unblocks:** SafeTrade L2 depth+trades for PRL, QUBIC, XMR on venue-of-truth.

**Fix:** Run from unblocked machine + rsync warehouse back, or proxy.

## 7. pearld sync — paused during disk triage

**What:** PRL chain data not available. Pearld full node resyncing.

**Why:** Disk space management. Data extractable once synced.

**Unblocks:** PRL pool→miner→exchange flow graph.

## 8. AKT/NOS/CLORE rental demand — endpoints unreachable

**What:** No rental market data for compute marketplace coins.

**Why:** DNS/SSL failures from this VPS.

**Unblocks:** Rental demand half of compute efficiency metrics.

## 9. MCP server — verified but not deployed

**What:** `mcp_server.py` has 6 tools, verified end-to-end.

**Why:** Not wired to systemd. No agent querying it yet.

**Unblocks:** Any Claude/ChatGPT/Goose agent can reason over garden data.

## 10. Site auth — token only, no per-user

**What:** Token-gated, no rate limiting, no audit.

**Why:** MVP. Acceptable for now.

## 11. powdaily.py — not automated

**What:** Daily brief generator exists but no cron/timer.

**Why:** Not wired yet.

**Fix:** Add timer similar to pow-daily-state.
