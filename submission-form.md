# Kestrel Home — Task 2 submission form

## GitHub Repository URL

**REQUIRED HUMAN INPUT:** add the private repository URL after sharing reviewer access, or enter the reviewer-approved private ZIP route. Client data must not be public.

## What did you build, and what business decision does it support? State the number and the rupees.

I built an offline pre-dispatch return-risk system: a reproducible model pipeline, `predictions.csv`, a validated FastAPI endpoint, an employee screen with readable reasons/economics, privacy-safe logs, and a chronological evidence suite. It supports a **same-day confirmation call for orders at ≥15% risk, followed by release within 24 hours—not automatic cancellation or a long hold**. On the untouched newest quarter, that line called 24.3% of orders and caught 60.0% of returns. Scaled to 700 monthly orders, the backtest estimates about 170 calls costing ₹7,660, about 17 prevented returns worth ₹19,481, and **₹11,821 monthly net benefit**. This is a pilot estimate, not guaranteed savings.

## What score do you expect predictions.csv to get on the hidden outcomes, on which metric, and why that metric? Say how you estimated it.

I expect **about 0.78 ROC-AUC**, plausibly **0.75–0.81**. I chose ROC-AUC because the file supplies continuous ranking scores and only 11.4% of canonical historical orders are returns; raw accuracy rewards the useless all-negative answer. Two forward model-selection quarters scored 0.768 and 0.773 AUC. The untouched April–June 2026 holdout scored 0.786; a fixed 500-resample bootstrap interval was 0.758–0.815. Average precision was 0.413, Brier score 0.0849, and decile calibration error 0.0057. Called orders averaged 28.84% predicted risk versus 28.43% observed.

## How do you know it works? How you validated, on what split, error rate, and the kind of case it gets wrong.

I deduplicated orders before splitting, selected the model on Q4 2025 and Q1 2026 forward folds, froze the 15% action threshold, then evaluated once on the untouched April–June 2026 quarter (2,126 orders; 245 returns). At that threshold: TP 147, FP 370, FN 98, TN 1,511; recall 60.0%, precision 28.4%, operational accuracy 78.0%. It therefore misses 40% of returns and most called orders would not have returned. Recall is weakest for prepaid UPI, ceiling fans, and EMI. Ten automated tests cover leakage and payment-value invariance, impossible/unknown-field validation, missing-model behavior, log privacy, endpoint output, and exact submission shape.

## Did you change, narrow, or push back on the client's ask? What, when, and why.

Yes. Before final modeling I rejected “95% accuracy” as the decision target: always predicting no return already reaches 88.6% while preventing nothing, and the data does not support 95% honest discrimination. I also changed “flag and hold” into “flag for a same-day confirmation call and release within 24 hours.” Policy says holds beyond 24 hours cancel around 12% of orders, while a call costs ₹45 and the pilot suggests benefit. The model never cancels or indefinitely holds. Shield customers get a service-oriented call because their lifetime value is important.

## What is wrong with what you are handing us, or with the data we handed you? Be specific.

The hidden outcomes are unavailable, so 0.78 AUC is an estimate. The 35% call effect was not randomized, so rupee benefit is not causal. The pack has 651 duplicate partner-feed rows; all 700 October 2025 payment values are exactly 100× expected; 1,999 signup dates occur after their orders; customer history counters sometimes decrease; Shield status and signup are current snapshots, not guaranteed as-of-order; and service/pickup columns are outcome leakage. A deliberate leakage probe reached 0.996 AUC, proving why they cannot be used. The final test has 31.49% customers unseen in labelled orders. The product lacks production authentication, deployment, drift monitoring, and a warehouse connector.

## What does one prediction cost, and what would a month cost at Kestrel's volume (about 700 orders a month)? Show the arithmetic. If you used no paid calls, say so.

The production model is local and makes **no paid API calls: ₹0/prediction × 700 = ₹0/month** in model/API fees (ordinary machine overhead excluded). The separate recommended operation costs about `170 calls × ₹45 = ₹7,650` per month; exact holdout scaling gives ₹7,660. Expected avoided handling is `~17 prevented returns × ₹1,150 ≈ ₹19,550` (exact scaling ₹19,481), leaving about ₹11,821 net under the stated assumptions.

## What did you deliberately leave out, and why that rather than something else?

I left out an LLM explanation layer because coefficient-based reasons are faithful, fast, private, and free. I left out free-text NLP because notes can contain private address details and the sample is too small to justify the exposure. I excluded post-outcome service/pickup fields, broken raw payment value, unreliable tenure, customer ID memorization, automatic holds/cancellations, authentication, deployment, and a database. The task rewards a working decision loop; those additions would not repair the main uncertainty, which is intervention causality.

## Anything you built or found that nobody asked for?

I added an economic threshold derived from policy, a 500-resample AUC interval, slice-level failure reporting, a deliberate leakage probe, amount/leakage invariance tests, privacy-safe structured logs, a graceful missing-model state, local latency/cost benchmarks, and an exact sample-order submission validator. I also found the 100× October payment defect and quantified how a leaky model could falsely appear almost perfect.

## What did you use AI for? Which tools and models, where they helped, where they misled you, what you threw away. Link your three-minute screen recording here.

I used OpenAI Codex (GPT-based coding agent) to accelerate data-audit hypotheses, implementation, tests, UI copy, and document drafting. I verified every reported number by running local Python scripts and retained deterministic outputs in the evidence JSON. The seductive near-perfect result from including service/pickup fields was rejected as leakage; tree models and raw-value/tenure features were also discarded after forward validation or data audit. The production product uses no AI API and has ₹0 paid inference cost. Incremental assistant cost was not separately metered under the existing account.

**REQUIRED HUMAN INPUT — public three-minute Google Drive link:** paste after recording and confirming “Anyone with the link” in a private browser.

## Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. Run `python -m scripts.train`, then `uvicorn app.main:app --host 127.0.0.1 --port 8000`; no API key is needed. Reproduce evidence with `python -m scripts.evaluate` and `python -m pytest -q`.
2. The action line is 15%: make a same-day confirmation call and release within 24 hours. Never use service/pickup fields, never turn the score into an automatic cancellation, and treat Shield callers as service recovery.
3. Measure the intervention in a controlled pilot before trusting ₹11,821/month. Monitor call completion, cancellations, returns, Shield slice, drift, and the known upstream data defects.

## Hours spent

**REQUIRED HUMAN INPUT:** enter Pratik's actual elapsed hours; this cannot be inferred honestly from generated files.
