# The Architecture — How Everything Fits Together

## The stack (from the analysis)

```text
                    USER
                     │
                     ▼
              ┌─────────────┐
              │    MUSE     │
              │ goal/planner│
              │ memory      │
              │ background  │
              │ browser     │
              │ human UX    │
              └──────┬──────┘
                     │
             MCP / connectors
                     │
                     ▼
       ┌──────────────────────────┐
       │       UK BORING         │
       │     DOMAIN GRAPH         │
       │                          │
       │ requirements             │
       │ dependencies             │
       │ observations             │
       │ actions                  │
       │ outcomes                 │
       └────┬─────────┬───────────┘
            │         │
        ambiguous   deterministic
        semantic      rules
            │         │
            ▼         │
         ┌─────┐      │
         │ JEV │      │
         └──┬──┘      │
            └────┬────┘
                 ▼
          proposed transition
                 │
                 ▼
         ┌──────────────┐
         │   QP-LITE    │
         │ evidence     │
         │ actuality    │
         │ provenance   │
         │ settlement   │
         │ receipt      │
         └──────┬───────┘
                │
                ▼
         canonical history
                │
                ▼
           DATA GARDEN
```

## The four roles

| Component | Role | What it does |
|-----------|------|--------------|
| **Muse** | Runtime | Goal planning, memory, background execution, browser, human UX |
| **Jev** | Fuzzy transistor | Unstructured state → typed probabilistic decisions |
| **Sentinel** | Authority | Permission grants, credential isolation, action approval |
| **QP-lite** | Epistemic settlement | Evidence, actuality, provenance, receipt, history |

## What survives from QP

The four canonical objects:

```text
Evidence    — an observation with source and timestamp
Actuality   — TRUE / FALSE / UNKNOWN
Gate        — deterministic verification rule
Receipt     — content-addressed proof of settlement
```

Plus `Claim` as a fifth:

```text
Claim       — statement + domain + actuality
```

## What gets removed from QP

| Removed | Why |
|---------|-----|
| Grant/authority system | Muse Sentinel handles this |
| HumanTask runtime | MCP Tasks handles this |
| Orchestration/tasks | Muse traverses the workflow graph |
| Agent framework | Muse is the agent |
| Dashboard | Muse is the UX |
| Jev wrapper | Jev is independent |

## The workflow graph

Every garden workflow becomes:

```text
Goal
 └── Requirement*
      ├── depends_on Requirement*
      ├── Observation*
      ├── Decision*
      ├── Action*
      └── Outcome*
```

With edges:

```text
REQUIRES
PRODUCES
SATISFIES
BLOCKED_BY
OBSERVED_BY
VERIFIED_BY
```

## The two kinds of verification

```text
Can this action happen?
    → Muse Sentinel answers

Did the thing we care about actually happen?
    → QP-lite answers
```

**Sentinel protects effects. QP protects history.**

## The layer model

```text
L0 — Garden truth
    canonical(), evidence(), claim(), actuality(), gate(), settle(), receipt()

L1 — Observe (read-only)
L2 — Decide (Jev if semantic)
L3 — Prepare
L4 — Act (Muse + Sentinel)
L5 — Verify/readback
L6 — Learn/history
L7 — Outlet (Muse/YouTube/API)
```

## What each garden gets

```text
garden
├── schema
├── sources
├── graph
├── rules
├── decisions     # Jev
├── actions
├── verify        # readbacks
├── history       # QP-lite receipts
└── mcp
```

## The key insight

> **The graph is the product architecture.**
> **Muse is the runtime.**
> **Jev is the fuzzy transistor.**
> **MCP Tasks are the durable human/work boundary.**
> **Sentinel is authority.**
> **QP is the epistemic settlement layer.**
> **The Data Garden is the accumulated verified history produced by the whole loop.**

## The distinction that matters

```
Muse can tell us: "I submitted your application."
QP tells us: "submission attempted ≠ submission accepted ≠ application approved"
```

Only the final observation advances the corresponding claim.

That's QP.

## QP-lite as a tiny package

```text
garden-proof/
  evidence.py
  actuality.py
  claims.py
  gates.py
  receipt.py
  store.py
```

No agent. No scheduler. No HumanTask system. No dashboard. No Jev wrapper. No connector framework. No general-purpose grant/authority system.

## Sources

- QP spec: /home/box/qprivately/SPEC.md
- Influence dependency graph: /home/box/influence/dependency-graph.md
- Muse safety: https://security.muse.ai/
- MCP Tasks: https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks
- TypeSafe Jev: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Muse Spark: https://research.meta.ai/blog/introducing-muse-spark-meta-model-api
