# PowPowPow — product-readiness work list

> Review 2026-09-19. The pressure equation is correct algebra over empty
> inputs. Fix the money math first; everything compounds on it.

## 1. Money math (blocks everything)

- [ ] `v1_live_cards.py`: replace magic `yield_per_th` / `yield_per_h`
  constants with network-share revenue
  (`rig_hashrate / network_hashrate × emission × price`). KAS yields
  (`50`) currently price a single rig at $3.3B/day — recompute or remove.
- [ ] `economics.py`: revenue formula missing network-share term; fix
  dimensions before any signal reads it.
- [ ] Sell methodology per coin to replace hardcoded `sell_fraction`
  (0.5/0.6/0.7 across `economics.py` / `factors.py`). State assumptions
  on every signal until miner-flow measurement exists.
- [ ] Electricity as input, not `ELECTRICITY = 0.10` constant.
- [ ] Hardware specs measured (hashrate/power/cost with source + date),
  not specced.

## 2. Pipes (blocks time series)

- [ ] Replace all `/home/box/powpowpow` paths (30+ files) with
  repo-relative `BASE_DIR`. Nothing runs off-box until this lands.
- [ ] Collapse storage to `core.py` only; delete/redirect `warehouse.py`
  + `v1_pipeline.py` duplicates and naive-timestamp
  `v1_collector_base.py`.
- [ ] Migrate every collector to auto-archiving `fetch_json`
  (only clore done). PRL first (own pearld canonical, PearlTrack labels).
- [ ] L2 archival gap-safe: exchange event time vs receive time,
  sequence IDs, snapshot-vs-delta, REST checkpoints.
- [ ] Daemon fixed + running so warehouse fills. Backtester needs
  ~90 days of daily factors; the clock starts when this ships.
- [ ] README 16-coin universe → `v1_registry.py` 8 systems (PR1 item 12).

## 3. Fundamental signals (no TA, confidence bands printed)

- [ ] Emission value/day per coin from chain data.
- [ ] Real bid depth from archiving order book.
- [ ] Pressure ratios (creation / realization / absorption) with
  assumptions on the signal. Content MCP already emits this shape.

## 4. Backtester (after warehouse fills)

- [ ] Daily factor time series (not snapshots) → event studies on
  halvings / difficulty changes / listings. Candle replay is out
  of scope; fundamentals only.

## 5. Autoassigner (last — highest liability)

- [ ] Needs 3 + 4 with a track record, measured hardware benchmarks,
  and bounded-grant execution (products.md). Ship when signals
  have scars.
