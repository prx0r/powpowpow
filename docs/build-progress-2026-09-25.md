# Build progress — session of 2026-09-25

Range: `d09cc12` → `HEAD`. Commits landed this session:

| Commit | What |
|---|---|
| `ff3d952` | Verified R2 sync, safe mining collectors, public dashboard |
| `f8d94f2` | Live home dashboard + hourly STATE/signals chain |
| `ce13ee8` | Refresh analytics after a handover snapshot reset freshness |
| `f2a98d4` | Recoverability tagging, layer manifests, ticker trim, MCP outlet |

(Interleaved with four pushes from a second box: `5444798`, `34e28bc`,
`4623274`, `6890454` — see *Open threads* §1.)

## What is working now

### Public dashboard

`https://pow.systems/` → Cloudflare Tunnel → `127.0.0.1:8795` → `pow-site.service`.

- GETs are public (verified `/`, `/api/health`, `/api/ticks`, `/api/home` → 200
  with no token). Only `POST /api/chat` is token-gated; token lives in
  `~/.config/powpowpow/site.env` (mode 600), rotated this session after a
  leak, never committed.
- Home tab rebuilt from a single `GET /api/home`: 3 network cards, collection
  strip, 16-row market table, signals table. Refreshes every 60s.
- Repo rule respected: signals render as numeric z-scores and evidence
  sources only — no directional language in the UI.

### Mining data is actually being collected

| Metric | Value |
|---|---|
| Chain poll cadence | 300s, `--only qubic,xmr,btc` |
| QUBIC epoch engine | every 10m |
| QUBIC computors + DOGE leg | hourly |
| Daily STATE + signals + factors | hourly at :25 |
| Analytics refresh | every 6h |
| Health check | every 5m |
| Warehouse | 403 MB, 48k raw files, 74,584 normalized rows |

Signals now produce **22/day** (`miner_pressure` 11, `flow_pressure` 6,
`required_flow` 5) — they were **0** before this session because the STATE
chain was never wired and `load_emission()` looked up `XMRUSDT` against
network_state keyed `XMR`.

### Data organisation — moat vs re-fetchable

`core.classify_recoverability()` now stamps every raw envelope and normalized
row. `manifest.py` had a hardcoded `/home/box/...` path, so layer breakdown
was always `unknown`; rewritten to classify from content:

| Layer | Before | After |
|---|---:|---:|
| `unknown` | 744,429 files / 5.6 GB | **0** |
| `ephemeral_archive` | 0 | 50,155 files / 228.9 MB |
| `canonical_backfill` | 0 | 256 files / 13.2 MB |
| `derived` | 0 | 2 files / 44 KB |

Ticker rows went from **29,338 bytes** (whole-market bundle, no `symbol`,
read by nobody) to **644–688 bytes** per tracked market — ~98% smaller, and
`build_daily_state` now fills `last_price`/`day_volume` for SafeTrade, which
was previously always empty.

Policy: `docs/data-moat-policy.md`.

### Backup

- `pow-r2-upload` completed a full backfill: **24,460 files, 21,956 uploaded,
  2,504 verified, 0 failed**; `chains/` 29 → 2 uploaded / 27 skipped.
- Local deletion only after a fresh remote `HEAD` confirms size + SHA-256:
  `raw` 24h, `normalized` 30h, `parquet` 168h, `chains/` never.
- Collectors pause below `POW_MIN_FREE_BYTES` (2 GiB).

### Agent outlet

`mcp_server.py` was dead (config pointed at `/home/box/.../.venv/python`, and
installed `mcp` 2.1.1 has no `mcp.server.fastmcp`). Fixed: imports `fastmcp`
3.4.7, config now `/usr/bin/python3 /root/powpowpow/mcp_server.py`.
**13 tools verified calling real warehouse data.**

### Verification receipts

| Check | Result |
|---|---|
| `pytest tests/ -q` | **48 passed, 1 failed** (pre-existing `test_lineage_resolves`) |
| `ruff check` on new files | clean |
| `scripts/health_check.py` | `{"ok": true, "failures": []}` |
| `python3 manifest.py` | 7.5s, `unknown` absent |
| Live `pow.systems` | `/` 200, `/api/home` 200, health true |
| Services running | site, chain-state, safetrade-l2, cloudflared |

---

## Open threads

### 1. Two boxes, one branch — race
**Evidence:** four remote commits arrived mid-session (`5444798`, `34e28bc`,
`4623274`, `6890454`); each required a rebase, and `6890454` overwrote
`warehouse/*_analytics.json` with a 22-hour-old snapshot, which flipped the
health check to false until I regenerated them.
**First action:** pick one canonical box, or give each its own branch and a
single integration branch. Tracked regenerated artifacts
(`warehouse/*_analytics.json`, `chains/network_state.json`) are the collision
surface — consider gitignoring them since they are R2-backed.

### 2. R2 job is slower than its timer
**Evidence:** the cold backfill ran **1h27m** (`Consumed 4min19s CPU`); the
timer is hourly with `Persistent=true`, so a missed firing replays
immediately (saw `16:05:19` start right after a `16:05:19` finish). Once the
state file existed the next run was still ~20 min of statting 24k files.
**First action:** measure a warm run; if >60 min, drop cadence to 3h or make
`R2Sync.run` emit state incrementally instead of at the end.

### 3. Single-venue signals
**Evidence:** `venue_l2`/`venue_ws` (CoinEx/Gate/MEXC) are not installed;
only SafeTrade L2 runs. `signals.py` cross-section therefore comes from one
book, and `assumptions` in every signal says so.
**First action:** decide whether cross-venue depth is worth starting the
parked collectors (`BLOCKERS §5` says only wire what feeds a named
transformation — the named transform here is `burden_vs_book`).

### 4. One day of history
**Evidence:** `daily_state` has 1 date; `backtest.py` "honestly refuses until
2+ days"; `chain_snapshot` has hours, not days.
**First action:** wait 3 days, then re-run `btc_mining_backtest.py` and
re-check whether signals stabilize (they need a cross-section ≥4, which now
passes).

### 5. Reconstructable data is tagged but not pruned
**Evidence:** `canonical_backfill` = 256 files / 13.2 MB tagged
`reconstructable`, but no prune step acts on the tag; R2 keeps it forever.
**First action:** add a prune that removes reconstructable raw older than N
days **only when** the source still answers a HEAD/GET, or set an R2
lifecycle rule on the `powpowpow/raw/` prefix.

### 6. No provenance timer
**Evidence:** `manifest.py` docstring says "at the end of each day" but no
`pow-provenance` unit exists; the four manifests on disk exist only because
someone ran it by hand. It also hashes every raw file (7.5s today, will grow).
**First action:** add `pow-provenance.timer` (daily) and move hashing off the
critical path (hash closed dates only).

### 7. `test_lineage_resolves` fails on HEAD
**Evidence:** `tests/test_garden.py:83` asserts rows exist after
`store_normalized` into an `isolated` tmp dir, but returns `[]` — the
`core/` package shadows `core.py`, so `store_normalized.__globals__`
points at a different `BASE_DIR`. Same class of bug as the one I worked
around in `tests/test_home.py` with `monkeypatch.setitem(__globals__)`.
**First action:** patch `core.store_normalized.__globals__["BASE_DIR"]` in the
fixture instead of `core.BASE_DIR`.

### 8. Disk headroom
**Evidence:** `df`: 68G/75G used, ~3.8 GB free (95%). Warehouse 403 MB but
raw grows ~1.3 GB/day; 24h retention only prunes **after** R2 verifies.
**First action:** watch `pow-health.service`; if free < 2 GiB the collectors
pause by design, but consider lowering `raw` retention to 12h while disk is
this tight.

### 9. Point-in-time labels half-built
**Evidence:** `backfill.md:123-131` requires `known_at`/`superseded_at`;
`entities.py` writes `valid_from` only. `valid_to` is defined but never
assigned, so "what did we know when" cannot be reconstructed — the
structural moat layer in `06_moat_strategy.md:453-481` is unimplemented.
**First action:** add `known_at` to entity writes, then a supersede path.

### 10. ~71 hardcoded `/home/box` paths remain
**Evidence:** 81 occurrences in 36 tracked files; **26 are executable code**.
Only the live one is fixed this session (`core/warehouse_core.py` created
12 dirs under `/home/box` on *every* `import core`). The rest write outside
the repo only when called (`moat/*`, `universe.py`, `entities.py`,
`seesaw_backtests/*`, `scripts/seed_rebuild.py`).
**First action:** fix `scripts/seed_rebuild.py:32` (`VENV_PY`) and
`moat/*` module-level `os.makedirs` next time those are revived; the
remainder are parked.

---

## Repo organisation done this session

- **Annotated, not rewritten** (per instruction and `agents.md §5`): STALE
  banners added to `README.md`, `DOCS.md`, `QUICKSTART.md`,
  `API_DOCUMENTATION.md`, `HANDOVER.md`, `BLOCKERS.md`, `threads.md`,
  `audit.md`, `TODO.md`, `agents.md`, `failures.md`, `dashboard/index.html`,
  and the `site/server.py` docstring. Each states exactly what is wrong and
  points at current truth.
- **Fixed outright** (code, not prose): `core/warehouse_core.py` path,
  `manifest.py` path, `mcp_server.py` + `opencode.json` MCP wiring.
- **`.gitignore`**: added `extracted/` (untracked research tree) and
  `core/warehouse/` (runtime dirs created at import).

## Authoritative docs

| Topic | File |
|---|---|
| Live ops, units, tokens, Cloudflare | `docs/pow-systems-live.md` |
| Moat vs re-fetchable storage policy | `docs/data-moat-policy.md` |
| This session | `docs/build-progress-2026-09-25.md` |
| What compounds + how to sell it + next dev steps | `docs/data-product-report-2026-09-25.md` |
