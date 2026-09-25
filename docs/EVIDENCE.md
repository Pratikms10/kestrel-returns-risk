# Evidence and failure report

## Claim boundary

The system ranks return risk usefully; it does **not** achieve or claim 95% predictive accuracy. Returns are 11.42% of canonical historical orders, so an all-negative model already appears 88.58% accurate while catching zero returns. I therefore use ROC-AUC for ranking, average precision for the imbalanced positive class, Brier score for probability quality, and threshold metrics for the operational call decision.

Expected hidden score: **about 0.78 ROC-AUC (plausible range 0.75–0.81)**. This expectation comes from two forward validation quarters (AUC 0.768 and 0.773) plus an untouched final-quarter AUC of 0.786 with a 500-resample bootstrap interval of 0.758–0.815.

## Validation design

All splits happen after canonicalizing duplicate order IDs and are chronological.

1. Model selection fold 1: train before 1 October 2025; validate on October–December 2025 (4,170 / 2,082 orders).
2. Model selection fold 2: train before 1 January 2026; validate on January–March 2026 (6,252 / 2,126 orders).
3. Final untouched holdout: train through 31 March 2026; evaluate April–June 2026 (2,126 orders, 245 returns).
4. Only after recording the holdout result is the final model fit on all 10,504 canonical labelled orders for `predictions.csv`.

Candidate averages across the two selection folds:

| Model | ROC-AUC | Average precision | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|---:|
| Logistic regression, C=0.05 | **0.7703** | **0.3584** | **0.0863** | **0.2981** |
| Logistic regression, C=0.10 | 0.7694 | 0.3567 | 0.0865 | 0.2987 |
| Logistic regression, C=0.30 | 0.7675 | 0.3532 | 0.0868 | 0.2998 |
| Logistic regression, C=1.00 | 0.7662 | 0.3523 | 0.0869 | 0.3004 |
| Extra Trees | 0.7508 | 0.3061 | 0.0895 | 0.3083 |
| Histogram gradient boosting | 0.7492 | 0.3069 | 0.0906 | 0.3117 |

## Untouched holdout

Probability quality:

| Metric | Result |
|---|---:|
| ROC-AUC | 0.7861 |
| ROC-AUC 95% bootstrap interval | 0.7581–0.8154 |
| Average precision | 0.4126 |
| Brier score | 0.08495 |
| Log loss | 0.2933 |
| Quantile expected calibration error | 0.00573 |
| Return capture in top-scoring 10% | 36.33% (3.63× random lift) |

Calibration at the decision boundary was strong on this holdout: flagged orders averaged 28.84% predicted risk and returned at 28.43%; unflagged orders averaged 6.15% predicted risk and returned at 6.09%. This is useful evidence for the rupee calculation, but not proof that future probabilities or call impact will remain calibrated.

The action threshold is 15%, chosen before viewing the final holdout. It is above the policy break-even point of 11.18% and limits workload.

| At 15% | Count / rate |
|---|---:|
| Flagged / called | 517 / 24.32% |
| True positives | 147 |
| False positives | 370 |
| False negatives | 98 |
| True negatives | 1,511 |
| Recall | 60.00% |
| Precision | 28.43% |
| Operational accuracy | 77.99% |

How often it does not work: it misses 40% of holdout returns and 71.6% of called orders do not return. Those are expected trade-offs at a low-cost intervention threshold, not hidden defects. Recall is weaker for prepaid UPI (42.9%), ceiling fans (34.8%), and EMI (40.0%); it is stronger for Shield (75.5%), COD (74.6%), air fryers (78.1%), and robot vacuums (73.8%). This is why the action is a short call, not a punitive hold or cancellation.

## Rupee model

Policy inputs: confirmation call ₹45, return handling ₹1,150, and historical call-pilot effectiveness 35%.

On the holdout: `147 × 35% × ₹1,150 − 517 × ₹45 = ₹35,902.50` estimated net benefit.

Scaled to 700 monthly orders: about 170 calls (₹7,660), 48 returns in the called queue, 17 estimated prevented returns (₹19,481 avoided handling), and **₹11,821 estimated monthly net benefit**. Annualized mechanically, that is roughly ₹1.42 lakh. Paid model inference is ₹0/order and ₹0/month. These figures exclude staff overhead already embodied in the call figure, refund amount, margin, cancellation loss, and lifetime value because the pack does not quantify them.

The 35% effectiveness number is observational. A randomized eligible-order pilot is required before treating the savings as causal.

## Failures actually observed

1. **Post-outcome leakage looked spectacular.** Including export-day service and pickup columns produced 0.996 holdout AUC. Every `REVERSE_PICKUP` order in canonical training data was returned. These fields describe the outcome process, not pre-dispatch risk, so they were removed and are protected by an invariance test.
2. **Payment values broke in October.** All 700 October 2025 orders have stored values exactly 100× the catalogue-based expected value. Raw order value is ignored; the model reconstructs it from list price, quantity, and discount. An invariance test proves changing raw value cannot change a score.
3. **Duplicate imports crossed the data boundary.** There are 651 extra partner-feed rows. Dedupe now prefers CRM before any split, preventing one order appearing on both sides.
4. **Customer dates cannot support tenure.** There are 1,999 canonical orders whose current signup date is later than the order. Signup/tenure was discarded.
5. **History counters move backward for some repeat customers.** They remain because they are available pre-dispatch and strongly useful, but this creates a monitoring and upstream-repair requirement.

## Runtime evidence

- Automated suite: 10 tests covering deduplication, amount and leakage invariance, probability/reasons, health/UI, impossible/unknown-field validation, graceful missing model, privacy-safe logging, and exact submission shape.
- `predictions.csv`: 2,096 rows, 2,096 unique order IDs, exact sample order, no missing/out-of-range scores.
- Local endpoint benchmark: 200 calls, 28.7 ms median, 35.8 ms p95; this excludes network transit.
- Test snapshot: 19.75% score at or above threshold; 31.49% of customers were not seen in labelled orders, although all exist in `customers.csv`. Unknown categories are handled, but this is a real generalization risk.

Machine-readable evidence is in `outputs/evaluation_metrics.json`, `outputs/service_benchmark.json`, and `outputs/predictions_summary.json`.
