# PRL — compiled 2026-09-19T12:00:51.022118+00:00

*Pearl — useful-work*

## Identity
- physical_resource: H100/H200 GPU
- resource_type: gpu_compute
- supplier_type: miner
- telemetry: pearld RPC + PearlTrack enrichment
- marginal_cost: Power + hardware amortization
- reward: Mining revenue (PRL/day)
- supply_response: GPU entry/exit based on profitability
- price_source: SafeTrade L2
- mining_algo: Matrix multiplication (cuPOW)
- useful_output: AI inference (LLM serving)
- hardware: GPU (NVIDIA CUDA)
- consensus: Proof-of-Useful-Work (PearlHash)
- max_supply: 2100000000
- daily_emission: 500000
- github: pearl-research-labs/pearl

## Current economic state (latest STATE per venue)
- coinex 2026-09-19: mid_close=None spread_med=None trades=113 gaps=0
- gate 2026-09-19: mid_close=0.119 spread_med=16.820857863750366 trades=12 gaps=0

## Derived signal
- miner_pressure miner_pressure_v1: neutral (0.279) on 2026-09-19
- drivers: emission_usd_day=59,725; bid_notional_20_sum=10,652; burden=5.61x; spread_bps_med=16.8
- assumptions: sell_fraction unmeasured: burden is structural creation load, not observed miner selling; bid_notional_20 is top-20-level resting notional, not full book; cross-venue sum mixes CoinEx+Gate books; venue-of-truth weighting arrives with SafeTrade egress

## Factor row
- issuance_usd_24h: 59725.0
- burden_vs_book: 5.607
- issuance_to_volume: 52.058
- trade_notional_24h: 1147.27
- venues: ['coinex', 'gate']

*Projection of the garden at 2026-09-19T12:00:51.022118+00:00. Regenerate with `scripts/compile_coins.py`. Provenance: warehouse record IDs.*
