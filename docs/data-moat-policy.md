# Moat vs re-fetchable — storage policy

Canonical doctrine lives in `backfill.md`; this file is the machine-readable
implementation. Two sentences:

> **Backfillable truth** → fetch/rebuild when needed.
> **Ephemeral truth** → archive continuously because time destroys it.

The moat is not "we store every number forever" — it is that we preserve
historical state the underlying systems do not.

## How a row is classified

`core.classify_recoverability(table_name, source_id)` returns one of:

| Value | Meaning | Layer in the manifest |
|---|---|---|
| `ephemeral` | Vanishes; archive it | `ephemeral_archive` |
| `reconstructable` | Re-fetch from a public endpoint | `canonical_backfill` |
| `derived` | Pure function of stored rows; recompute | `derived` |
| `unknown` | Not classified | `unknown` |

The tag is stamped in two places:

- `warehouse/raw/<chain>/*.json` → `recoverability` in the envelope
- `warehouse/normalized/<table>/chain=…/hour=*.jsonl` → `recoverability` per row

Registries live in `core.py`:

- `RECONSTRUCTABLE_SOURCE_PREFIXES` — `coingecko`, `kraken-ohlc`,
  `coinex-klines`, `gate-candles`, `blockchaininfo-charts`, `xmrclub-mining`,
  `qubic-rpc`, `qubic-query`, `qubic-analytics`, `doge-stats`
- `DERIVED_TABLES` — `daily_state`, `derived_signal`

Everything else defaults to **`ephemeral`**, because an unknown source is
assumed to disappear. Be conservative: adding a prefix means we are willing
to lose it later.

Rows written before the tag existed still classify correctly on read —
`manifest.py` falls back to the same registry using the row's `source_id`.

## What is actually on disk (2026-09-25)

| Layer | Files | Rows | Bytes |
|---|---:|---:|---:|
| `ephemeral_archive` | 50,155 | 57,378 | 228.9 MB |
| `canonical_backfill` | 256 | 17,163 | 13.2 MB |
| `derived` | 2 | 43 | 44 KB |
| `knowledge` | 54 | — | 75 KB |
| `unknown` | **0** | — | — |

Reproduce with `python3 manifest.py`. Before this change the same run reported
`unknown: 744,429 files / 5.6 GB` because `manifest.py` hard-coded
`/home/box/powpowpow/warehouse` and only recognised directory prefixes that
do not exist in this tree.

## Keep archiving (moat)

- SafeTrade L2 books, trades and ticks — once WS updates vanish the book is gone.
- Our own observations: `receive_time`, `poll_id`, coverage, gap events.
  Nobody can reconstruct *when we saw it*.
- `pool_snapshot` — `blockchain.info/pools?timespan=5days` is a rolling window;
  historical distribution is not re-fetchable. P2Pool miner counts are
  snapshot state.
- Entity and label knowledge in `warehouse/knowledge/` — labels change.

## Fetch instead of store

- OHLCV (`coingecko`, `kraken-ohlc`, `coinex-klines`, `gate-candles`) —
  excellent backfill APIs, many providers.
- Chain history (`blockchaininfo-charts`, `xmrclub-mining`) — the chain is
  the archive.
- Qubic ticks/epochs/computor sets (`qubic-rpc`, `qubic-query`) — archive
  Query API.
- BTC trade zips — already handled correctly: download to tmp, parse, delete
  (`scripts/backfill_trades.py:11`).

These are cheap to keep (13.2 MB today) but they are the first candidates to
prune if R2 spend or local disk pressure grows.

## Derived

`daily_state`, `derived_signal`, factors and `*_analytics` are recomputable
from raw. Keep them — they are KBs and they are what the dashboard reads —
but never treat them as evidence without their `raw_event_id` or
`emission_source`.

## Storage bounds

- Local `warehouse/raw` is pruned after 24 h by `pow-r2-upload.service`
  (`--retention-hours raw=24`), and **only** after a fresh remote `HEAD`
  confirms size + SHA-256. `normalized` 30 h, `parquet` 168 h, `chains/`
  never deleted.
- Collectors pause below `POW_MIN_FREE_BYTES` (2 GiB) instead of filling the disk.

## Ticker rows

SafeTrade `global.tickers` covers every listing on the venue. Storing the
bundle wholesale cost 29,338 bytes/row and nothing read it (every consumer
keys on `symbol`, which the bundle row did not have). `tracked_ticker_rows()`
in `collectors/l2_archival.py` now emits one row per tracked market:

- 644–688 bytes/row (**~98% smaller**)
- `symbol` present, so `build_daily_state` now populates `last_price` and
  `day_volume` for SafeTrade markets — previously those STATE fields were
  empty for this venue.

## MCP outlet

`mcp_server.py` exposes 13 read-only tools over stdio. It was dead on this box:
`opencode.json` pointed at `/home/box/powpowpow/.venv/bin/python` and the
installed `mcp` 2.1.1 no longer provides `mcp.server.fastmcp`. Both fixed —
it now imports `fastmcp` (3.4.7) and runs as
`/usr/bin/python3 /root/powpowpow/mcp_server.py`.

So agents query the warehouse through MCP instead of reading files: the moat
stays in the store, everything re-fetchable can be fetched at read time.
