# API reference — live routes

Authoritative list of what the running site exposes. Generated from
`site/server.py`, verified against `https://pow.systems` on 2026-09-25.

`API_DOCUMENTATION.md` at the repo root is **fiction** (its own banner says so:
`api.powpowpow.dev`, Bearer keys, rate tiers and a WebSocket do not exist).
It is kept as endpoint brainstorming only — this file is what is real.

---

## Base and auth

| | |
|---|---|
| Local origin | `http://127.0.0.1:8795` (`pow-site.service`, loopback only) |
| Public | `https://pow.systems` via Cloudflare Tunnel (`pow-cloudflared.service`) |
| GET auth | **none — all reads are public** |
| POST auth | `?token=$POW_SITE_TOKEN`, token in `~/.config/powpowpow/site.env` (mode 600) |
| Encoding | `charset=utf-8` on every response |
| SSE | `GET /api/ticks`,5-min connection cap, client auto-reconnects |

`site/server.py: do_GET` has no gate; only `do_POST` calls `_gate()`.

## Pages

| Route | Returns |
|---|---|
| `GET /` or `/index.html` | dashboard HTML |
| `GET /access.html`, `/login` | token-entry page (only needed to use chat) |
| `GET /powops` | pipeline status HTML |
| `GET /powops.json` | pipeline status JSON (cached 60s) |

## Read endpoints

| Route | Params | Returns |
|---|---|---|
| `GET /api/health` | — | `{ok, time}` — used by `pow-health` |
| `GET /api/home` | — | network cards, ops, storage, signals, state, health, `pipeline` |
| `GET /api/insights` | — | `chains`, `summary`, `version` — insight metrics vs price |
| `GET /api/ops` | — | service states + heartbeats (also `/powops.json`) |
| `GET /api/factors` | — | `cross_chain_factors.json` (burden, issuance, spread) |
| `GET /api/ticks` | `symbols` (comma list) | **SSE** freshest mid/spread per symbol |
| `GET /api/live` | — | latest `daily_state` rows + heartbeats |
| `GET /api/chain` | `symbol` | `network_state[symbol]` + fundamentals + row count |
| `GET /api/state` | `symbol`, `date` | daily STATE rows |
| `GET /api/state_series` | `symbol` | cross-venue daily aggregates |
| `GET /api/signals` | `symbol`, `date` | `derived_signal` rows |
| `GET /api/epoch_series` | — | last 30 QUBIC epoch rows |
| `GET /api/analysis` | `symbol` | price vs difficulty correlation |
| `GET /api/analytics` | `symbol` | `<symbol>_analytics.json` |
| `GET /api/history` | `symbol` | daily closes from `price_history` |
| `GET /api/btc` | — | `btc_context.json` (betas, security spend) |
| `GET /api/btc_series` | — | `chain_snapshot` series for BTC |
| `GET /api/xmr_full` | — | XMR analytics + network + closes |
| `GET /api/cards` | — | generated miner cards |
| `GET /api/cards_history` | `symbol` | card history |
| `GET /api/brief` | `date` | daily brief markdown |
| `GET /api/page` | `symbol` | compiled page markdown (404 — `pages/` not generated) |
| `GET /api/opportunity` | `hardware`, `date` | ranked opportunity rows |

## Write endpoints

| Route | Body | Auth | Notes |
|---|---|---|---|
| `POST /api/chat` | `{"message": "..."}` | token required | always falls back to data-only answers; `/home/ubuntu/qpbot` harness is absent on this box |

## Live vs stored

| Kind | Source | Freshness |
|---|---|---|
| Tick prices | `orderbook_snapshot` (SafeTrade WS) | ~seconds |
| Mining / chain | `network_state`, `chain_snapshot` | 300 s |
| Factors, STATE, signals, insights | hourly rollup at :25 | ≤60 min |
| Analytics (`*_analytics`, `btc_context`) | every 6 h | ≤6 h |
| Ops / pipeline | `pipeline_status` | ≤60 s cache |

## Known gaps

- `/api/page` returns 404 — `pages/` is gitignored and `compile_coins.py` is
  not scheduled.
- `/api/opportunity` returns an empty payload — `pow-opportunity.timer` and
  the `opportunity_snapshot` table were never installed on this box.
- `/api/signals` can be empty early in a day if fewer than 4 markets have
  measured emission + price; `signals.py` refuses rather than fabricating.
- No WebSocket; `/api/ticks` is SSE.
- No per-user API keys, rate limits or audit — see
  `docs/data-product-report-2026-09-25.md` gap list.
