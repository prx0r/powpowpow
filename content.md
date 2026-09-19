# PowPowPow — Content System Architecture

## Core Principle

Content is another sensor/actuator loop on top of the dataset.

Each video is not just "content." It is an **experiment** containing hypotheses about:
- which event/metric matters
- which framing makes it interesting
- which causal explanation people care about
- which visual/chart holds attention
- which segment loses them

YouTube analytics becomes the feedback signal.

---

## The Content Loop

```
PowPowPow data
→ detect interesting events
→ generate candidate interpretations
→ choose content hypothesis
→ script/video
→ publish
→ collect analytics
→ attribute response to script segments/features
→ update content model
→ repeat
```

---

## Content as Structured Data

### Content Experiment Schema

```text
content_experiment

video_id
created_at
published_at

source_events[]
source_metrics[]

thesis
hook
title_hypothesis
thumbnail_hypothesis

segments:
  0-10s   hook
  10-35s  setup
  35-80s  data
  80-130s explanation
  130-180s implication

claims[]
charts[]
entities[]
topics[]
tone
complexity
novelty_score
```

### Content Outcome Schema

```text
content_outcome

impressions
ctr

views
avg_view_duration
avg_percentage_viewed

retention_curve
rewatches
likes
comments
shares
subs_gained

traffic_source
viewer_geography
device
```

---

## Retention Curve Analysis

The retention curve is the most interesting signal because it evaluates individual sections, not just whole videos.

Example:
```text
00:00  100%
00:10   82%
00:35   79%
00:50   91%  ← people replayed chart
01:15   65%
01:35   38%  ← explanation lost them
```

Agent reasoning:
> The resource-premium chart generated a rewatch spike.
> The detailed pool-mechanics explanation caused abandonment.
> Next video should introduce the resource anomaly earlier and compress the mechanics.

---

## Event Detection + Content Selection

### Daily story candidates from:

```
PowPowPow hard data (what moved)
+
project/news/event feeds (why it might have moved)
+
market anomalies (what's unusual)
=
ranked stories
```

### Example:

Hard data detects:
```
A: PRL resource premium +74%
B: Akash H100 availability -22%
C: XMR hashrate record
D: KAS miner margins -31%
E: QUBIC computor concentration shift
```

Event layer detects:
```
Qubic release v1.304.1 (Sep 16)
Quantus weekly update (mining changes)
```

Content agent scores candidates:
```
ContentValue = f(
  EventNovelty,
  EconomicMagnitude,
  CausalClarity,
  HistoricalAudienceInterest,
  Visualizability,
  Timeliness
)
```

Chooses:
> "AI GPUs just became more valuable somewhere else — and Pearl miners haven't moved yet."

---

## Content Hypotheses

Each script is itself a hypothesis:

```text
content_hypothesis:
  viewers will care about PRL profitability
  IF framed as competition for scarce H100s
  MORE than if framed as a crypto mining update

prediction:
  CTR > channel median
  30s retention > 72%
  resource-premium chart produces rewatch peak
```

After publishing:
```text
result:
  CTR = 8.1%
  30s retention = 76%
  chart segment retention +9%
```

Hypothesis gains weight (or fails).

---

## Content Primitives

Reusable script/visual components:

```text
content_primitives

HOOK_SCARCITY
HOOK_SURPRISE
HOOK_DOLLAR_VALUE
HOOK_CONTRARIAN

VISUAL_SEESAW
VISUAL_RESOURCE_FLOW
VISUAL_MINER_MARGIN
VISUAL_SUPPLY_CURVE

EXPLANATION_ANALOGY
EXPLANATION_CAUSAL_CHAIN
EXPLANATION_COUNTERFACTUAL
```

Each video is a composition. Over hundreds of videos estimate:
```
E[retention uplift | primitive]
```

Discoveries like:
- `VISUAL_RESOURCE_FLOW` improves 60–90s retention by 8%
- Dollar-value hooks work for mining stories; AGI framing works better for compute-scarcity stories

---

## Content + Research Reinforcement

Audience feedback identifies which data transformations are cognitively useful.

Raw metric:
> PRL H100 allocation wedge = +$1.73/hour

Nobody cares.

Transform:
> An H100 currently earns 63% more mining Pearl than renting elsewhere.

That performs well.

That transformation becomes:
- a content primitive
- a useful dashboard metric
- potentially a trading/research factor

The stack:
```
RAW WORLD
↓
PowPowPow observations
↓
Seesaw transforms
↓
research hypotheses
↓
content hypotheses
↓
human attention/feedback
↓
better representations
↓
better transforms
```

---

## News/Event Layer

### Source Map

**PRL**
- GitHub releases + commits
- Pearl official announcements
- Pool announcements
- SafeTrade listing/status changes

**QUBIC**
- Qubic blog
- GitHub releases
- Governance proposals
- All-Hands recaps
- Epoch/software changes

**QUAN**
- Quantus weekly blog
- GitHub PRs/releases
- research.quantus.com
- Miner releases

**XMR**
- getmonero blog
- GitHub releases
- Meeting logs
- CCS/proposal activity
- Major pool/software releases

**KAS**
- rusty-kaspa releases
- KIPs
- Kaspa R&D channels/forum
- Protocol activation events

**CLORE**
- Changelog
- Official blog
- Marketplace/tokenomics announcements
- API changes

**AKT**
- Official blog
- GitHub provider/node releases
- Governance
- Provider/network updates

**NOS**
- Official blog
- GitHub
- New model/workload announcements
- Host/provider campaigns

### Project Event Schema

```text
project_event

event_id
network_id

published_at
observed_at

source_type:
  github_release
  github_commit
  blog
  governance
  exchange
  social
  protocol
  research

title
body_summary
source_url

event_tags:
  mining
  tokenomics
  compute
  hardware
  software
  listing
  protocol_upgrade
  research
  partnership
  security

entities[]
numbers_extracted[]

importance_score
novelty_score
confidence

source_hash
```

---

## GitHub as Primary Automated Primitive

Collect:
- new releases
- tags
- merged PRs
- commits
- issues marked release/security
- repo activity acceleration

Derive:
- code_change_intensity
- release_frequency
- files_changed
- miner-related commit count
- consensus-related commit count

---

## Social/X as Fast-Alert Layer

Store separately with lower confidence:

```text
social_event
  account
  posted_at
  text
  links
  engagement_at_capture

source_confidence = low/medium
```

Flow: social post flags event → agent checks GitHub/blog/on-chain data → PowPowPow evaluates actual effect.

---

## Daily Content Process

```
1. ingest project events
2. ingest market/resource data
3. detect anomalies
4. join events ↔ anomalies
5. rank stories
6. generate charts
7. generate script candidates
8. you choose what you actually find cool
```

---

## Exploration vs Exploitation

Contextual bandit for content format:
```
Score = ExpectedPerformance + λ × Uncertainty
```

80-90% exploit known-good structures.
10-20% test new formats.

Otherwise channel converges into repetitive slop.

Initial optimization: what you personally find interesting, not YouTube metrics.

---

## Three Synchronized Streams

```
WORLD STATE     — hard data
EVENT STATE     — news / releases / governance / protocol changes
HUMAN RESPONSE  — YouTube / social analytics
```

Every day the agent reasons over all three.

---

## Content Moat

Not merely: "what crypto videos perform well."

Specifically: **which transformations of hard machine/resource data consistently make complex market structure interesting and understandable to humans.**

Four years of experiments showing which causal patterns humans found surprising, understandable, and worth paying attention to.

---

## Data Sources

| Source | What it provides |
|--------|------------------|
| GitHub Releases API | Releases, tags, commits for all tracked repos |
| Qubic Blog | Protocol updates, All-Hands, research |
| Quantus Blog | Weekly technical updates, miner releases |
| getmonero Blog | Releases, announcements, CCS |
| Kaspa Developer Docs | KIPs, protocol activation, R&D |
| Clore Changelog | Marketplace, tokenomics, API changes |
| Nosana Blog | Provider demand, inference, models |
| YouTube Analytics API | Retention curves, CTR, engagement |
