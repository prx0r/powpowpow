<!-- STALE: This document describes an earlier naming scheme or unimplemented concept. Preserved for context. Current architecture is in ukgraph_final.md and SPEC.md. -->
# DataGarden Ideology

## The emerging core set

PowPowPow → allocate compute/capital
Breadup → allocate capital into physical goods
Margin Garden → allocate your own labor/business effort
Service Arbitrage Garden → exploit new AI capability before market pricing adjusts
Business Acquisition Garden → allocate larger capital into operating businesses

Those five all answer essentially the same primitive question:

> **Where is reality currently mispriced?**

---

## The cleaner abstraction

The product is **not "opportunities."** Opportunities are cheap once intelligence is cheap.

The durable asset is the **world-model substrate that lets any model judge opportunities correctly**.

So the three repos should be thought of less as apps and more as **economic reality engines**:

```text
BU = world model of physical goods
PG = world model of local future demand
ME = world model of margins / production economics
```

Each one continuously turns messy reality into structured state that agents can consume.

The key distinction is:

```text
cheap:
"Give me 20 business ideas."

valuable:
"Here is the continuously updated evidence required
to determine whether idea #7 actually makes money."
```

---

## BU — Physical Value Graph

Question:

> **What is this physical thing economically worth, and why?**

Canonical state:

```text
identity
condition
location
purchase price
retail replacement value
used value
parts value
repair cost
liquidation value
scrap value
sales velocity
shipping / handling
historical outcomes
```

Breadup's "flip this" recommendation is merely one **view** over the graph.

Future agents might use the same garden for:

```text
insurance valuation
pawn lending
estate liquidation
repair decisions
procurement
asset-backed lending
inventory pricing
circular economy
robotic resale agents
```

So the asset is not the flip opportunities.

It's **a continuously improving economic model of physical objects**.

---

## PG — Local Demand Graph

Question:

> **Where is money likely to be spent, on what, and when?**

Canonical state:

```text
place
people/businesses
installed assets
planning events
regulatory events
replacement cycles
supplier capacity
service prices
labor availability
property changes
demand evidence
```

Then:

```text
"Start an electrical business here."
"Sell heat-pump software to these firms."
"Open this kind of shop in this town."
```

are just queries.

The enduring asset is a **time-varying economic model of places**.

That's much stronger than "opportunity finder."

---

## ME — Production Economics Graph

Question:

> **What does it actually cost to produce an economic outcome, and what does the market currently pay for it?**

Canonical state:

```text
output
market price
inputs
labor
materials
software
AI capability
capital
distribution
regulation
competition
time
failure rate
```

From that you derive:

$$
\text{margin} =
\text{market value} -
\text{true production cost}
$$

And this gets especially interesting in AGI because the production function keeps mutating.

```text
Yesterday:
video ad = £250 production cost

Today:
new model → £18

Market price:
still £300

ME records:
temporary spread
```

But again, **the spread isn't the asset**.

The asset is knowing the evolving cost curves well enough that a frontier model can discover the spread itself.

---

## Service Arbitrage — the Seesaw of AI capability

```text
NEW CAPABILITY
      ↓
cost to perform task collapses
      ↓
market price hasn't collapsed yet
      ↓
ARBITRAGE WINDOW
```

That last one is extremely close to the Seesaw thesis.

For example:

Jev makes classification nearly free
+
businesses still paying agencies / staff heavily for classification workflows
=
temporary service opportunity

Or:

new avatar model
+
UGC creators still charging £200/video
+
generation cost falls to £2
=
opportunity

The garden continuously records:

```text
capability release
market price before
production cost before
production cost after
adoption lag
market price after
time until spread closes
```

And eventually you get something much more important than a list of business ideas:

A historical dataset of how quickly technological capability turns into economic price compression.

That is hard to recreate retrospectively and directly helps people make money.

---

## This changes the Data Garden doctrine

Previously:

> Grow opportunities.

Better:

> **Grow worlds from which opportunities can be inferred.**

You want the repositories to accumulate facts such that increasingly intelligent models become **more useful when plugged into your data**.

That is an unusually nice relationship with the frontier:

```text
frontier intelligence ↑
        +
our reality graph ↑ over time

        ↓

value of query ↑
```

You are not betting that your recommendation algorithm stays superior.

You're betting:

> **Future intelligence still needs grounded state.**

That's much safer.

---

## "Consumed worlds" is actually a useful concept

Think of an agent entering BU.

Instead of receiving a pile of listings, it enters a little economic universe in which:

```text
Technics SL-1200
has:
market history
variants
failure modes
parts
retail alternatives
regional liquidity
repair economics
substitutes
```

The model can reason *inside* that world.

Likewise PG gives it a world containing:

```text
Manchester
→ housing stock
→ planning
→ trades
→ prices
→ regulation
→ demand
→ businesses
```

And ME:

```text
UGC production
→ market price
→ human cost
→ AI cost
→ tools
→ customer pain
→ distribution cost
```

You're effectively selling **high-resolution slices of reality**.

That feels much closer to the final concept.

---

## The strongest moat becomes accumulated resolution

Not merely more rows.

Over time the world gets **denser**.

At first BU knows:

```text
item → price
```

Then:

```text
item
→ variants
→ condition
→ failure modes
→ parts
→ repair
→ liquidity
→ regional differences
→ seasonality
→ eventual sale
```

Same object, progressively richer reality.

So perhaps:

$$
\boxed{
\text{Garden Moat}
\approx
\text{Coverage}
\times
\text{Resolution}
\times
\text{History}
\times
\text{Verification}
}
$$

This is much better than counting dataset size.

---

## Content now has a precise role

Content is **not the core product**.

Content is how humans consume slices of the world:

```text
WORLD MODEL
    ↓
interesting query
    ↓
finding
    ↓
article/video/chart
    ↓
audience
    ↓
feedback / corrections / demand
    ↓
WORLD MODEL
```

Example BU:

> "5 broken coffee machines currently worth more repaired than working-condition sellers realize."

Example PG:

> "These five UK towns are approaching a boiler-replacement crunch."

Example ME:

> "This new model just collapsed the production cost of these three services."

Every piece of media is simply a **harvest query** against the garden.

Agents use APIs.

Humans use media.

Same underlying asset.

---

## The company-level thesis

> **Build persistent economic world models in domains where reality is fragmented, continuously changing, and expensive to normalize. Let frontier intelligence discover opportunities from them. Use content as the human interface, APIs as the machine interface, and time as the moat.**

And the three current worlds are beautifully orthogonal:

```text
BU — THINGS
What are physical assets actually worth?

PG — PLACES
Where is economic demand forming?

ME — PRODUCTION
What does creating value actually cost?
```

That's much cleaner.

The opportunities are **fruit**.

The graphs are **trees**.

The gardens are the **systems that keep those trees alive and growing**.

And frontier AI is just increasingly powerful machinery for harvesting them.
