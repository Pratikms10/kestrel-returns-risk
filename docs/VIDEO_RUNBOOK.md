# Three-minute screen recording runbook

Target length: **2:40–2:55**. Record the running product and code only—no slides. Use the synthetic order already loaded in the screen so the public video does not expose client rows or identifiers.

## Before recording

```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open these in advance:

1. Browser: `http://127.0.0.1:8000`
2. Editor: `app/modeling.py` around `UNSAFE_COLUMNS`, `engineer_features`, and `reasons`
3. Editor: `outputs/evaluation_metrics.json` at `holdout_probability_metrics` and `leakage_probe`
4. Editor: `outputs/predictions_summary.json`

Hide notifications, zoom the browser to fit both panels, and do not open raw CSV rows while recording.

## Exact flow and narration

### 0:00–0:20 — Outcome first

**Screen:** browser hero and operating-rule card.

**Say:** “I built an offline pre-dispatch return-risk desk. It scores one order, explains the risk, and recommends a same-day confirmation call above 15 percent. I pushed back on a long automatic hold because policy says holds beyond 24 hours increase cancellations.”

### 0:20–0:55 — Run a new synthetic order

**Screen:** point out that `DEMO-ORDER-001` is synthetic; click **Run decision**.

**Say:** “This synthetic COD robot-vacuum order has two prior returns. The endpoint validates the JSON, returns an 82 percent risk here, and gives an employee three model-faithful reasons. The economics use ₹45 per call, ₹1,150 per return, and the pilot’s 35 percent prevention estimate. No paid API call is made.”

Point to the warning that the demo customer is absent from the reference file. This shows graceful fallback rather than a silent failure.

### 0:55–1:18 — Show behavior changing

**Screen:** change `payment_mode` to `prepaid_upi`, `customer_prior_returns` to `0`, and `is_gift` to `N`; run again.

**Say:** “Changing real pre-dispatch facts changes the score and reasons. The output is decision support: low-risk orders dispatch normally; high-risk orders get a short call, never an automatic cancellation.”

### 1:18–1:52 — One code decision

**Screen:** switch to `app/modeling.py`; show `UNSAFE_COLUMNS`, reconstructed expected value, and `reasons`.

**Say:** “The most important code decision is what I threw away. Service events and pickup timestamps are export-day outcome leakage, so they never enter the model. October payment values were exactly 100 times wrong, so I reconstruct value from product price, quantity, and discount. A regularized logistic model then supports direct contribution-based reasons without an LLM.”

### 1:52–2:25 — Evidence and failure

**Screen:** show only the relevant lines in `evaluation_metrics.json`: final holdout AUC, interval, operating point, and leakage probe.

**Say:** “I selected the model on two forward quarters, then touched the April-to-June holdout once. AUC was 0.786, and the 15 percent rule caught 60 percent of returns while calling 24 percent of orders. My first leaky probe looked almost perfect at 0.996 AUC; that was a failure, not a win, and those fields are excluded and covered by invariance tests.”

### 2:25–2:50 — What ships and what comes next

**Screen:** show `predictions_summary.json` with 2,096 rows and `paid_inference_cost_inr: 0.0`, then return to the app.

**Say:** “The final file has all 2,096 orders in the required shape. I expect roughly 0.78 hidden ROC-AUC. At 700 orders, the backtest projects about ₹11,821 monthly net benefit, but I would start a controlled call pilot next week because the 35 percent call effect is not yet causal. What I deliberately left out: deployment, an LLM layer, and automatic holds.”

Stop recording. Do not add an outro slide.

## Public-link check

Upload the recording to Google Drive, set **Anyone with the link → Viewer**, and open the link in a private/incognito window. Paste that link into `submission-form.md`. This manual link is the only part of the recording workflow that cannot be produced or truthfully verified locally.
