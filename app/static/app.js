const example = {
  order_id: "DEMO-ORDER-001",
  order_placed_at: "2026-09-25T10:30:00",
  customer_id: "DEMO-CUSTOMER",
  sku: "KH-RV-02",
  sales_channel: "web",
  payment_mode: "cod",
  discount_pct: 20,
  qty: 1,
  order_value_inr: 1,
  promised_delivery_days: 7,
  delivery_pincode: "411001",
  is_gift: "Y",
  customer_prior_orders: 3,
  customer_prior_returns: 2,
  delivery_note: "Please call before delivery",
  last_service_event_type: "NONE",
  pickup_scheduled_at: null,
  source: "crm"
};

const payload = document.querySelector("#payload");
const scoreButton = document.querySelector("#score");
const validation = document.querySelector("#validation");

function resetExample() {
  payload.value = JSON.stringify(example, null, 2);
  validation.textContent = "Synthetic example—no customer record is displayed or logged.";
  validation.classList.remove("error");
}

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

async function checkHealth() {
  const status = document.querySelector("#status");
  try {
    const response = await fetch("/health");
    const data = await response.json();
    status.className = `status ${data.status === "ready" ? "ready" : "error"}`;
    status.innerHTML = `<span></span>${data.status === "ready" ? "Model ready" : "Model not ready"}`;
  } catch (_) {
    status.className = "status error";
    status.innerHTML = "<span></span>Service unavailable";
  }
}

function render(data) {
  document.querySelector("#empty").classList.add("hidden");
  document.querySelector("#result-content").classList.remove("hidden");
  document.querySelector("#order-id").textContent = data.order_id;
  const pct = Math.round(data.return_risk * 1000) / 10;
  document.querySelector("#risk-score").textContent = `${pct}%`;
  document.querySelector("#score-ring").style.setProperty("--score-angle", `${data.return_risk * 360}deg`);

  const isCall = data.action === "same_day_confirmation_call";
  const chip = document.querySelector("#decision-chip");
  chip.textContent = isCall ? "Intervene" : "Normal dispatch";
  chip.classList.toggle("normal", !isCall);
  document.querySelector("#action-title").textContent = isCall ? "Make a same-day call" : "Continue normal dispatch";
  document.querySelector("#guidance").textContent = data.guidance;

  const reasons = document.querySelector("#reasons");
  reasons.replaceChildren(...data.reasons.map(reason => {
    const li = document.createElement("li");
    li.textContent = reason;
    return li;
  }));

  document.querySelector("#call-cost").textContent = money(data.economics.call_cost_inr);
  document.querySelector("#avoided-cost").textContent = money(data.economics.expected_avoided_return_cost_inr);
  document.querySelector("#net-benefit").textContent = money(data.economics.expected_net_benefit_inr);

  const warningBox = document.querySelector("#warnings");
  const warningList = document.querySelector("#warning-list");
  warningList.replaceChildren(...data.warnings.map(warning => {
    const li = document.createElement("li");
    li.textContent = warning;
    return li;
  }));
  warningBox.classList.toggle("hidden", data.warnings.length === 0);
  document.querySelector("#meta").textContent = `${data.model_version} · request ${data.request_id.slice(0, 8)} · paid inference ${money(data.paid_inference_cost_inr)}`;
  if (window.innerWidth <= 920) {
    document.querySelector("#result").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function runDecision() {
  let body;
  try {
    body = JSON.parse(payload.value);
  } catch (error) {
    validation.textContent = `Invalid JSON: ${error.message}`;
    validation.classList.add("error");
    return;
  }

  scoreButton.disabled = true;
  scoreButton.firstChild.textContent = "Scoring… ";
  validation.textContent = "Validating and scoring locally…";
  validation.classList.remove("error");
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join("; ")
        : data.detail || `HTTP ${response.status}`;
      throw new Error(detail);
    }
    render(data);
    validation.textContent = "Decision returned. No paid model call was made.";
  } catch (error) {
    validation.textContent = `Could not score: ${error.message}`;
    validation.classList.add("error");
  } finally {
    scoreButton.disabled = false;
    scoreButton.firstChild.textContent = "Run decision ";
  }
}

document.querySelector("#reset").addEventListener("click", resetExample);
scoreButton.addEventListener("click", runDecision);
resetExample();
checkHealth();
