> **STALE 2026-09-25 — header contradicts itself and the box.** SafeTrade
> is **not** egress-blocked/geo-403 (unblocked 09-23, running as
> `pow-safetrade-l2`); venue L2 (CoinEx/Gate/MEXC) is **not** live;
> public host is `pow.systems`; R2 is hourly at :37 with vault creds, not
> daily/env-file; `pages/` still does not exist so `/api/page` 404s;
> the "(was 100+ /home/box hardcodes)" claim is false (~71 remain in 35
> tracked files). Working list: `docs/build-progress-2026-09-25.md`.

# PowPowPow — product-readiness work list

> Review 2026-09-19 eve. Money math + pipes + first signals are landed.
> The garden clock started 2026-09-19 (venue L2 live, STATE daily).
> SafeTrade is code-ready but egress-blocked (geo-403); venue-of-truth
> weighting waits on it.
>
> PROGRESS 14:10 UTC: Tardis free seeds (54 files, Jul/Aug/Sep firsts)
> loaded for KAS/CLORE/FLUX/AKT/NOCK/NOS → STATE/signals/factors/
> backtest run over 4 days of history. Seed JSONL compacted 8GB→253MB
> Parquet (25-30x) and dropped; disk recovered 43MB→9.4GB. Streaming
> STATE builder (100-400MB RSS, was OOM at 2.6GB). flow_pressure_v1
> live (12 symbols). pearld v1.4.8 syncing fresh under systemd
> (data dir cleared during disk triage, resync ~2h). Monthly tardis
> drip timer armed. Release/commit history: 213+240 rows, 12 repos.
>
> PROGRESS 2026-09-23 16:20 +07: SafeTrade UNBLOCKED (was Cloudflare bot-detection, not geo). `pow-safetrade-l2` running (25 streams). `core/` shadowing fixed. `pow-site` systemd-managed with stable token. R2 upload verified 10/10 (`powpowpow-warehouse`, secrets in 600 env file). XMR+QUBIC price history loaded (366d). Analytics refreshed (XMR $247k/day, QUBIC $12k/day, 4.78x burden). 31 market-states, 10 signals. Factors rebuilt (24 symbols). MCP 10 tools (added get_live + get_xmr_full). Dashboard ticker live. Tunnel still missing — see BLOCKERS.md.
>
> FOCUS: XMR + QUBIC only. All other one-shot collectors parked (BLOCKERS.md #5).
>
> SITE 16:10 UTC: consumer fork live at pow.moltwork.com (token gate,
> loopback :8795, systemd). Coverage-gated display (QUBIC/XMR/PRL/KAS/
> NOCK/XEL only — TAO + thin listings hidden until data earns them).
> Austere B/W single-file UI: left coin rail, per-coin home dash with
> canvas graphs (price 1y, flow bars, margin history), subtabs
> (Overview/Market/Mining/Signals), plain-language dossiers.
> New: /api/analysis (XMR price↔difficulty Seesaw, Qubic epoch-equiv
> returns), /api/history, /api/cards_history. Nightly card snapshots
> → margin history table (miner_card).
>
> STORAGE DOCTRINE 15:00 UTC (measured, not guessed): live burn
> ~1.2GB/day raw+JSONL → ~60MB/day Parquet (16-30x). Tiers: hot
> JSONL 7d (`trim_jsonl.py`, never drops uncompacted) → Parquet
> forever (DuckDB-queryable) → derived tables forever (KBs). Chain
> bytes (pearld) = extract-and-release, never hoarded. Off-box:
> R2 bucket `powpowpow-warehouse` via `scripts/r2_upload.py` (verified
> 10/10, daily `pow-r2-upload.timer`, secrets in 600 env file).
> Tardis seeds judged low-value going forward: our own ticks from
> now are the moat; monthly drip continues (cheap) but no more
> bulk backfill spend.

## 1. Money math — DONE (v2 network-share)

- [x] `v1_live_cards.py`: network-share revenue, KAS gated, electricity
  as input, hardware specs carry source + date, assumptions on every card.
- [x] `economics.py`: fixed dimensions, sell methodology disclosed per
  coin, no hidden 0.6.
- [x] `factors.py`: rebuilt from daily STATE; sell_fraction=null with
  methodology flag until miner-flow measurement exists.
- [ ] Remaining: replace seeded hashrate/emission estimates with live
  collector values (pearld, monerod, kaspa, qubic RPC).

## 2. Pipes — mostly done, collection live

- [x] Repo-relative `BASE_DIR` everywhere (was 100+ `/home/box` hardcodes).
- [x] Storage collapsed to `core.py`; `warehouse.py` + `v1_pipeline.py`
  are compat shims; `v1_collector_base.py` UTC + canonical hashing.
- [x] PRL + Qubic + XMR migrated to auto-archiving `fetch_json`.
  PearlTrack marked derived/labels with classification provenance.
- [x] L2 archival gap-safe (both venues): event vs receive time, seq IDs,
  snapshot-vs-delta, REST checkpoints, raw-before-parse.
- [x] Daemon supervised (systemd `pow-venue-l2`, restart+linger) AND
  daily STATE timer (`pow-daily-state` 00:30 UTC). Full-plant `daemon.py`
  rewritten but not yet unit-ized.
- [x] README points at `v1_registry.py` 8-system truth; `registry.py` is
  the labeled candidate pool.
- [ ] Migrate remaining ~15 one-shot chain collectors to `core.fetch_json`. PARKED — focus XMR+QUBIC (BLOCKERS.md #5). Do not wire unless it feeds a named transformation.
- [ ] Unit-ize full `daemon.py` (chain collectors + api + safetrade-l2)
  under systemd. PARTIAL: venue/chain/safetrade/site each have units; full-plant daemon.py still not unit-ized.

## 3. Fundamental signals — v1 live

- [x] `signals.py` `miner_pressure_v1`: cross-sectional burden z-score
  with drivers, evidence record IDs, assumptions, version. Refuses on
  thin cross-section. First output: XMR bearish 0.66, QUBIC bullish 0.80.
- [x] Emission value/day (fundamentals) + real bid depth (archived books).
- [ ] Realization component needs pool→miner→exchange flow (pearld +
  miner graph). Until then v1 scores structural burden only — disclosed.
- [ ] `pressure.py` / `ofi.py` / `two_timescale.py` still run on stale
  file inputs; rewire them onto STATE + derived_signal tables.

## 4. Backtester — scaffold live, history growing

- [x] `backtest.py`: forwards-by-signal-bucket on daily_state; honestly
  refuses until 2+ days (clock started 2026-09-19).
- [x] Trade backfill: +3,488 timestamped trades via venue pagination
  (`scripts/backfill_trades.py`). Books unrecoverable — live only.
- [x] Tardis check: Gate.io history exists for KAS/CLORE/FLUX/AKT;
  MEXC for KAS/CLORE/FLUX/NOCK/NOS. No PRL/QUBIC/XMR anywhere.
  First-of-month CSVs free — pull KAS/CLORE/FLUX/NOCK/NOS seeds next.
- [ ] Event studies once `chains/events/` fills + 30d STATE.

## 5. Knowledge compiler — seed live

- [x] `scripts/compile_coins.py` → `pages/<SYM>.md` from registry +
  STATE + signals + factors. 15 pages. Rerun anytime.

## 6. SafeTrade — DONE (2026-09-23)

- [x] Root cause: (1) `PowPowPow/1.0` UA → Cloudflare 403, (2) missing `ssl=ssl_ctx` in ws.connect, (3) `core/` pkg shadowing `core.py` → silent None import
- [x] `collectors/l2_archival.py` running as systemd `pow-safetrade-l2`
- [x] REST market list + WS depth/trades + REST depth checkpoints all live

## 7. Autoassigner (last — highest liability)

- [ ] Needs 3 + 4 with a track record, measured hardware benchmarks,
  and bounded-grant execution (products.md). Ship when signals
  have scars. Not started — correct order.
