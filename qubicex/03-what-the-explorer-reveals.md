# What the ANN explorer reveals (read 2026-09-26)

Source: annexplorer.jetskipool.ai (Jetskipool pool explorer). Frontend is
a JS shell; the API underneath is open: `/api/v1/epochs`,
`/api/v1/epochs/{n}`, `/api/v1/solutions`, `/api/v1/computors`,
`/api/v1/live/tick-info`, `/api/ui/qubic-price`.

## Four reads on the operation

1. **Real weekly loop, not a demo.** ~1M solutions/epoch, every epoch,
   tagged to computor + core version + parameter set. Core versions
   advance across epochs (v1.304.0 → v1.304.1 → v1.305.0): versioned R&D,
   visible from outside.
2. **Quality control is load-bearing.** Every solution re-checked
   (232: 6 failed / 921,492). They expect adversaries, not volunteers.
3. **The leaderboard is a reputation system.** 100-epoch streaks,
   lifetime counts, zero-failure records (rank #1: 100 epochs, 66,080
   solutions, 0 failed). Histories only make sense if they matter later
   (work weighting, payouts).
4. **Transparent objective function.** Public scoring rule
   (`lower_is_better`, maximum). Outsiders can audit whether winners
   deserved it.

## Doctrine note

Third-party API, no stated terms: mirror what we need into the
warehouse, never depend on it live. Archive or lose it.
