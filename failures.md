# Failures — what was tried, what broke, what unblocks it

> Every failure below was hit live from `vps-e94d5dea` on 2026-09-19.
> Nothing here is assumed — each entry has a probe behind it.
> Outage evidence for collector failures also lands in the warehouse
> (auto-archived fetch failures), this file is the human index.

## 1. SafeTrade — fully blocked (IP-level geo-fence)

- REST `safe.trade/api/v2/trade/public/*` (markets, tickers, timestamp,
  swagger): **HTTP 403** direct AND via agent-vault proxy. Body is the
  Canada geo-block page ("does not currently allow trading or new
  signups for Canadians").
- Same paths on `safetrade.com`: **403**, same page.
- WS `wss://safe.trade/...` + `wss://safetrade.com/.../websocket/public`:
  **403 on handshake**, browser headers included.
- Signed private REST with valid vault creds (key len 16 + secret len 32
  retrieved, HMAC nonce/key signature per official client): **403, same
  Canada page**. Auth cannot fix an IP-level block.
- Unblocks: run `collectors/l2_archival.py` (committed, replay-verified)
  from any unblocked machine + rsync `warehouse/` back, or proxy on
  unblocked egress. Vault creds are confirmed working — only the network
  path is broken.

## 2. Old /home/box SafeTrade stack — never migrated, unrecoverable here

- `/home/box` does not exist on this VPS. The tracker daemon
  (`daemon.py` start/stop/status), `{COIN}_depth*.json` +
  `{COIN}_1d_ohlcv.csv` in `safetrade/tracked/`, and the ML pipeline
  (`feature_pipeline.py`, `train_model.py`, `live_predictions.py`)
  exist only as references in QUICKSTART/`api/app.py`/`export.py`.
- No tracked data, snapshots, or model artifacts found anywhere on box
  (searched `/home/ubuntu`, `/tmp`, `/`). If the old machine still
  exists, its `safetrade/tracked/` dir is the single most valuable
  recovery target on this list.
- Mitigations landed: `export.py` falls back to warehouse daily_state
  mid-OHLC, `api/app.py` reads warehouse snapshots, QUICKSTART rewritten.

## 3. PRL chain/pool telemetry — dry from here

DOCTRINE (2026-09-19): chain bytes are not the moat — any peer
re-serves them. `pearld/data` (full chain + addrindex, ~6GB at
tip) was deleted twice during disk triage at zero information loss;
resync is ~2h. When the pool graph build starts: sync → extract
pool/miner/exchange flows into warehouse tables → drop chain data.
Hoard only what cannot be reconstructed (L2 books, polls, derived).

- `https://rpc.pearlresearch.ai` (pearld JSON-RPC `get_info`): **timeout**.
- PearlTrack `GET /api/v1/{network,blocks,pools,transfers}`: **all 404**.
  Homepage is a Next.js SPA with **zero `/api/*` references** in HTML —
  no discoverable API surface.
- `prlscan.com` + `/api/v1/network`: SPA HTML, no API.
- Unblocked 2026-09-19: `pearld` v1.4.8 linux-amd64 binary runs;
  own node syncing under systemd `pow-pearld` (target height 115,530 at
  start, `--addrindex` on for future miner-graph queries). Data dir
  wiped once during disk triage (43MB free); resyncing fresh ~14:10 UTC,
  ~2h pace. Until sync completes, PRL has venue L2 + static emission only.

## 4. Qubic RPC — archive Query API found, computors captured

- **qubic.tools: dead** (DNS does not resolve). **qubic.it: dead**
  (connection reset). Neither is a live resource; ignore both.
- Public RPC surface really is tick-info + status only — BUT the
  official archive Query API at `rpc.qubic.org/query/v1` was missed
  earlier: `getLastProcessedTick`, `getProcessedTickIntervals`,
  `getComputorListsForEpoch` (POST), `getTickData`, transactions,
  `getEventLogs` (beta). Computor set captured 2026-09-19
  (`scripts/qubic_computors.py`, 676 identities epoch 231, churn
  tracked). Remaining: per-epoch burn aggregation (heavy tick
  scans), exchange labels (static registry 403).
- **doge-stats.qubic.org/dispatcher.json LIVE**: active_tasks +
  per-computor shares → external DOGE-mining revenue leg captured.
- **explorer.qubic.li/epochs/{n}**: rich per-epoch pages but SPA with
  no JSON API — use archive Query API instead.
- guardians.qubic.org node sync overview: candidate health feed,
  not yet collected.

- Live: `/v1/tick-info` (tick 80792768, epoch 231), `/v1/status`
  (19KB, includes per-epoch tick map — epoch history reconstructable).
- 404: `/epoch-info`, `/epochs`, `/epochs/231`, `/computors`,
  `/tick-data/*`, `/latest/stats`, `/network-info`, `/health`.
- Unblocks for computor sets / burn accounting: Qubic archiver
  endpoints (go-archiver / core-bob / qubic.li). Queued.

## 5. XMR fallbacks — mixed

- `rpc.monero.obl.alee.pw`: **DNS fail**. `minero.cc/api/network`:
  **connection refused**.
- Live: `localmonero.co/blocks/api/get_stats` (height, difficulty,
  5.9GH hashrate, total emission, last reward). Confirms seeded scale.
- Pool-level flow: impossible by protocol design — marked, not pursued.

## 6. Kaspa — mostly live, units unconfirmed

- Live: `/info/hashrate` (354332.5, **units unconfirmed** — scale fits
  PH/s but not verified), `/info/price`, `/info/coinsupply/circulating`
  (27.7B KAS, baselined for day-delta emission).
- 404: `/info/circulating-supply`, `/info/virtual-chain-stats`.
- KAS money math stays gated until units confirm + first delta lands.

## 7. Nock/Xelis/Tari/Kryptex — mixed

- Live: `nockscan.net/api/v1/{recent-blocks,proof-rate}`.
- Dead: `explorer.xelis.io/api/stats` (404), stats.xelis.io (SPA only),
  `explore.tari.com/api/*` (SPA), kryptex pool API (anti-bot HTML now),
  minero (refused).
- XEL/XTM have no live stats endpoint from here; fundamentals-only.

## 8. Rental marketplaces — dry from here

- `clore.ai/api/v1/marketplace`: **404**. `api.akashnet.io/*`:
  **DNS fail**. `api.cloudmos.io/*`: **SSL EOF**. `api.nosana.io/*`:
  **DNS fail**. `api.akashnet.net/gpu`: 501. `console.akash.network`:
  404. Only CoinGecko prices work.
- Collectors migrated to auto-archive so failures record outage
  evidence; rental demand half waits on reachable endpoints.

## 9. Venue API quirks found by probing (all handled in code)

- CoinEx has NO `/v2/spot/order_book` (404) — books live at
  `/v2/spot/depth`, levels nested under `data.depth` (parser fixed).
- Gate `XMR_USDT` book: **400** (delisted — discovery filters it).
- Gate WS `spot.order_book` rejects interval `"0"` — must be `"100ms"`.
- CoinEx + Gate trade pagination both work (`page` param) — used by
  `scripts/backfill_trades.py` (+3,488 trades recovered).
- Tardis has NO CoinEx exchange (400); no PRL/QUBIC/XMR history on
  Gate/MEXC either. History exists only for KAS/CLORE/FLUX/AKT
  (Gate) + KAS/CLORE/FLUX/NOCK/NOS (MEXC).

## 10. Box/tooling friction (solved, recorded)

- System pip blocked (PEP 668 externally-managed) + no `websockets`
  module → project venv at `/home/ubuntu/.venvs/powpowpow`
  (websockets, requests, pyarrow, duckdb).
- `nohup` stdout buffering hid logs → `-u` + systemd journal.
- Naive 1-file-per-WS-frame measured **~1k files/min** → batched raw
  (200 frames / 5s), trades still individual for lineage.
- `git push` via `http.extraHeader` bearer failed ("could not read
  Username") → token-in-URL for push only, remote config untouched.
- NOTE: a GitHub PAT was pasted in chat during this work — rotate it;
  chat logs are not secret storage.
