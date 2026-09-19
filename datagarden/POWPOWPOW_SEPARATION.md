# PowPowPow — Separate Project

PowPowPow is a separate project from UKBoring/Datagarden.

## Relationship

- **Datagarden** = UKBoring (UK economic opportunity engine)
- **PowPowPow** = Crypto mining economics data garden

Both share the same Data Garden primitives (core/ and shared/), but they are independent projects with separate repos, separate collectors, and separate MCP servers.

## Shared Code

The Data Garden framework lives in both repos:
- `/home/box/datagarden/datagarden/` — for UKBoring
- `/home/box/powpowpow/datagarden/` — for PowPowPow

Core primitives (Observation, Entity, Source, DerivedFact, QualityGate, Storage, Receipt, Manifest) are garden-agnostic and shared.

PowPowPow-specific code (schema.py, entities.py, warehouse.py) is already configured for mining data.

## Do NOT

- Do not add powpowpow-specific logic to datagarden
- Do not add UK-specific logic to powpowpow
- Do not import from each other's collectors or MCP servers
- Do not share API keys between projects

## DO

- Share core/ primitives (they're garden-agnostic)
- Share conceptual docs (thesis.md, formula.md, ideology.md)
- Keep both repos in sync on core/ changes
- Each project owns its own collectors, MCP tools, and data

## Status

- **PowPowPow**: 12/12 MCP tools real (100% real data)
- **Datagarden**: 37/89 MCP tools real (42% real data)
- **Shared primitives**: Working in both repos
