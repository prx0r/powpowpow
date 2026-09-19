# XMR — compiled 2026-09-19T12:00:51.022118+00:00

*Monero — pow-privacy*

## Identity
- physical_resource: CPU
- resource_type: cpu_mining
- supplier_type: miner
- telemetry: monerod RPC + pool APIs
- marginal_cost: Power + CPU depreciation
- reward: Block reward (0.6 XMR tail)
- supply_response: CPU entry/exit
- price_source: CEX (Kraken, etc)
- mining_algo: RandomX (CPU-optimized)
- useful_output: None (pure consensus security)
- hardware: CPU (RandomX)
- consensus: RandomX
- daily_emission: 432
- github: monero-project/monero

## Current economic state (latest STATE per venue)
- coinex 2026-09-19: mid_close=None spread_med=None trades=179 gaps=0

## Derived signal
- miner_pressure miner_pressure_v1: bearish (0.657) on 2026-09-19
- drivers: emission_usd_day=254,178; bid_notional_20_sum=8,425; burden=30.17x; spread_bps_med=0.2
- assumptions: sell_fraction unmeasured: burden is structural creation load, not observed miner selling; bid_notional_20 is top-20-level resting notional, not full book; cross-venue sum mixes CoinEx+Gate books; venue-of-truth weighting arrives with SafeTrade egress

## Factor row
- issuance_usd_24h: 254178.0
- burden_vs_book: 30.17
- issuance_to_volume: 72.534
- trade_notional_24h: 3504.26
- venues: ['coinex']

*Projection of the garden at 2026-09-19T12:00:51.022118+00:00. Regenerate with `scripts/compile_coins.py`. Provenance: warehouse record IDs.*
