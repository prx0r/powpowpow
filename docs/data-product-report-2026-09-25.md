# Data product report — what compounds, and how to sell it

2026-09-25. Answers four questions: what do we actually collect each day,
what does it become after ~60 days, how could it be sold over an API, and did
we already do this work?

---

## 1. What we collect each day (measured, not modelled)

Steady-state rate taken from the last 60 minutes of a running collector, then
projected. Warehouse today: **443 MB**, 74,584 normalized rows.

### Per hour

| Table | rows/h | B/row | Notes |
|---|---:|---:|---|
| `orderbook_snapshot` | 13,494 | 698 | SafeTrade depth for tracked POW markets |
| `ticker` | 3,471 | ~500–2,700 | trimmed this session; older rows still 29 KB |
| `trade` | 560 | 600 | SafeTrade prints |
| `chain_snapshot` | 43 | 517 | QUBIC/XMR/BTC polls, 300s |
| `fee_market` / `mempool_snapshot` / `pool_snapshot` | 22 each | ~480–580 | XMR fee+mempool+p2pool, BTC fees+pools |
| `daily_state` / `derived_signal` | 21 / 22 | ~1,000 | hourly rollup + signals |
| `qubic_epoch` | 5 | 765 | epoch engine, 10 min |
| `computor_snapshot` / `external_mining` | 1 / 1 | 43,760 / 497 | hourly QUBIC identity + DOGE leg |
| **Total normalized** | **17,695** | — | **461 MB/day** |
| **Raw observations** | **14,916** | ~2,700 | **979 MB/day**, one JSON per stream event |

### Per day

| | Rows/files | Bytes |
|---|---:|---:|
| Normalized | ~425,000 | 461 MB |
| Raw | ~358,000 objects | 979 MB |

### After 60 days, unchanged

| | Cumulative |
|---|---:|
| Normalized | **25.5 M rows / 27.7 GB** |
| Raw | **21.5 M objects / 58.8 GB** |

The split matters: **76% of rows and most of the byte volume are SafeTrade
L2 depth.** That is deliberate — it is the only class of data here that
disappears if we stop.

---

## 2. What actually becomes valuable over 2 months

Ranked by (irreversibility × uniqueness × POW-coin relevance).

### A. Emission-absorption series for POW coins — **the product**

`burden_vs_book = daily emission USD ÷ resting top-20 bid notional`, computed
per coin from our own L2 books. Today it exists for BTC/QUBIC/XMR/PRL/KAS/
NOCK/XEL. In 60 days that is **~1,300 daily observations per coin** — a
time series nobody else can rebuild, because the denominator is a book snapshot
that no archive vendor sells for QUBIC/PRL/NOCK/XEL.

Positioning fit: this *is* "POW coins" — issuance pressure measured against
the only venue that quotes these markets.

### B. Signal labels with evidence (a labelled dataset)

22 signals/day × 60 days = **~1,320 labelled points**, each carrying
`evidence.daily_state_records`, `emission_source`, `assumptions`,
`confidence`, `z`, `version`. The label + provenance pair is the sellable
object; a bare z-score is not.

`threads.md:33` already dates the payoff: backtests become meaningful at
~30 days STATE (**mid-Oct 2026**).

### C. POW-coin L2 microstructure archive

Today: ~324k depth updates/day, ~13k trades/day, ~83k ticker rows/day.
Over 60 days: **~19 M depth updates and ~800 k trades** for markets that are
thinly covered or absent elsewhere. Priced correctly this is the "we have
yesterday's book, you don't" asset (`backfill.md:83`, `06_moat_strategy.md:526`).

### D. Point-in-time state snapshots

`pool_snapshot` (P2Pool miners, BTC 5-day pool concentration), `qubic_epoch`
+ `computor_snapshot` (sets/churn per epoch → ~8.5 epochs in 60 days),
`mempool_snapshot`/`fee_market` history. All rolling-window upstreams: the
time-indexed copies exist only here.

### E. Not valuable to sell (context only)

`price_history` (CoinGecko/Kraken/CoinEx), `chain_snapshot` history from
`blockchaininfo-charts`, `xmrclub-mining`. All re-fetchable — classified
`reconstructable` this session (`docs/data-moat-policy.md`). Useful as joins;
should never be the product.

---

## 3. Did we already do this work?

**Collection and moat: yes, settled.**
**Commercialisation: explicitly deferred — not done.**

### Settled (do not redo)

| Claim | Where |
|---|---|
| Moat ≈ transformation × continuous collection × time; raw is not the moat | `devplancurrent.md:40-52` |
| The dataset *is* "historical opportunity cost of compute" | `devplancurrent.md:100` |
| 8 moat layers; L2 archive + identity + benchmarks | `06_moat_strategy.md:11-22,526` |
| Ephemeral vs backfillable doctrine, now machine-readable | `backfill.md:5-6`, `docs/data-moat-policy.md` |
| Unlock calendar: meaningful backtests ~mid-Oct 2026 | `threads.md:33-34`, `devplanresponse.md:326` |
| "Capture first. Normalize second. Productize last." | `emails/1789919095015.eml:557` |
| Source must carry licence/redistribution fields | `emails/1789919095015.eml:283-298` |
| Read-only MCP/API is product #1, "partially landed" | `products.md:220`, `devplanresponse.md:203` |
| Endpoint shape sketch | `01_architecture_and_vision.md:1045-1063` |
| Publishable index names `PPP_*` | `datacollection.md:107-124` |

### Open (not done)

| Question | Evidence |
|---|---|
| What IS the paid product? | `unsure.md:159-168` — *"Build data first, decide later"* |
| What is the MVP? | `unsure.md:181-190` — *"Data pipeline first, product later"* |
| Who buys it? | **No named buyer for PowPowPow data anywhere** (only the repair-domain threads name buyers) |
| API keys / tiers / billing | `API_DOCUMENTATION.md` tiers are **self-declared fictional**; no Stripe, no price |
| Who is the customer vs Glassnode/CryptoQuant? | `unsure.md:170-179` gives differentiation, never a buyer |
| "POW coins" positioning | **Zero matches** outside the excluded `extracted/` tree |
| Monetisation phase in the roadmap | `VISION.md:260-288` phases 1–4, **no revenue phase** |

---

## 4. Gaps

### Data gaps

1. **Depth is one venue.** `venue_l2`/`venue_ws` (CoinEx/Gate/MEXC) are not
   installed, so `burden_vs_book` is a single-book denominator. Signals admit
   it in `assumptions`.
2. **6 days of history, not 60.** `chain_snapshot` is hours-thin, `daily_state`
   has 1 date. Value in §2 is *projected*, not banked — uptime is the asset.
3. **`known_at` / `superseded_at` unimplemented** (`backfill.md:123`) — the
   point-in-time layer that makes backtests defensible is still missing.
4. **BTC hashrate unit is an unconfirmed assumption** (`chain_state.py`
   "GH/s ASSUMED … UNCONFIRMED"). Shipping an assumption to a customer is a
   credibility risk.

### Legal / packaging gaps

5. **No source licence manifest.** The policy exists only in email. Without
   per-source `commercial_use` / `redistribution` / `api_cache_limit` fields
   we cannot legally resell rows whose source is CoinGecko/Kraken/Blockchain.com.
   Mitigation: sell only `ephemeral` rows (our own observations) — those are
   ours — and never ship `reconstructable` rows.
6. **No terms / attribution / redistribution statement** for a paid tier.

### Product / engineering gaps

7. **No per-user API key, rate limit, or audit** — `BLOCKERS.md:108` states it
   plainly: one shared token, no per-user, no rate limit, no audit.
8. **No billing, no pricing, no entitlement model.**
9. **No exports** — JSON API + stdio MCP only. Buyers of data series want
   Parquet/CSV/SDK, and we already produce Parquet for compact tables.
10. **MCP has no auth or quota** — `mcp_server.py` is read-only and provenance
    correct, but any client can call it unbounded.
11. **`API_DOCUMENTATION.md` is fiction** and now correctly bannered STALE;
    there is nothing to hand a developer.

### Cost / scale gaps (surfaced by this measurement)

12. **Object count, not bytes, is the scaling risk.** 358k raw writes/day ≈
    **10.7 M/month**, and the verifier issues a comparable number of HEADs.
    Cloudflare R2's free allowance is ~10 M Class A and 10 M Class B per month,
    so **within ~2 months both classes edge over the free tier.** Storage itself
    stays pennies (86 GB ≈ $1.30/mo at $0.015/GB). Options: batch raw into
    hourly archives, add an R2 lifecycle for reconstructable prefixes, or accept
    the cost as the price of the moat.
13. **Local disk is 95% used** (3.8 GB free). At 1.44 GB/day combined and
    24–30 h retention we are within ~2 days of the 2 GiB floor where collectors
    pause by design (`POW_MIN_FREE_BYTES`).

---

## 5. How to sell it over an API

Constraint from the repo's own thesis: `datagarden/thesis.md:30-42` argues the
conventional `scrape → clean → database → sell access` model is fragile as AI
improves, and `emails/1789919095015.eml:349` says if an agent can make three
fresh calls and get the same answer, it is distribution, **not** moat.

So sell the two things that are neither scraped nor trivially recomputable:

**Tier 1 — the series (raw material).**
`/v1/series/burden/{coin}?from&to`, `/v1/series/microstructure/{market}`,
`/v1/series/pool/{coin}`. Backed by `ephemeral` rows only. Parquet + CSV
download, not just JSON. This is the Glassnode/CryptoQuant-shaped product but
for POW-coin issuance pressure (`unsure.md:170-179`).

**Tier 2 — the labelled history (the actual differentiator).**
`/v1/signals?date&coin` returning the full evidence envelope, plus
`/v1/point-in-time?as_of=` once `known_at` exists. This is what a quant
cannot rebuild from public APIs: labels + what was known when.

**Tier 3 — MCP for agents.** Already 13 tools. Add per-key quota so it becomes
a metered product rather than an open pipe.

Deliberately **not** sold: `price_history`, chain backfill, OHLCV — they are
`reconstructable`, cheap to fetch, and reselling them adds licence risk for
zero differentiation.

Minimum viable paid surface = **keys + quotas + one Tier 1 endpoint + Parquet
export.** Everything else is packaging on top.

---

## 6. Next dev steps (ranked)

| # | Step | Why now | Effort |
|---|---|---|---|
| 1 | **Per-user API keys + rate limits + audit log** on `site/server.py`, keeping GETs public at a low anonymous tier | Unblocks every other commercial step; `BLOCKERS.md:108` already names it | M |
| 2 | **Source licence manifest** — implement the fields from `emails/1789919095015.eml:283` as `recoverability`-adjacent metadata; refuse to expose rows without `commercial_use` | Without it, selling is legally unsound | S |
| 3 | **Bundle raw into hourly archives** (or add an R2 lifecycle for `reconstructable`) | 358k objects/day crosses R2 free ops in ~60 days | M |
| 4 | **Parquet/CSV export endpoint** from existing `warehouse/parquet` | Data buyers need files, not JSON; compactor already exists | S |
| 5 | **`known_at` / `superseded_at` on entity + signal writes** | Makes §2-B sellable as point-in-time; currently unimplemented | M |
| 6 | **Pick one canonical box / stop tracking regenerated artifacts** | The two-box race already clobbered analytics once (open thread §1) | S |
| 7 | **Rebuild `API_DOCUMENTATION.md` from the live routes** (replace the fictional one; keep it STALE-annotated, add `docs/api-v1.md`) | Nothing is handable to a developer today | M |
| 8 | **Decide the paid product** — record the answer in `unsure.md` Q13/Q15 instead of "decide later" | Everything above is packaging; the decision is still open on the record | S |
| 9 | **Name a buyer** and validate Tier 1 against them before building Tier 2 | No named buyer exists for this data anywhere in-repo | S |
| 10 | **Protect the 60-day clock** — disk headroom (drop raw retention to 12 h while tight), R2 job cadence vs 1 h timer, single-box push | The value in §2 only accrues if collection does not stop | S |

### Deliberately deferred

- CoinEx/Gate/MEXC cross-venue depth (`BLOCKERS §5`: only wire what feeds a
  named transform) — revisit when Tier 1 is being sold, because it directly
  improves `burden_vs_book`.
- Paid Tardis history ($249/mo, `BLOCKERS.md:44`) — still not worth it at
  current scale.
- Re-selling public OHLCV — licence risk, zero differentiation.

---

## 7. Positioning note

"POW coins" is not currently expressed anywhere in this repository as product
positioning — zero matches outside the excluded research tree. What *is*
settled is that PowPowPow is the compute/mining pillar of POW.SYSTEMS
(`devplancurrent.md:216`).

The defensible sentence, built entirely from assets we already collect:

> **We measure the issuance pressure of proof-of-work coins against the only
> order books that quote them — continuously, with provenance, from now on.**

Everything in §2-A/B/C is exactly that sentence, and nothing else in the
repository needs to change to stand behind it.
