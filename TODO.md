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
> PROGRESS 14:30 UTC: XMR stack (localmonero + xmrchain fees/mempool +
> p2pool miners/hashrate) and Qubic demand totals (2.015B txns via
> analytics) wired into chain poller. KAS supply-delta FIXED to rate
> form (was 5-min-delta bug); AKT supply sampling live. emission.py
> schedules for CLORE/FLUX/NOS/TAO/NOCK. required_flow_v1 live
> (9 signals; QUBIC bullish 0.91 coverage 1.15, XMR bearish 0.00).
> MCP stdio server verified end-to-end (6 tools, live tables).

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
- [ ] Migrate remaining ~15 one-shot chain collectors to `core.fetch_json`.
- [ ] Unit-ize full `daemon.py` (chain collectors + api + safetrade-l2)
  under systemd once SafeTrade egress exists.

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

## 6. SafeTrade (blocked on egress, ready to run)

- [x] `collectors/l2_archival.py` gap-safe, replay-verified
  (parse/gap/discovery/backfill-proof). Needs unblocked box or proxy;
  rsync `warehouse/` back here.
- [x] Vault creds verified retrievable; signed requests still geo-403
  (IP-level block, auth can't fix).

## 7. Autoassigner (last — highest liability)

- [ ] Needs 3 + 4 with a track record, measured hardware benchmarks,
  and bounded-grant execution (products.md). Ship when signals
  have scars. Not started — correct order.
