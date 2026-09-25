# QUBIC structure note — measured numbers, 2026-09-25

Neutral metric read-out. No recommendation, no direction: this records what
the warehouse measured and what it refused to measure. Sources are named per
row; every figure is reproducible from `chains/`, `warehouse/` and
`scripts/qubic_analytics.py`.

---

## 1. What the burn actually is

The ~78% figure is a **scheduled issuance haircut** (post-Epoch-227), not
usage-driven fee burn.

| Metric | Value | Source |
|---|---|---|
| Gross issuance | 1,000,000,000,000 QU/week | `network_state.gross_per_week` |
| Burn ceiling | 0.775 | `POST_227_MAX_BURN` (`scripts/qubic_analytics.py`) |
| Observed vs schedule | **0.996×** | `burn_deviation_vs_schedule` |
| Burst at epoch start | **99.83%** of epoch burn | `burn_concentration_at_epoch_start` |
| Trickle between events | 4.75B QU per 1e6 ticks | `burn_trickle_rate` |
| Snapshot intensity | 0.0 QU per 1e6 ticks | `burn_intensity_snapshot` |
| Epoch burn total | 771,928,433,743 QU | `burn_epoch_total` (event logs, logType=8) |
| Cumulative burned | 54,433,860,634,895 QU | `rpc.qubic.org/v1/latest-stats` |

Burn fires on schedule, within 0.4% of specification, and essentially never
outside that burst — so it scales with the schedule, not with price or usage.

**Consequence:** net issuance is still positive. Gross 1T QU/week less the
0.775 haircut leaves **225B QU/week = 32.14B QU/day**, worth **~$14.0k/day**
at the observed SafeTrade price.

| Supply effect | Value |
|---|---|
| Net issuance | +11.7T QU/year |
| Circulating supply | 177,566,139,365,105 QU |
| Implied net dilution | **+6.6%/year** |
| Market cap (circulating × price) | ~$77.6M |
| Annualised net issuance | ~$5.1M (6.6% of cap) |

---

## 2. Computor / miner economics

| Metric | Value | Source |
|---|---|---|
| Gross per epoch | 1T QU | epoch allocation table |
| Effective per epoch (post-burn) | 225B QU | `computor_economics` |
| Mineable per epoch | 181.64B QU | `POST_227_MINIMUM_MINEABLE_PER_WEEK` |
| Computors | 676 | `network_state.computors` |
| Reward per computor per epoch | 268,698,225 QU | `computor_economics` |
| Reward per computor per day | 38,385,461 QU | derived |
| USD value per computor per day | **~$16.7** | QU price × reward |
| Set churn per epoch | 225 in / 225 out / 451 retained = **33%** | `computor_churn` |
| Epoch progress / tick rate | 0.01 / 1.48 | `network_state` |
| Epoch tick quality | 98.6% (last 10k: 99.5%) | `epoch_tick_quality` |

Reward is gross of hardware, availability and power cost; no cost measurement
exists in this repo, so no margin figure is published.

---

## 3. Market structure (SafeTrade, one venue)

| Metric | Value |
|---|---|
| Price | $4.335e-07 (SafeTrade mid) |
| Percentile of range | 5.8th |
| 365d-range low / date | $2.594e-07 / 2026-09-15 |
| Top-20 bid depth (chain, all pairs) | **$4,103** |
| Top-20 ask depth (chain, all pairs) | $295,847 |
| 24h traded notional | $17,595 |
| 24h buy / sell notional | $3,488 / $14,108 (4.0×) |
| Trade count | 89 |
| Median spread | ~2,181 bps (USDT pair ~297 bps) |
| `burden_vs_book` | **3.40×** |
| `issuance_to_volume` | 0.792 |
| Exchange reserve | 29,299,092,672,196 QU (16.5% of circulating) |
| Exchange netflow (window) | −518,657,766 QU |
| Wealth concentration | gini 0.8745 |
| Exchange share of rich list | 0.0007 |
| Measured active addresses (window) | 91 |
| Transfer rate | 625/min |
| Active address growth | 0.0 |

`burden_vs_book` = one day of issuance ÷ resting top-20 bids. The depth above
is **chain-aggregated across all USD-converted pairs** as of this session; the
single-pair figure previously shown ($319) omitted the QUBIC/BTC book.

---

## 4. What the model refuses to compute

| Refusal | Reason |
|---|---|
| `sell_fraction` | "miner exchange flow not yet observed" — unmeasured, disclosed in `signals.py` |
| `price_hashrate_divergence` | no hashrate history for a tick-based chain |
| `activity_vs_price_corr` | zero variance inside window |
| `epoch_tick_quality_vs_price_corr` | fewer than 30 overlapping observations |
| `burn_intensity_snapshot` (0.0) | burn occurs as a scheduled burst; snapshot window between events |

Because `sell_fraction` is unmeasured, `miner_pressure` is a **structural
creation-load score versus absorbable liquidity**, not an observation of
selling.

---

## 5. Caveats on these numbers

1. **Single venue.** Depth, volume and flow are SafeTrade. XMR's and BTC's
   SafeTrade books are $29 and $168 deep, which is why `signals.SECONDARY_DEPTH_VENUES`
   now refuses them there — and why the QUBIC figures should be read as
   SafeTrade microstructure, not the whole market.
2. **Emission confidence** is `medium-low`; the schedule-derived number is
   labelled `projected maximum effective emission`.
3. **`price_range_365d.high_date`** is 2024-12-03, outside a 365-day window —
   label/window mismatch worth an audit item.
4. **Cross-sectional labels** (bearish/neutral/bullish) are z-scores against
   four to five other chains. They describe relative position in this
   cross-section only, and change as coverage changes.

---

## 6. Reproduce

```bash
python3 collectors/qubic_stats.py --once     # burn + stats
python3 scripts/qubic_analytics.py           # emission, supply curve, computors
python3 signals.py --date $(date -u +%F)     # burden + refusals
python3 factors.py --date $(date -u +%F)     # chain rows, USD-converted
```
