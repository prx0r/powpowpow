# What Qubic mining solutions actually are

Normal machine learning works like school: humans design the brain once,
then training adjusts connection strengths (weights) until mistakes stop.
The brain's shape never changes.

Qubic mining mutates the school itself. Each submission is a different
theory of how learning should work — different structures, different
plasticity — scored against the epoch's task.

## Anatomy of one solution (per ANN explorer `/api/v1/solutions`)

- **annGenomeId** (`sha256:…`): fingerprint of the trained network's
  weights. The solution's DNA.
- **nonce + miningSeed**: the randomness behind that training run —
  proof this attempt happened, same role as a PoW nonce.
- **computorId**: who submitted it. Histories accumulate per computor.
- **coreVersion / parameterSetId**: which task definition it answers
  (e.g. `epoch-232-v1.305.0`).

## Scoring and verification

Each epoch publishes a scoring rule (currently `lower_is_better`,
maximum rule). Best scores win rewards. Then solutions get
*re-checked*: epoch 232 saw 921,492 submitted, 6 failed; epoch 231 saw
1,573,224 submitted, 28 failed. Failed = claimed score didn't
reproduce (bad training, wrong params, or cheating attempt).

## Why "reconstructed genomes" matter

The explorer rebuilds actual weight sets from seeds, so solutions are
auditable, not take-our-word hashes. That plus per-computor histories
(rank, epochs, lifetime solutions, failures) is what makes reliability
scoring possible downstream.

Sources: annexplorer.jetskipool.ai `/api/v1/epochs`, `/api/v1/solutions`,
`/api/v1/computors` (probed 2026-09-26).
