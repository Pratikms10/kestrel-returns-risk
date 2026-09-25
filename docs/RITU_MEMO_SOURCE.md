# To: Ritu Deshpande, Head of D2C Operations

## Decision

Do not put every flagged order on an open-ended hold. Starting next week, send orders scoring **15% or higher** to a same-day confirmation call and release them within 24 hours. Give Shield members a service-oriented call; do not penalize them for the higher observed return rate.

## The number

On the newest labelled quarter, the model separated returns from non-returns with **0.786 ROC-AUC**. At the 15% action line it selected 24% of orders and caught 60% of eventual returns. Precision was 28%, so this is suitable for a low-cost call—not cancellation or a long hold. A blanket “not returned” guess is already 89% accurate, which is why the promised 95% accuracy is the wrong board measure.

## The rupees

At 700 orders a month, the backtest implies about **170 calls costing ₹7,660**, roughly **17 prevented returns worth ₹19,481**, and **₹11,821 net benefit per month** (about ₹1.42 lakh annualized). Production model calls cost ₹0. The estimate uses policy figures of ₹45/call, ₹1,150/return, and the earlier pilot’s 35% prevention rate. That last number is not yet causal proof.

## What to do next week

Launch a four-week controlled pilot: randomly split eligible flagged orders between same-day call and business-as-usual, never hold beyond 24 hours, and track call completion, dispatch time, cancellation, return, Shield status, and reason. Review queue size and cancellations daily. At month-end, decide from measured incremental returns prevented and net rupees—not model accuracy alone. Meanwhile, IT should repair the October payment scaling, non-monotonic customer history counters, and non-as-of customer dates.

## Boundary

Do not use export-day service or pickup fields: they reveal what happened after dispatch and made a bad model look almost perfect. The result above excludes them and uses a true forward-time test.
