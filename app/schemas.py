"""Validated API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    order_id: str = Field(min_length=1, max_length=80)
    order_placed_at: datetime
    customer_id: str = Field(min_length=1, max_length=80)
    sku: str = Field(min_length=1, max_length=80)
    sales_channel: Literal["app", "web", "marketplace", "partner_outlet"]
    payment_mode: Literal["prepaid_upi", "prepaid_card", "cod", "emi"]
    discount_pct: float = Field(ge=0, le=100)
    qty: int = Field(ge=1, le=20)
    order_value_inr: float | None = Field(default=None, ge=0)
    promised_delivery_days: int = Field(ge=0, le=60)
    delivery_pincode: str
    is_gift: Literal["Y", "N"]
    customer_prior_orders: int = Field(ge=0, le=100_000)
    customer_prior_returns: int = Field(ge=0, le=100_000)
    delivery_note: str | None = Field(default=None, max_length=500)
    last_service_event_type: str | None = Field(default=None, max_length=80)
    pickup_scheduled_at: datetime | None = None
    source: str | None = Field(default=None, max_length=40)

    @field_validator("delivery_pincode", mode="before")
    @classmethod
    def normalize_pincode(cls, value: object) -> str:
        text = str(value).strip()
        if text.endswith(".0"):
            text = text[:-2]
        if not text.isdigit() or len(text.zfill(6)) != 6:
            raise ValueError("delivery_pincode must contain at most six digits")
        return text.zfill(6)

    @model_validator(mode="after")
    def validate_history(self) -> "OrderInput":
        if self.customer_prior_returns > self.customer_prior_orders:
            raise ValueError("customer_prior_returns cannot exceed customer_prior_orders")
        return self


class Economics(BaseModel):
    call_cost_inr: float
    expected_avoided_return_cost_inr: float
    expected_net_benefit_inr: float
    assumptions: str


class PredictionResponse(BaseModel):
    request_id: str
    order_id: str
    return_risk: float
    action: Literal["same_day_confirmation_call", "dispatch_normally"]
    action_threshold: float
    reasons: list[str]
    economics: Economics
    guidance: str
    warnings: list[str]
    model_version: str
    paid_inference_cost_inr: float


class HealthResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model_version: str | None
    detail: str
