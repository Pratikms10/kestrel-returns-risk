# Exact three-minute video guide

Target length: **2:40–2:55**. Hard limit: **3:00**. Show the running product and code only—**no slides**. Use only the synthetic orders below so the public video never exposes a client order, customer ID, raw CSV row, or `predictions.csv` row.

## 1. Prepare the demo before recording

The app is currently configured for port `8022`. First try opening:

`http://127.0.0.1:8022`

If it does not load, open PowerShell and paste:

```powershell
cd "C:\Users\HP\Documents\Codex\2026-09-25\kestrel-home-returns-risk"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8022
```

Leave that terminal running. If PowerShell says the address is already in use, the existing server is probably still running—open the URL instead of starting a second copy.

Open these three files before pressing Record:

1. `app/modeling.py` at lines 27, 172, and 213.
2. `outputs/evaluation_metrics.json` around lines 294–342.
3. `outputs/predictions_summary.json` from line 1.

If VS Code's `code` command is available, paste these in a second terminal:

```powershell
cd "C:\Users\HP\Documents\Codex\2026-09-25\kestrel-home-returns-risk"
code -g app/modeling.py:27
code -g outputs/evaluation_metrics.json:294
code outputs/predictions_summary.json
```

Do not open `data/raw/`, `predictions.csv`, the email thread, or the policy PDF during the public recording.

## 2. Recording setup

- Record landscape at 1920×1080 if possible.
- Use a clear microphone; no music or animated intro.
- Keep the pointer visible and move it slowly.
- Set browser zoom around 80–90% so the input and result are easy to see.
- Hide notifications, bookmarks, email, and unrelated tabs.
- Put this script on a phone or second screen; do not display it in the recording.
- Do one rehearsal. Aim for 2:45, leaving 15 seconds of safety.

## 3. High-risk synthetic payload

The app loads this example automatically. If it was changed, click **Reset example**, or select the whole JSON box with `Ctrl+A` and paste:

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

Expected result: approximately **82.4% risk** and **Make a same-day call**.

## 4. Low-risk comparison payload

For the second run, click inside the JSON box, press `Ctrl+A`, and paste this complete payload:

```json
{
  "order_id": "DEMO-ORDER-002",
  "order_placed_at": "2026-09-25T10:30:00",
  "customer_id": "DEMO-CUSTOMER",
  "sku": "KH-RV-02",
  "sales_channel": "web",
  "payment_mode": "prepaid_upi",
  "discount_pct": 20,
  "qty": 1,
  "order_value_inr": 1,
  "promised_delivery_days": 7,
  "delivery_pincode": "411001",
  "is_gift": "N",
  "customer_prior_orders": 3,
  "customer_prior_returns": 0,
  "delivery_note": "Please call before delivery",
  "last_service_event_type": "NONE",
  "pickup_scheduled_at": null,
  "source": "crm"
}
```

Expected result: approximately **11.1% risk** and **Continue normal dispatch**.

## 5. Exact recording timeline and narration

### 0:00–0:18 — Outcome first

**Screen action:** Start on the top of the browser screen. Point to the 15% operating rule.

**Say exactly:**

> Hi, I built Kestrel's offline pre-dispatch return-risk desk. It scores an order before shipment, explains the risk, and recommends either normal dispatch or a same-day confirmation call above 15 percent. I changed the requested blanket hold because holds beyond 24 hours create cancellations.

### 0:18–0:52 — Run the high-risk order

**Screen action:** Point to `DEMO-ORDER-001`, then click **Run decision**. Let the result settle. Point to 82.4%, the three reasons, and the rupee cards.

**Say exactly:**

> This is a synthetic COD robot-vacuum order with two prior returns, so no client row is exposed. The validated endpoint returns about 82 percent risk and three employee-readable reasons. It recommends a same-day call, not cancellation. The economics use a 45-rupee call, 1,150 rupees per return, and the policy's 35 percent pilot estimate. Paid inference cost is zero.

### 0:52–1:12 — Show that real inputs change the decision

**Screen action:** Paste the complete low-risk payload from section 4 and click **Run decision**. Point to approximately 11.1% and **Continue normal dispatch**.

**Say exactly:**

> I changed only facts available before dispatch: prepaid payment, no gift, and no prior returns. Risk falls to about 11 percent, below the action threshold, so dispatch continues normally. The score supports a reversible operating decision; it never blocks or cancels automatically.

### 1:12–1:47 — Show one important code decision

**Screen action:** Switch to `app/modeling.py`. Briefly show line 27, then line 172, then the `reasons` method near line 213. Do not scroll through the whole file.

**Say exactly:**

> I tried regularized logistic regression, Extra Trees, and histogram gradient boosting; logistic regression won both forward-selection folds. More importantly, I threw away misleading features. Service events and pickup timestamps occur after dispatch and produced a fake 0.996 AUC. October payment values were exactly 100 times wrong, so this code reconstructs value from product price, quantity, and discount. Coefficient contributions generate faithful reasons without an LLM.

### 1:47–2:23 — Show evidence and failure rate

**Screen action:** Switch to `outputs/evaluation_metrics.json`. Show `holdout_operating_point`, `holdout_probability_metrics`, `leakage_probe`, and `monthly_backtest_projection`. Pause briefly on each; do not read every JSON field.

**Say exactly:**

> Model selection used two earlier forward quarters, followed by one untouched April-to-June holdout. ROC-AUC was 0.786, with a 0.758 to 0.815 interval, and average precision was 0.413. At 15 percent, it calls 24 percent of orders and catches 60 percent of returns. Precision is 28 percent, so a cheap call is appropriate but a punitive hold is not. Called-order calibration was also close: 28.84 percent predicted versus 28.43 percent observed.

### 2:23–2:52 — What ships, what was left out, and what happens next

**Screen action:** Show `outputs/predictions_summary.json`, pointing only to `rows`, `unique_order_ids`, and paid cost. Return to the product for the final sentence.

**Say exactly:**

> The submission contains all 2,096 required scores in the supplied order, and I expect roughly 0.78 hidden ROC-AUC. At 700 monthly orders, the backtest estimates about 11,821 rupees net benefit. I deliberately left out deployment, an LLM layer, and automatic holds. The 35 percent call effect is not causal proof, so next week I would run a controlled four-week call pilot.

Stop recording immediately. Do not add an outro slide.

## 6. One-piece narration for a teleprompter

Copy this into a private notes/teleprompter app; do not display the script itself in the video:

```text
Hi, I built Kestrel's offline pre-dispatch return-risk desk. It scores an order before shipment, explains the risk, and recommends either normal dispatch or a same-day confirmation call above 15 percent. I changed the requested blanket hold because holds beyond 24 hours create cancellations.

This is a synthetic COD robot-vacuum order with two prior returns, so no client row is exposed. The validated endpoint returns about 82 percent risk and three employee-readable reasons. It recommends a same-day call, not cancellation. The economics use a 45-rupee call, 1,150 rupees per return, and the policy's 35 percent pilot estimate. Paid inference cost is zero.

I changed only facts available before dispatch: prepaid payment, no gift, and no prior returns. Risk falls to about 11 percent, below the action threshold, so dispatch continues normally. The score supports a reversible operating decision; it never blocks or cancels automatically.

I tried regularized logistic regression, Extra Trees, and histogram gradient boosting; logistic regression won both forward-selection folds. More importantly, I threw away misleading features. Service events and pickup timestamps occur after dispatch and produced a fake 0.996 AUC. October payment values were exactly 100 times wrong, so this code reconstructs value from product price, quantity, and discount. Coefficient contributions generate faithful reasons without an LLM.

Model selection used two earlier forward quarters, followed by one untouched April-to-June holdout. ROC-AUC was 0.786, with a 0.758 to 0.815 interval, and average precision was 0.413. At 15 percent, it calls 24 percent of orders and catches 60 percent of returns. Precision is 28 percent, so a cheap call is appropriate but a punitive hold is not. Called-order calibration was also close: 28.84 percent predicted versus 28.43 percent observed.

The submission contains all 2,096 required scores in the supplied order, and I expect roughly 0.78 hidden ROC-AUC. At 700 monthly orders, the backtest estimates about 11,821 rupees net benefit. I deliberately left out deployment, an LLM layer, and automatic holds. The 35 percent call effect is not causal proof, so next week I would run a controlled four-week call pilot.
```

## 7. Final video quality check

Before uploading, confirm all seven:

- Duration is below 3:00.
- The app visibly runs twice and produces two different decisions.
- One code decision is visible.
- The observed failure/leakage story is explained.
- Tried, changed, and discarded choices are all stated.
- No raw client row, row-level prediction, email, customer ID, or notification appears.
- Audio is clear at normal volume.

Suggested filename: `Pratik_Kestrel_Returns_Risk_Walkthrough.mp4`

## 8. Upload and paste the link

1. Upload the MP4 to Google Drive.
2. Right-click it and choose **Share**.
3. Under **General access**, choose **Anyone with the link**.
4. Keep the role as **Viewer** and copy the link.
5. Open the link in an incognito/private window and play at least the first 10 seconds.
6. In `submission-form.md`, replace the video placeholder with:

```markdown
**Three-minute screen recording:** https://drive.google.com/file/d/YOUR_FILE_ID/view
```

7. Replace the hours placeholder with your actual total, for example:

```markdown
**Hours spent:** 6.5 hours
```

8. Commit and push those two final edits:

```powershell
git add submission-form.md
git commit -m "docs: add walkthrough link and hours"
git push origin main
```

Do not upload the raw CSVs, `predictions.csv`, trained artifact, logs, or confidential ZIP to the public repository or show them in the public video.
