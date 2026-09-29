from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AgingBucket:
    name: str  # e.g. "current", "1-30", "31-60", "61-90", "91-120", "120+"
    label: str
    min_days: int | None
    max_days: int | None


DEFAULT_AGING_BUCKETS: list[AgingBucket] = [
    AgingBucket(name="current", label="Current", min_days=None, max_days=0),
    AgingBucket(name="1-30", label="1–30 Days", min_days=1, max_days=30),
    AgingBucket(name="31-60", label="31–60 Days", min_days=31, max_days=60),
    AgingBucket(name="61-90", label="61–90 Days", min_days=61, max_days=90),
    AgingBucket(name="91-120", label="91–120 Days", min_days=91, max_days=120),
    AgingBucket(name="120+", label="120+ Days", min_days=121, max_days=None),
]


@dataclass(frozen=True, slots=True)
class AgingQuery:
    company_id: int
    report_type: str  # "ar" or "ap"
    as_of_date: date
    currency: str
    partner_id: int | None = None


@dataclass(frozen=True, slots=True)
class AgingItem:
    partner_id: int
    partner_code: str
    partner_name: str
    invoice_id: int
    invoice_no: str
    invoice_date: date
    due_date: date
    original_amount: Decimal
    paid_amount: Decimal
    credited_amount: Decimal
    outstanding_amount: Decimal
    days_overdue: int
    bucket: str
    currency: str


@dataclass(frozen=True, slots=True)
class AgingTotals:
    total_current: Decimal
    total_1_30: Decimal
    total_31_60: Decimal
    total_61_90: Decimal
    total_91_120: Decimal
    total_120_plus: Decimal
    total_outstanding: Decimal


@dataclass(frozen=True, slots=True)
class AgingReportRead:
    company_id: int
    report_type: str  # "ar" or "ap"
    as_of_date: date
    currency: str
    items: list[AgingItem]
    totals: AgingTotals
