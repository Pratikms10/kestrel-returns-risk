# Kestrel Returns Risk

An offline decision-support service that scores an order **before dispatch**, explains the score in plain language, and recommends either a same-day confirmation call or normal dispatch. It does not cancel orders, does not impose an indefinite hold, and makes no paid model/API call.

> **Public-repository boundary:** this repository excludes the supplied client files, trained artifact, row-level predictions, logs, package manifest, and confidential submission ZIP. Reviewers with the original task pack can reproduce everything using the commands below.

## The decision

Call orders at **15% or higher predicted return risk**, then release them within 24 hours. The policy inputs imply a theoretical call break-even risk of `45 / (0.35 × 1,150) = 11.18%`; 15% adds a buffer for uncertainty and keeps the queue manageable. Shield members receive a service-oriented call, not harsher treatment.

On the untouched April–June 2026 holdout, this rule flagged 517 of 2,126 orders (24.3%), caught 147 of 245 returns (60.0% recall), and achieved 28.4% precision. Scaled to 700 orders/month, the backtest estimates 170 calls, roughly 17 prevented returns, and **₹11,821 monthly net benefit** after call cost. This is an estimate, not a guaranteed saving.

## How it works

```text
order JSON ──> Pydantic validation ──> pre-dispatch feature builder
                                               │
customers.csv + products.csv ──────────────────┘
                                               ↓
                                  regularized logistic model
                                               ↓
                          probability + coefficient-based reasons
                                               ↓
                 ≥15%: same-day call    <15%: normal dispatch
                                               ↓
                       privacy-safe JSONL decision log
```

The model is deliberately inspectable. A regularized logistic regression beat Extra Trees and histogram gradient boosting on two chronological model-selection folds. It also produces faithful local contribution reasons without an LLM.

## Start on a clean machine

Requirements: Python 3.11+ and the supplied Kestrel data files. No API key, Docker, database, or internet connection is required after dependencies are installed.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.train
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The interactive screen calls the same `POST /predict` endpoint documented at `http://127.0.0.1:8000/docs`.

macOS/Linux activation is `source .venv/bin/activate`; the remaining commands are unchanged.

If the model file is missing, the service still starts and `/health` reports `not_ready`; `/predict` returns a polite HTTP 503 with the training command.

## Reproduce every deliverable

Place the eight supplied files in `data/raw/` with these names: `train.csv`, `test_unlabelled.csv`, `customers.csv`, `products.csv`, `sample_submission.csv`, `ops-policy.pdf`, `email-thread.txt`, and `README.txt`.

```powershell
python -m pip install -r requirements-dev.txt
python -m scripts.evaluate
python -m scripts.train
python -m scripts.build_predictions
python -m scripts.benchmark_service
python -m scripts.build_memo_pdf
python -m pytest -q
python -m scripts.package_submission
python -m scripts.verify_submission
```

Generated outputs:

- `outputs/predictions.csv` — 2,096 test orders in the exact sample order and schema.
- `outputs/evaluation_metrics.json` — fold-level, holdout, slice, economics, and leakage evidence.
- `outputs/service_benchmark.json` — local endpoint latency evidence.
- `outputs/Ritu_Deshpande_Memo.pdf` — one-page nontechnical memo.

## Endpoint

`POST /predict` accepts one order in the supplied snapshot schema. Example:

```json
{
  "order_id": "DEMO-ORDER-001",
  "order_placed_at": "2026-09-25T10:30:00",
  "customer_id": "DEMO-CUSTOMER",
  "sku": "KH-RV-02",
  "sales_channel": "web",
  "payment_mode": "cod",
  "discount_pct": 20,
  "qty": 1,
  "order_value_inr": 1,
  "promised_delivery_days": 7,
  "delivery_pincode": "411001",
  "is_gift": "Y",
  "customer_prior_orders": 3,
  "customer_prior_returns": 2,
  "delivery_note": "Please call before delivery",
  "last_service_event_type": "NONE",
  "pickup_scheduled_at": null,
  "source": "crm"
}
```

The stored `order_value_inr` is accepted for schema compatibility but intentionally ignored. Expected value is reconstructed from product list price, quantity, and discount because all 700 October 2025 payment values are exactly 100× the expected amount.

## Evidence, not just a score

The test outcome is hidden, so the honest performance estimate is the final chronological holdout:

| Measure | Result |
|---|---:|
| ROC-AUC | 0.786 |
| 95% bootstrap interval | 0.758–0.815 |
| Average precision | 0.413 |
| Brier score | 0.0849 |
| Decile calibration error | 0.0057 |
| Top 10% return capture | 36.3% |
| Median local endpoint latency (200 calls) | 28.7 ms |
| Paid inference cost | ₹0/order |

I expect `predictions.csv` to score about **0.78 ROC-AUC** on the hidden outcomes, plausibly 0.75–0.81. ROC-AUC is the primary estimate because the deliverable is a continuous ranking score and only 11.4% of historical orders were returns. Accuracy is misleading here: predicting “not returned” for every order already gives 88.6% accuracy. The 15% action threshold intentionally trades accuracy for useful return capture.

The probabilities were also well aligned on the holdout: called orders averaged 28.84% predicted risk versus a 28.43% observed return rate; uncalled orders averaged 6.15% versus 6.09% observed. That supports using the score for economics, while still requiring a live pilot.

Full methodology and failure analysis are in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

## Data controls and design choices

| Issue observed | What the system does |
|---|---|
| 651 partner-feed duplicate rows | Keeps one CRM row per `order_id` before every split. |
| Service/pickup fields are export-day snapshots | Excludes them completely; using them produced a fake 0.996 holdout AUC. |
| October payment values are 100× wrong | Ignores raw payment value and reconstructs order value. |
| 1,999 signup dates occur after their orders | Excludes signup date and customer tenure. |
| Free-text delivery notes may contain private data | Uses only presence and capped length; never logs the text. |
| Customer history counters are inconsistent for some repeats | Keeps the strong pre-dispatch signal, documents the defect, and recommends repair/monitoring. |
| Current Shield status may not be as-of-order | Keeps it as supplied, audits Shield separately, and forbids an extended hold. |

Prediction logs contain a request ID, a truncated hash of the order ID, score, action, latency, warning count, model version, and cost. They exclude raw order/customer IDs, address fields, and delivery-note text.

## What works and what does not

Works now:

- Deterministic offline training, batch scoring, and single-record scoring.
- Pydantic validation, unknown-category handling, human-readable reasons, and graceful missing-model behavior.
- Chronological evaluation, slice metrics, bootstrap interval, leakage sentinel tests, and exact submission-shape checks.
- A responsive employee screen and local structured logs.

Not finished by design:

- No authentication, deployment, model registry, feature store, or live warehouse integration.
- No automatic dispatch hold/cancel action; the economics do not justify it and policy records a 12% cancellation rate after holds beyond 24 hours.
- No claim that calls cause a 35% reduction; that figure needs a controlled pilot.
- No hidden-label result, production drift evidence, or calibrated cancellation/lifetime-value cost because those outcomes were not supplied.

## Repository map

```text
app/                    FastAPI service, model code, schemas, and screen
scripts/                train, evaluate, predict, benchmark, package, verify
tests/                  leakage, validation, privacy, and submission tests
docs/                   evidence, memo source, recording runbook
outputs/                predictions and generated evidence/deliverables
data/raw/               supplied confidential data (never public)
submission-form.md      prefilled submission answers
```

## Privacy

The data is client-confidential. This public repository contains implementation and aggregate evidence only. Do not force-add `data/raw/`, the trained artifact, row-level predictions, logs, package manifest, or the submission ZIP. Transfer the complete package only through the approved private route. See `DATA_PRIVACY.md`.
