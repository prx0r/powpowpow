# PowPowPow Plan 1 — The Pressure Equation

Yes. There is real literature pointing toward exactly this kind of model, and the interesting part is that **the strongest ingredients are not exotic deep learning**. They are mostly economically interpretable flows:

**new supply → holder/miner behavior → exchange inflow → order-flow imbalance → book resilience → price impact.**

That is extremely close to the "scientific pressure" framing you're describing.

The most directly relevant crypto paper I found is a 2024 study using intraday on-chain flows. It found that **ETH net inflows to exchanges negatively forecast future ETH returns**, while USDT inflows positively forecast BTC/ETH returns, with the strongest effects around the **1-hour horizon**. BTC exchange inflows themselves were not significant in that sample, which is a useful warning that these relationships are asset-specific rather than universal.

For PRL, the analogue is much cleaner than for BTC because miners are continuously creating a very large fraction of the liquid supply. So I would explicitly model:

$$
\text{Miner Supply Pressure}_t
=
\frac{\text{miner-originated PRL arriving at exchange}_t}
{\text{available bid liquidity}_t}
$$

rather than simply `PRL emitted/day`.

That distinction is essential. Emission is **potential pressure**. Exchange-bound miner flow is **realized pressure**.

Then define the opposing force:

$$
\text{Buy Absorption}_t
=
\text{aggressive buy volume}
+
\Delta \text{resting bid liquidity}
-
\text{bid cancellations}
$$

and finally:

$$
\text{Pressure Balance}_t =
\frac{\text{Buy Absorption}_t}
{\text{Miner Sell Pressure}_t + \text{other aggressive sells}}
$$

That starts to look like an actual physical system.

## There is already strong microstructure evidence for the second half

A new 2026 crypto paper is particularly relevant. It took **1-second Binance Futures L2 data across BTC, LTC, ETC, ENJ and ROSE**, engineered order-book/trade features, and trained CatBoost models. The surprising result was that the same microstructure features had similar predictive importance across assets of very different sizes. Order-flow imbalance, spread and adverse-selection-type features were consistently important, and the authors tested both taker and maker strategies under transaction costs.

That's almost perfect for us because it suggests you don't necessarily need a custom prediction architecture per SafeTrade coin.

You could build **one PowPowPow microstructure feature library** and see whether it transfers across QUBIC, PRL, NOCK etc.

Earlier crypto LOB work found temporal CNNs could predict BTC movements at a ~2-second horizon from raw order-book data, reporting roughly **71% walk-forward directional accuracy** in its Coinbase experiment. I would be cautious about expecting that exact number to survive on SafeTrade after costs, but it establishes that L2 contains genuinely predictive structure.

Another crypto study used **Hawkes processes**, which are especially interesting here because they model the way orders/trades trigger more orders/trades rather than treating observations independently.

## The classic quantitative-finance concept we should steal is OFI

**Order Flow Imbalance (OFI)** is much better than just `bid volume - ask volume`.

It considers changes caused by:

* new bids,
* cancelled bids,
* new asks,
* cancelled asks,
* market buys,
* market sells.

Research shows that price impact is approximately linear in signed order-flow imbalance over small ranges, and ML can improve estimates of the resulting market impact.

Even more relevant to your full L2 dataset: work on **multi-level OFI** finds that including deeper order-book levels improves explanatory power versus just looking at best bid/ask.

And another study found that on slightly longer microstructure horizons, **limit-order additions/cancellations and deeper book shape can be more predictive than simple top-of-book imbalance**.

So for SafeTrade I would calculate something like:

```text
OFI_1
OFI_5
OFI_10
OFI_25
```

where the number refers to number of book levels, plus:

```text
bid_add_rate
bid_cancel_rate
ask_add_rate
ask_cancel_rate

market_buy_rate
market_sell_rate

book_refill_bid
book_refill_ask

book_resilience_bid
book_resilience_ask
```

That tells you whether apparent liquidity is actually willing to absorb pressure.

---

## The really interesting research: dilution appears to matter

A **2026 paper on 404 cryptocurrencies from 2020–2026** found that high FDV relative to circulating market value and higher recent dilution predicted lower subsequent cross-sectional returns.

The reported long-short spreads were roughly **25–32% annualized**, and the effect was strongest among young coins rather than mature blue chips.

That is extremely relevant to Pearl.

It means your intuition:

> "Only 15% is emitted, FDV is massive, miners constantly create tokens—surely that creates pressure"

isn't just crypto folklore. There is emerging empirical evidence that **dilution itself is an asset-pricing factor**, particularly in younger tokens.

There's another 2026 event study of 52 token unlocks. **46 of 52** experienced negative returns within 72 hours, averaging about **−17%**, although the author explicitly describes the evidence as preliminary and correlational.

Continuous mining isn't identical to an unlock, but economically they are relatives:

**unlock:** discrete supply shock
**PoW issuance:** continuous supply shock

Pearl is basically giving us a laboratory where the supply shock happens continuously and is observable.

---

## I'd build a "pressure equation" for PRL

Rather than immediately feed everything into a neural network, define economically meaningful state variables.

### 1. Creation pressure

```text
new_prl_1h
new_prl_24h

new_supply_usd_1h
new_supply_usd_24h

annualized_dilution
```

But don't treat this as selling yet.

### 2. Miner realization pressure

Using identified pool payouts:

```text
pool_rewards
pool_to_miner
miner_to_exchange
miner_unknown_outflow
```

Then:

$$
R_t =
\frac{\text{miner-to-exchange PRL}}
{\text{PRL emitted}}
$$

This is the **miner realization ratio**.

Imagine discovering:

```text
normal R = 0.25

during rally R = 0.18

after price stalls R = 0.62
```

That's far more valuable than RSI.

### 3. Sell pressure

Then:

$$
S_t =
(\text{miner exchange flow})
+
(\text{aggressive non-miner sells})
$$

weighted by price impact.

One PRL dumped into a $100k bid wall doesn't mean the same thing as one dumped into a $500 bid wall.

So:

$$
S^*_t =
\frac{\text{sell notional}}
{\text{bid depth}}
$$

This is your **liquidity-adjusted sell pressure**.

---

## 4. Required buy pressure

Here's the fun bit.

You can estimate the amount of capital required merely to keep the price stationary.

Imagine in a 1-hour window:

```text
miner sell flow       $38,000
other aggressive sell $24,000

bid cancellations     $7,000
new passive bids      $11,000
```

Then the market needs roughly enough incoming buy demand to offset those pressures.

We can empirically estimate:

$$
\Delta P =
\beta_1 OFI
+
\beta_2 MinerFlow
+
\beta_3 Depth
+
\beta_4 Spread
+ \epsilon
$$

Then solve for:

$$
\Delta P = 0
$$

to obtain an approximate:

### `required_buy_flow_for_zero_return`

That's essentially what you're describing:

> **How much buying is scientifically required to keep PRL at $0.90 given the current creation/sell pressure?**

Not philosophically required—empirically required under the current estimated market-impact function.

That could be a fucking excellent PowPowPow metric.

---

## Qubic becomes an amazing comparison

PRL and QUBIC have very different supply systems.

For each, calculate:

$$
\text{Issuance Pressure}
=
\frac{\text{net new supply USD}}
{\text{market depth}}
$$

Suppose illustrative numbers eventually showed:

```text
PRL:
new issuance value/day = $1.0M
5% bid depth            = $300k

pressure = 3.33

QUBIC:
new net issuance/day    = $13k
5% bid depth            = $60k

pressure = 0.22
```

Those figures are illustrative, not measurements.

But it gives a normalized comparison:

> **How much newly created economic inventory exists relative to what the actual market can absorb?**

Then include observed seller behavior.

Maybe PRL miners surprisingly hoard 90%.

Then issuance isn't nearly as bearish as assumed.

That's why measuring the wallets is critical.

---

## Miner profitability introduces another causal layer

There is academic work modeling miners' allocation of hashpower as an economic decision. One paper modeled BTC/BCH miner allocation using expected returns/risk and reproduced observed miner allocations reasonably well; aggregate modeled allocation had a reported correlation around **0.65** with actual allocation.

A more recent paper derives mining profitability directly from hash probability, difficulty, hardware and operating costs rather than relying on historical heuristics.

So we can construct:

$$
\text{Expected Mining Profit}
=
\text{Expected block rewards}
-
\text{electricity}
-
\text{hardware amortization}
-
\text{fees}
$$

Then test a causal sequence like:

$$
Price \uparrow
\rightarrow Profitability \uparrow
\rightarrow Hashrate \uparrow
\rightarrow Miner inventory \uparrow
\rightarrow Exchange inflow \uparrow
\rightarrow Sell pressure \uparrow
\rightarrow Price \downarrow
$$

That is basically your Seesaw in mathematical form.

And different chains will have different lag lengths.

PRL might be:

```text
price → miners: 6h
miners → hashrate: 1–3 days
rewards → exchange: 12h
exchange → price: hours
```

Qubic could be completely different.

Finding those lag structures is probably one of the most valuable things we could do.

---

## Machine learning: I'd use it after the causal features

The temptation is to throw this at a transformer.

I wouldn't initially.

The 2026 crypto microstructure work got strong interpretable results with **CatBoost + engineered OFI/book features**, and the feature relationships transferred surprisingly well between assets.

I'd therefore build this ladder:

**Baseline 1 — linear regression**

```text
future_return_5m ~
    OFI
  + miner_flow
  + issuance
  + depth
  + spread
```

If that doesn't work, stop. Something is wrong with the hypothesis.

**Baseline 2 — logistic regression**

Predict:

```text
P(return_1h < 0)
```

**Baseline 3 — LightGBM / CatBoost**

Add nonlinear relationships and interactions.

This is probably where I expect the best cost/performance initially.

**Baseline 4 — Hawkes process**

For event intensity:

```text
miner sells trigger sells?
large market buys trigger follower buys?
pool payouts create predictable bursts?
```

**Baseline 5 — temporal CNN/transformer**

Only when you have months of high-resolution data.

Then raw L2 sequences + fundamental states.

---

## One especially exciting idea: two-timescale model

I'd separate **pressure** from **trigger**.

### Slow state

Changes over hours/days:

```text
miner_profitability
emission
hashrate
dilution
pool inventory
exchange balances
useful compute
market cap
```

This tells you whether the spring is being compressed.

### Fast state

Milliseconds/minutes:

```text
OFI
aggressive flow
depth
spread
cancellations
microprice
book_resilience
```

This tells you **when the spring releases**.

So:

$$
P(Return_{t+h})
=
f(
\text{structural pressure},
\text{microstructure trigger}
)
$$

For PRL:

> structural: miners sitting on huge profitable inventory
> trigger: bids disappear + aggressive selling begins

That's far better conceptually than predicting price from candles.

---

## Another 2026 result supports the overall idea

A study of **122 Ethereum tokens** constructed 27 on-chain factors. After controlling for traditional crypto momentum/volume factors, **holder distribution and exchange-held share remained among the strongest signals**, while several popular valuation metrics lost significance.

That's important.

It suggests:

**who owns the tokens and where they're moving may be more useful than fancy valuation ratios.**

Which for Pearl means:

**pool → miner → exchange**

could genuinely be one of the best datasets available.

---

## What I would call the main PowPowPow metric family

This could become the signature of the API:

```text
POW PRESSURE
```

With four components:

```text
Creation Pressure
= new issuance / liquidity

Realization Pressure
= miner exchange flow / issuance

Market Pressure
= signed OFI / depth

Absorption Pressure
= sell pressure / incoming buy flow
```

Then expose raw numbers rather than some opaque magic score:

```json
{
  "chain": "PRL",
  "window": "24h",

  "issuance_usd": 0,

  "miner_realization_ratio": 0,

  "miner_exchange_flow_usd": 0,

  "aggressive_buy_usd": 0,
  "aggressive_sell_usd": 0,

  "bid_depth_1pct_usd": 0,
  "bid_depth_5pct_usd": 0,

  "ofi_1m": 0,
  "ofi_1h": 0,

  "required_buy_flow_zero_return": 0
}
```

Then the content almost writes itself:

**"Pearl needs $X of fresh buying every day just to absorb miners."**

**"Qubic only needs $Y."**

**"Pearl miners started selling 3× more this week."**

**"Qubic price fell but its network pressure actually improved."**

That's much more interesting than technical-analysis crypto content because you're trying to measure **the literal forces acting on the market**.

And importantly, the literature suggests each piece independently has empirical justification: dilution matters, exchange flows can forecast returns, on-chain holder distribution matters, order-flow imbalance predicts short-horizon price movement, deeper book structure improves that signal, and miner allocation responds economically to profitability.

The novel part for PowPowPow would be **joining all of those layers for tiny mineable assets where almost nobody has bothered to do it.**

---

## References

1. Return-forecasting and Volatility-forecasting Power of On-chain Activities in the Cryptocurrency Market — https://arxiv.org/abs/2411.06327
2. Explainable Patterns in Cryptocurrency Microstructure — https://arxiv.org/abs/2602.00776
3. Deep Learning for Digital Asset Limit Order Books — https://arxiv.org/pdf/2010.01241
4. Hawkes-based cryptocurrency forecasting via Limit Order — https://arxiv.org/html/2312.16190v1
5. Empirical Study of Market Impact Conditional on Order-Flow Imbalance — https://arxiv.org/abs/2004.08290
6. Multi-Level Order-Flow Imbalance in a Limit Order Book — https://arxiv.org/abs/1907.06230
7. Order Flows and Limit Order Book Resiliency on the Meso-Scale — https://arxiv.org/abs/1708.02715
8. Token Dilution and the Cross-Section of Cryptocurrency Returns — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6636258
9. The 72-Hour Shock? Preliminary Evidence from 52 Token Unlock Events — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6632838
10. Using Economic Risk to Model Miner Hash Rate Allocation in Cryptocurrencies — https://arxiv.org/abs/1806.07189
11. Expected Revenue, Risk, and Grid Impact of Bitcoin Mining — https://arxiv.org/abs/2512.20518
12. On-Chain Factors and Cryptocurrency Asset Pricing — https://papers.ssrn.com/sol3/Delivery.cfm/6670521.pdf?abstractid=6670521
