# Qubic burns + miner-data pipeline — spec (powpowpow)

Goal: every supply/burn claim (like "net −1.35T/week") recomputable from
our warehouse. No number without provenance.

## Validation protocol (for any external claim)

1. **Rederive from independent sources.** Transaction burn: Query API
   BURNING events per tick vs analytics.qubic.li vs stats-service
   burnedQUs. All three must agree within tolerance.
2. **Pin definitions.** "Transaction burn" = contract execution fees +
   explicit burns? Transfers don't burn. List exactly which event types
   count, per qubic JSON-RPC tx-type table (type 8 BURNING, 9
   DUST_BURNING, 12 CONTRACT_RESERVE_DEDUCTION).
3. **Check the denominator.** −1.35T/week ÷ circulating = ?%. Verify
   which supply figure is used (circulating vs total vs cap). The viral
   −0.76% implies ~177T — reconcile against official ~138T circulating
   before repeating it.
4. **Window sensitivity.** 7-day avg vs epoch-aligned vs 30-day. Spikes
   must persist across ≥2 epochs before "structural" is claimed.
5. **Protocol vs actual.** Scheduled max burn (775B/week post-227) vs
   measured (thread claims 771B — i.e. Supply Watcher running just under
   ceiling, consistent with dynamic-burn design).

## New collectors (powpowpow/collectors/)

- `burn_ledger.py` — Query API BURNING/DUST_BURNING/CONTRACT_RESERVE_
  DEDUCTION events per tick → `burn_event` rows (tick, epoch, type,
  amount, tx). Cadence: hourly catch-up; epoch week is the grain.
- `epoch_burn_summary` (derived, weekly) — per epoch: gross (1T),
  protocol-burn-max (schedule), protocol-burn-actual (measured),
  tx-burn total, net change, net % of circulating.
- `ann_snapshot.py` — mirror annexplorer API: `/api/v1/epochs`
  (solutions, verification fails, core versions), `/api/v1/computors`
  (rank, epochs, solutions, fails). Summaries only, never full solution
  dumps. Cadence: 6h.
- `fee_burn.py` — oracle query fees + SC execution fees per epoch from
  Query API / stats service → `fee_burn` rows. This is the usage-demand
  leg; currently zero coverage.

## New normalized tables

- `burn_event`, `epoch_burn`, `ann_epoch`, `ann_computor`, `fee_burn`
- Every row: raw_event_id lineage, UTC event_time + observed_at,
  source_role (canonical/derived), per core.py conventions.

## Derived metrics (qubict, then site)

- net_supply_change_weekly (+ % of circulating)
- burn_deviation (actual vs scheduled max — Supply Watcher behavior)
- tx_burn_trend (7d/30d MA, spike flags at 2σ)
- computor reliability score, verification-fail trend
- fee-burn revenue (usage demand — the spark metric)

## Site panels (crypto.pow.systems Qubic tab)

- Supply strip: gross → protocol burn → tx burn → net/week with signs.
- Burn-deviation chart (actual vs schedule by epoch).
- Computor leaderboard top-10 + epoch verification strip.
- Freshness badges per panel (stale data must look stale).

## Sequencing

1. burn_ledger + epoch_burn (validates the viral thread end-to-end).
2. ann_snapshot (computor data, uncontested lane).
3. fee_burn (usage leg — hardest, most valuable).
4. Site panels read the tables. Content (powvid) reads the metrics.
   Never the live API directly.
