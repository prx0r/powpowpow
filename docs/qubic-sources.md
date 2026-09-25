# QUBIC data sources — canonical registry

Status verified live from this box on 2026-09-25. Re-verify before relying on
it: `curl -sS -o /dev/null -w '%{http_code}' <url>`.

Nothing here is theory — every "OK" below was probed. Every "DEAD" was probed
and failed from `/root/powpowpow`.

---

## 1. Official API surfaces

Documented in `qubic/integration` (cloned at `/root/qubic-sources/integration`).

| API | Base path | Status | Notes |
|---|---|---|---|
| **Query API** | `/query/v1` | ✅ Active — **use this** | Indexed, verified, filterable; may lag network. Always call `getLastProcessedTick` first. |
| **Live API** | `/live/v1` | ✅ Active | Current tick, balances, broadcasting. |
| **Stats API** | `/v1/latest-stats`, `/v1/rich-list` | 🔄 "subject to change" | Swagger says `host: rpc.qubic.org` — **not** `api.qubic.org`. |
| **Archiver API** | `/v1`, `/v2` | ⚠️ **Deprecated, removed end of 2026** | Migrate to Query API (`integration/Partners/migration.md:42`). |

## 2. Verified live — collect these

| Endpoint | Method | Result | Used for |
|---|---|---|---|
| `rpc.qubic.org/v1/latest-stats` | GET | **200** | circulating supply, active addresses, price, mcap, epoch/tick, epoch + last-10k tick quality, burned QUs |
| `rpc.qubic.org/v1/rich-list?page&page_size` | GET | **200** (10,000 records = 100 pages) | wealth concentration |
| `rpc.qubic.org/live/v1/balances/{identity}` | GET | **200** | per-address balance (exchange reserves) |
| `static.qubic.org/v1/general/data/exchanges.json` | GET | **200**, 18 entries | exchange address labels |
| `rpc.qubic.org/query/v1/getEventLogs` (`logType=8`) | POST | **200** | per-tick BURNING events (beta) |
| `rpc.qubic.org/query/v1/getEventLogs` (`logType=0`) | POST | **200**, newest-first, cap 10,000 | `quTransfer` records: source, destination, amount |
| `rpc.qubic.org/query/v1/getComputorListsForEpoch` | POST | **200**, 676 identities | computor sets + churn |
| `rpc.qubic.org/query/v1/getLastProcessedTick` | GET | **200** | archive progress |
| `rpc.qubic.org/query/v1/getProcessedTickIntervals` | GET | **200** (epoch 104+) | per-epoch tick spans |
| `rpc.qubic.org/v1/tick-info` | GET | **200** | current tick/epoch/initialTick |
| `localmonero.co`, `xmrchain.net`, `blockchain.info`, `blockstream.info` | GET | 200 | XMR/BTC chain state (already wired) |

Query API methods available (from `query_services.openapi.yaml`):
`getComputorListsForEpoch`, `getEventLogs`, `getLastProcessedTick`,
`getProcessedTickIntervals`, `getTickData`, `getTransactionByHash`,
`getTransactionsForIdentity`, `getTransactionsForTick`.

## 3. Verified dead / blocked from this box

| Endpoint | Result | Cause |
|---|---|---|
| `api.qubic.org/*` | connection failure | no such public host reachable |
| `api.qubic.li/Score/EstimatedSolutionRevenue` | **401** | needs JWT from `api.qubic.li/Auth/Login` + `Origin: https://pool.qubic.li` |
| `stats-test.qubic.li/stats/dashboard` | unreachable | test host |
| `static.qubic.org/v1/general/exchanges.json` | **404** | wrong path — correct is `/v1/general/data/` |
| `rpc.qubic.org/query/v1/getCirculatingSupply` | **404** | not a real method |

## 4. Cloned references

`/root/qubic-sources/` (outside this repo, not committed):

| Repo | Status | Value |
|---|---|---|
| `qubic/qubic-stats-service` | cloned | source of `/v1/latest-stats` + `/v1/rich-list` contract |
| `qubic/integration` | cloned | Query/Live/Archiver docs, OpenAPI, migration table, epoch rules |
| `qubic/static` (as `qubic-static`) | cloned | **`data/exchanges.json`** + `address_labels.json` |
| `fyllepo/qubic-mcp` | cloned | reference MCP surface (balances, rich list, network status) |
| `qubic/go-data-publisher` | cloned | Go message-broker publishers; streaming alternative |
| `Pickle-Pixel/qubic-dashboard` | cloned | pool metrics → MongoDB → Grafana; needs JWT |
| `tomaspozo/qubic-metrics` | cloned | React analytics app; needs a token |

Not cloned: the repo containing `SOURCES.md`/`TRANSFORMS.md`/`transforms/puell.py`
was described without a URL.

## 5. What PowPowPow actually collects

| Table | Cadence | Source |
|---|---|---|
| `qubic_stats` | 300s | `/v1/latest-stats` |
| `qubic_exchange_balance` | 300s | `exchanges.json` × `live/v1/balances` |
| `qubic_wealth_concentration` | every 72 passes (6h) | `/v1/rich-list` ×100 pages |
| `qubic_burn_event` | 300s | `getEventLogs` `logType=8` |
| `qubic_transfer_window` | 300s | `getEventLogs` `logType=0` (1,000 transfers/pass) |
| `qubic_epoch` | 10 min | `tick-info` + `status` |
| `computor_snapshot`, `external_mining` | hourly | `getComputorListsForEpoch`, `doge-stats` |
| `chain_snapshot`, `network_demand` | 300s | `tick-info`, `status`, `analytics.qubic.li` |

Collectors: `collectors/qubic_stats.py`, `collectors/qubic_holdings.py`,
`collectors/chain_state.py`, `scripts/qubic_epoch.py`,
`scripts/qubic_computors.py`. Exchange labels are cached at
`warehouse/knowledge/qubic_exchanges.json`.

Metrics derived from all of the above: `docs/pow-systems-live.md` →
*Insight metrics vs price*.

## 6. Third party (cross-check only, not collected)

| Source | What it shows | Why not collected |
|---|---|---|
| `qubic.lt/analytics/*` | exchange reserves (60d), Gini, whale events, netflow | third-party UI, no stable API; useful to sanity-check our numbers |
| `explorer.qubic.org` | circulating supply, tick quality | duplicates `/v1/latest-stats` |
| `pool.qubic.li` | pool hashrate, revenue | needs JWT; parked |
| `grafana.pickle-pixel.com` | qubic-dashboard output | parked |

## 7. Known gaps

1. **No hashrate history for QUBIC** — `chain_snapshot/chain=qubic` carries
   only `height` + `epoch`, so `price_hashrate_divergence` refuses for QUBIC.
   Source needed: computor hashrate or tick-rate-derived network rate.
2. **`active_addresses` and `burned_qus` are coarse counters** — unchanged
   across 16 minutes of 5-minute snapshots. Growth metrics from them will read
   0 most passes. Burn rate must come from `getEventLogs` instead (it does).
3. **Rich list caps at 10,000** (`pagination.totalRecords = 10000`); older
   docs quoted 476,802. Concentration is therefore *top-10k*, disclosed in the
   metric's `window`.
4. **Stats API can break without notice** — treat `/v1/latest-stats` as
   replaceable, Query API as canonical.
5. **Per-epoch burn/deduction summaries blocked upstream** (`qubic/integration`
   issue #102) — reconstructed from BURNING events meanwhile.
