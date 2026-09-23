# DevPlan Response — PowPowPow Current State & Global Threads

> **Generated 2026-09-23 from live repo audit.**
> Reviews every thread in the codebase, what's landed, what's blocked,
> and what the global devplan may be missing.

---

## TL;DR

PowPowPow is a **data garden** that continuously collects compute/crypto
telemetry and transforms it into historical economic state. The garden
clock started 2026-09-19. SafeTrade (the venue-of-truth for PRL, QUBIC)
was blocked until today — now live. The system collects from 8+ chains,
3 venues, derives versioned signals, and publishes to a consumer site
at pow.moltwork.com.

**What landed today (2026-09-23):**
- SafeTrade WS + REST unblocked (Cloudflare bot detection, not geo-block)
- SafeTrade collector running as systemd service `pow-safetrade-l2`
- R2 upload pipeline verified (10/10 test files to `powpowpow-warehouse`)
- `core.py` User-Agent fix (was `PowPowPow/1.0`, now browser UA)
- `core/` package shadowing `core.py` — silent import fallback fixed

---

## 1. What's Live & Working

### Collectors (all systemd-supervised)

| Service | Status | What it does |
|---------|--------|--------------|
| `pow-venue-l2` | RUNNING | REST polls 19 markets CoinEx+Gate+MEXC every 60s |
| `pow-venue-ws` | RUNNING | WebSocket tick archive CoinEx+Gate |
| `pow-chain-state` | RUNNING | QUBIC RPC + XMR localmonero + KAS + Nockscan every 5min |
| `pow-qubic-epoch` | RUNNING | Epoch engine: burn schedule + net emission every 10min |
| `pow-qubic-computors` | RUNNING | Computor set + Doge tasks every hour |
| `pow-daily-state` | RUNNING | STATE rollup + Parquet compact + trim at 00:30 UTC |
| `pow-site` | RUNNING | Consumer site on pow.moltwork.com (token-gated) |
| `pow-safetrade-l2` | RUNNING | SafeTrade WS depth+trades (25 streams) — **NEW TODAY** |
| `pow-pearld` | PAUSED | Full node resyncing, paused during disk triage |

### Data Pipeline

```
APIs → core.fetch_json (archive raw) → collectors normalize → warehouse
warehouse → build_daily_state → Parquet compact → trim (7d hot)
warehouse → signals.py → derived_signal table
warehouse → analytics scripts → JSON snapshots
warehouse → backtest.py → forward return analysis
warehouse → site/server.py → dashboard + MCP
warehouse → r2_upload.py → Cloudflare R2 (daily) — NEW TODAY
```

### Signals (v1, live)

| Signal | Status | Notes |
|--------|--------|-------|
| `miner_pressure_v1` | LIVE | Cross-sectional burden z-score, refuses on thin data |
| `flow_pressure_v1` | LIVE | Venue trade flow vs resting book |
| `required_flow_v1` | LIVE | How much buying the day needed to stand still |

### Storage Doctrine

- Hot JSONL: 7 days (trimmed)
- Parquet: forever (25-30x compressed)
- Raw: append-only forever (auto-archived)
- Chain bytes: extract-and-release (never hoarded)
- Off-box: R2 bucket `powpowpow-warehouse` (daily upload)

---

## 2. All Threads in the Repo

### Thread 1: Architecture & Vision (01_architecture_and_vision.md)

**Status:** COMPLETE design doc, schema-first approach.

**What it defines:**
- Universal schema: chain_snapshot, block, market_snapshot, orderbook_level,
  trade, miner_economics, protocol_event
- Per-chain schemas: QUBIC, PRL, NOCK, QUAN, TSC, GNK, XMR
- Ingestion order: QUBIC+PRL+SafeTrade → TSC+GNK → NOCK+QUAN → XMR
- Cross-chain factor table (14 factors, 6 live today)

**What's missing from devplan:**
- The ingestion order was QUBIC+PRL first, but SafeTrade was blocked.
  Now unblocked — PRL data collection can begin properly.
- TSC+GNK collectors exist but are not yet wired to chain pollers
  (endpoints unreachable from this VPS).

### Thread 2: Pressure Equation Research (02_pressure_equation_research.md)

**Status:** Academic references compiled, formulas defined.

**What it defines:**
- Seesaw framework: Innovation → ΔConstraint → ΔShadowPrice → Capital Allocation
- Miner sell burden, absorption ratio, dilution pressure
- OFI (Order Flow Imbalance) and two-timescale model

**What's missing:**
- OFI and two_timescale.py still run on stale file inputs
- Need to rewire onto STATE + derived_signal tables

### Thread 3: Seesaw Filter (03_seesaw_filter.md)

**Status:** Inclusion criteria defined (7 requirements + 2 bonus).

**What it defines:**
- A system qualifies only if observable demand creates a binding constraint
  with a measurable shadow price, capital allocates, and supply responds
  through observable resources.

**What's missing:**
- No automated filter implementation yet — manual review only.

### Thread 4: Canonical Universe (04_canonical_universe_v1.md)

**Status:** 16 candidate systems, V1 admission rules.

**What it defines:**
- Tier 1: QUBIC, PRL, NOCK, QUAN, TSC, GNK, XMR
- Tier 2: NPT, XTM, XEL
- Admission: must have observable emissions, exchange listing, some hashrate data

**What's missing:**
- Tier 2 coins (NPT, XTM, XEL) have no collectors yet.

### Thread 5: Extended Coin Research (05_extended_coin_research.md)

**Status:** Research complete for TAO/KAS/QRL/ZEPH/ALPH/ERG/XTM.

**What it defines:**
- Additional systems that could force the ontology to become more general
- TAO (machine intelligence), QRL (post-quantum), ZEPH (algorithmic)

**What's missing:**
- None of these have collectors. They're research-only.

### Thread 6: Moat Strategy (06_moat_strategy.md)

**Status:** COMPLETE moat theory.

**What it defines:**
- 8 moat layers: historical miner economics, pool/miner identity graphs,
  hardware benchmark registry, protocol-change history, raw order-book
  archive, compute-output history, exchange-flow attribution,
  reproducible source-code-derived tokenomics
- Per-chain moat specifics for QUBIC, PRL, NOCK, QUAN, TSC, GNK, XMR

**What's missing:**
- Identity graph work is blocked on pearld sync.
- Hardware benchmark registry is conceptual only.

### Thread 7: Coin Categories (07_coin_categories.md)

**Status:** Category system defined.

**What it defines:**
- Categories: privacy, useful-compute, proof-native, post-quantum, etc.
- Cross-category comparisons

**What's missing:**
- No automated categorization.

### Thread 8: Missing Data Layers (08_missing_data_layers_research.md)

**Status:** Research complete.

**What it defines:**
- Electricity prices, GPU rental rates, inference revenue
- Hardware benchmarks, pool composition

**What's missing:**
- No collectors for these yet. They're conceptual.

### Thread 9: Transforms (transforms.md)

**Status:** Formula registry — live vs queued with blockers.

**What's landed:**
- 11/24 factors LIVE
- 7/24 QUEUED (need circulating supply, hashrate history, pool graph, etc.)

### Thread 10: Failures (failures.md)

**Status:** Living document of what was tried and what broke.

**Key failures:**
1. SafeTrade geo-block → **FIXED TODAY** (was Cloudflare bot detection)
2. Old SafeTrade stack unrecoverable → mitigated with warehouse fallback
3. PRL chain/pool telemetry dry → pearld paused, needs resync
4. KAS emission units unconfirmed
5. AKT/NOS/CLORE endpoints unreachable
6. Tardis paid history ($249/mo) — not worth it at current scale
7. OOM at 2.6GB → fixed with streaming STATE builder (100-400MB RSS)

### Thread 11: Products (products.md)

**Status:** 7 products defined, sequencing planned.

**Products:**
1. Pow MCP/API (read-only resource economics) — partially landed
2. Local Allocation Agent — not started
3. Bounded executor — not started
4. XMR treasury adapter — not started
5. Execution receipts — not started
6. Multi-machine controller — not started
7. Private supply aggregation/MPC — not started

### Thread 12: Site (site/)

**Status:** LIVE at pow.moltwork.com.

**What works:**
- Token-gated, black/white/grey, austere design
- Left rail: HOME + coins + CHAT
- Per-coin subtabs: Overview/Market/Mining/Signals
- Canvas graphs, auto-refresh, plain-language dossiers
- /api/analysis, /api/history, /api/cards_history

### Thread 13: MCP Server (mcp_server.py)

**Status:** Verified end-to-end (6 tools, live tables).

**Tools:**
- pow_get_profitability, pow_compare_workloads, pow_get_resource_price
- pow_get_miner_pressure, pow_get_energy_proxy, pow_get_market_depth

### Thread 14: SafeTrade (collectors/l2_archival.py)

**Status:** **FIXED TODAY** — was blocked, now running.

**Root cause chain:**
1. `PowPowPow/1.0` User-Agent → Cloudflare 403 → fixed to browser UA
2. Missing `ssl=ssl_ctx` in websockets.connect → fixed
3. `core/` package shadowing `core.py` → silent None import → fixed
4. `rest_checkpoint` blocking event loop → changed to `asyncio.create_task`

### Thread 15: R2 Upload (scripts/r2_upload.py)

**Status:** **NEW TODAY** — verified 10/10 test files.

**What works:**
- AWS SigV4 signing with `x-amz-content-sha256`
- Separate Access Key / Secret Key auth
- Bucket `powpowpow-warehouse` created (APAC region)
- Systemd timer `pow-r2-upload.timer` for daily uploads

### Thread 16: Datagarden Integration (datagarden/)

**Status:** Shared primitives defined but not integrated.

**Primitives:** entity, observation, signal, receipt, source, storage,
valuation, capability, hardware, quality, outcome, derived

**What's missing:**
- Datagarden primitives not used by powpowpow collectors yet.
- Separate schema that could unify with powpowpow's warehouse.

### Thread 17: PowParts (powpowpow.md)

**Status:** Vision document only — 2000+ lines.

**What it defines:**
- Physical capability component graph (function → implementation → part → market)
- BOM history, substitution graphs, manufacturing benchmarks
- "Don't store what can be queried later. Store what only exists because we were watching."

**What's missing:**
- No implementation. Pure vision doc.
- Could be a separate garden that powpowpow's methodology clones.

### Thread 18: PowSystems (powsystems/)

**Status:** Compressed reference data from agent inbox.

**Contains:**
- UKGraph ZIP reports
- Post-AGI research memos
- PowPowPow + datagarden peer reviews

---

## 3. What the Global DevPlan May Be Missing

### 3.1 SafeTrade Was Never Really Blocked by Geography

The original diagnosis was "geo-block from Canada." The actual cause was
Cloudflare bot detection on the `PowPowPow/1.0` User-Agent. This means:

- **Every other collector using non-browser UAs may also be silently failing.**
  Check: `chain_state.py`, `qubic_collector.py`, `xmr_collector.py`.
- **The "geo-block" narrative delayed fixing this for days.**
  Always test with browser UA before assuming IP-level blocks.

### 3.2 The `core/` Package Shadowing Is a Latent Bug for All Collectors

Any collector that does `from core import ...` will silently get `None`
for `_archive_raw`, `store_normalized`, `utcnow`, `fetch_json` because
Python finds `core/__init__.py` first.

**Fix needed:** Either rename `core/` to something else (e.g., `powcore/`)
or make all collectors use `importlib` to load `core.py` directly.

### 3.3 No Automated Health Checks

Services can silently fail (import errors, empty data) and nobody notices
until the site shows stale data. Need:

- Heartbeat monitor per collector
- Alert if no new raw files in N minutes
- Alert if STATE build fails
- Alert if Parquet compaction falls behind

### 3.4 Storage Growth Will Hit Disk Limit

Current: 45MB warehouse, 125GB/160GB used. SafeTrade will grow this fast
(depth snapshots every WS update for 25 streams). The R2 upload handles
off-box backup but doesn't reduce local disk usage.

**Needed:** Local cleanup policy that removes raw files older than N days
after confirmed R2 upload.

### 3.5 Backtest Needs More History

Backtest.py refuses until 2+ days of STATE. Garden started 2026-09-19.
By 2026-09-25 we'll have 6 days — still thin for statistical significance.
By 2026-10-19 we'll have 30 days — first meaningful backtests.

### 3.6 The Site Has No Authentication Beyond Token

Token is hardcoded in systemd service. Anyone with the token can access
the site. No per-user auth, no rate limiting, no audit log.

### 3.7 MCP Server Is Not Deployed

Verified end-to-end but not running as a service. No agent is querying
the garden through MCP yet.

### 3.8 PowDaily Is Not Automated

`scripts/powdaily.py` generates a daily brief but is not wired to
a cron/timer. The brief is the primary content outlet.

### 3.9 Missing: Realized Outcome Data

The products.md describes a flywheel where agents act on signals and
report back realized outcomes. None of this exists yet. The garden
collects telemetry but doesn't close the loop.

### 3.10 Missing: Cross-Chain Correlation

No code yet correlates events across chains (e.g., "QUBIC epoch
boundary → PRL miner migration → XMR hashrate spike"). The data is
there but the analysis isn't.

---

## 4. Priority Actions (If I Were Building the DevPlan)

| Priority | Action | Effort | Unblocks |
|----------|--------|--------|----------|
| P0 | Rename `core/` to `powcore/` or fix all imports | 1h | Silent None bugs in all collectors |
| P0 | Add browser UA to all remaining collectors | 30m | Potential silent 403s |
| P1 | Wire `powdaily.py` to systemd timer | 15m | Daily content output |
| P1 | Add collector health monitoring | 2h | Operational visibility |
| P1 | Deploy MCP server as systemd service | 1h | Agent access to garden |
| P2 | Add local cleanup policy (remove raw after R2 confirm) | 1h | Disk management |
| P2 | Wire TSC+GNK collectors (need endpoint access) | 4h | Useful-compute metrics |
| P2 | Wire OFI + two_timescale to STATE tables | 2h | Signal completeness |
| P3 | Implement automated Seesaw filter | 4h | System qualification |
| P3 | Add NPT/XTM/XEL collectors | 3h | Tier 2 coverage |
| P3 | Build cross-chain correlation analysis | 8h | Research moat |

---

## 5. The Garden's Position in the Broader System

```
PowPowPow (observe)  →  Seesaw (decide)  →  QP/grants (authorize)
                                                    ↓
                                              agents (act)
                                                    ↓
                                              XMRBot (settle privately)
                                                    ↓
                                              receipts/proofs (verify)
                                                    ↓
                                              PowPowPow (observe actual result)
```

The garden is the foundation. Everything else depends on it having
reliable, historical, provenance-preserving data. Today's SafeTrade
unblock and R2 upload are the two highest-impact changes since the
garden clock started.

---

*Generated by opencode from live repo audit, 2026-09-23T14:30+07*
