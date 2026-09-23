# Blockers — what's not wired up and why

> Updated 2026-09-23 16:20 +07. Everything below is a known issue with a clear path.
> Focus is XMR + QUBIC only. Everything else is parked, not deleted.

## FIXED today

- `core/` shadowing `core.py` → `core/__init__.py` re-exports. All imports work.
- SafeTrade was Cloudflare bot-detection (not geo-block). Browser UA + `ssl=ssl_ctx` fixed. `pow-safetrade-l2` running, 25 streams.
- `pow-site` now systemd-managed with stable token (`~/.config/powpowpow/site.env`). Was manual with random token.
- R2 secrets moved out of unit file into `~/.config/powpowpow/r2.env` (600).
- `pow-mcp.service` disabled — MCP is stdio via `opencode.json`, not a daemon. Running it under systemd was wrong (exit 0 loop).
- Factors rebuilt (24 symbols, fresh 2026-09-23). Was stale 2026-09-21.
- XMR + QUBIC price history loaded (366 closes each). Analytics refreshed.
- Frontend: live ticker (`/api/live` every 5s), XMR Mining tab (security spend, $/MH/day hashprice, hardware table with per-model costs).

## 1. Dashboard not publicly exposed — tunnel missing

**What:** Site listens on 127.0.0.1:8795. `~/.cloudflared/config.yml` only routes `agentcom.org` → :8793. No `pow.moltwork.com` ingress, no cloudflared process running.

**Why:** HANDOVER claims pow.moltwork.com is live, but the tunnel was never configured on this box.

**Unblocks:** powops / anyone off-box querying the dashboard + API.

**Fix:** Add ingress `- hostname: pow.moltwork.com, service: http://127.0.0.1:8795`, create `cloudflared` systemd unit, verify DNS routes to this tunnel. Needs Cloudflare dashboard check (outside this box).

## 2. Price history: only XMR + QUBIC — PRL/KAS/etc parked

**What:** `price_history` has XMR + QUBIC (366d). No PRL, KAS, NOCK, XEL, XTM.

**Why:** User focus is XMR + QUBIC. CoinGecko rate limits make bulk backfill slow.

**Unblocks:** Full 8-coin signals, cross-asset burden z-scores.

**Fix:** Run `load_cg_history.py --coins PRL,KAS,...` when expanding beyond XMR/QUBIC. Opportunity cost: skip for now.

## 3. Chain snapshots thin — needs time

**What:** `chain_snapshot` has hours of XMR/QUBIC/KAS/AKT/NOCK, not days.

**Why:** `pow-chain-state` restarted today. Difficulty-price correlation needs multi-day history.

**Fix:** Time. Collector running every 5min.

## 4. Signals partial — needs more STATE days

**What:** flow_pressure + required_flow live (10 signals). miner_pressure refuses on thin cross-section.

**Why:** Only 1 day of STATE. Burden z-scores need 4+ markets with emission + depth.

**Fix:** Time. Daily STATE at 00:30 UTC. After 3–4 days all signals activate.

## 5. One-shot collectors parked (not wired, by design)

**Status:** `akt, clore, flux, gnk, kas, nock, nos, pha, prl, qrl, quan, qubic, tao, theta, tig, tsc, la, mcm, external, compute_benchmark, coinex, gate, xmr_collector` are one-shot/legacy.

**Why parked:**
- `chain_state.py` supersedes kas/nock/akt/qubic/xmr chain polling.
- `venue_l2.py` supersedes coinex/gate L2.
- `xmr_collector.py`, `qubic_collector.py`, `prl_collector.py` are Phase-1 one-shots; chain_state + epoch engine replace them.
- TAO/THETA/TIG/PHA/QRL/LA/MCM/FLUX/QUAN/TSC/GNK/NOS/CLORE have no venue-of-truth or no reachable endpoint from here.

**Rule:** Don't wire a collector unless it feeds a named transformation. XMR + QUBIC only until signals have scars.

## 6. pearld sync — paused

**What:** PRL pool→miner→exchange graph needs own pearld node. Paused during disk triage.

**Fix:** Resync (~2h) → extract flows → drop chain bytes. Only when expanding beyond XMR/QUBIC.

## 7. AKT/NOS/CLORE rental demand — endpoints unreachable

**What:** DNS/SSL failures from this VPS.

**Fix:** Proxy or unblocked egress. Parked (not XMR/QUBIC).

## 8. powdaily.py — not automated

**What:** Brief generator exists, no timer, `briefs/` empty. `/api/brief` + MCP `get_brief` return errors.

**Fix:** Add `pow-daily-brief.timer` (after `pow-daily-state`). 15 min work. Queued.

## 9. Local cleanup policy — missing

**What:** R2 upload works (verified 10/10), but nothing deletes local raw after confirmed upload. Warehouse 275MB today; SafeTrade grows it ~1GB/day raw.

**Fix:** Script that lists R2 keys, deletes local raw older than N days only if present remotely. Queued behind powdaily timer.

## 10. Site auth — token only

**What:** Single shared token, no per-user, no rate limit, no audit.

**Why:** MVP. Token now stable + 600-perms env file. Acceptable until off-box exposure (blocker 1) lands.
