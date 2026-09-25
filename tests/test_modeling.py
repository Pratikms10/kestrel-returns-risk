from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from app.modeling import canonical_orders


def test_canonical_orders_prefers_crm() -> None:
    raw = pd.DataFrame(
        [
            {"order_id": "A", "source": "partner_feed", "value": 1},
            {"order_id": "A", "source": "crm", "value": 1},
            {"order_id": "B", "source": "crm", "value": 2},
        ]
    )
    result = canonical_orders(raw)
    assert list(result.order_id) == ["A", "B"]
    assert result.loc[result.order_id.eq("A"), "source"].item() == "crm"


def test_payment_export_anomaly_cannot_change_score(artifact, order_record) -> None:
    low = copy.deepcopy(order_record)
    high = copy.deepcopy(order_record)
    low["order_value_inr"] = 1
    high["order_value_inr"] = 99_999_999
    low_score = artifact.score(pd.DataFrame([low]))[0][0]
    high_score = artifact.score(pd.DataFrame([high]))[0][0]
    assert np.isclose(low_score, high_score)


def test_post_outcome_fields_cannot_change_score(artifact, order_record) -> None:
    safe = copy.deepcopy(order_record)
    leaky = copy.deepcopy(order_record)
    safe["last_service_event_type"] = "NONE"
    safe["pickup_scheduled_at"] = None
    leaky["last_service_event_type"] = "REVERSE_PICKUP"
    leaky["pickup_scheduled_at"] = "2026-10-01T10:00:00"
    safe_score = artifact.score(pd.DataFrame([safe]))[0][0]
    leaky_score, _, warnings = artifact.score(pd.DataFrame([leaky]))
    assert np.isclose(safe_score, leaky_score[0])
    assert any("ignored by design" in message for message in warnings[0])


def test_score_is_probability_and_reasons_are_readable(artifact, order_record) -> None:
    score, engineered, _ = artifact.score(pd.DataFrame([order_record]))
    reasons = artifact.reasons(engineered.iloc[[0]])
    assert 0 <= score[0] <= 1
    assert 1 <= len(reasons) <= 3
    assert all(len(reason) > 15 for reason in reasons)
