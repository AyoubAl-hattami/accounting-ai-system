from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.application.reports.aging_dto import (
    DEFAULT_AGING_BUCKETS,
    AgingBucket,
    AgingItem,
    AgingTotals,
)


def classify_bucket(
    days_overdue: int,
    buckets: Sequence[AgingBucket] | None = None,
) -> str:
    """Classify overdue days into an aging bucket.

    Default buckets:
    - Current: days_overdue <= 0
    - 1-30: 1 <= days_overdue <= 30
    - 31-60: 31 <= days_overdue <= 60
    - 61-90: 61 <= days_overdue <= 90
    - 91-120: 91 <= days_overdue <= 120
    - 120+: days_overdue > 120
    """
    active_buckets = buckets or DEFAULT_AGING_BUCKETS

    for b in active_buckets:
        if b.min_days is None and b.max_days is not None:
            if days_overdue <= b.max_days:
                return b.name
        elif b.min_days is not None and b.max_days is not None:
            if b.min_days <= days_overdue <= b.max_days:
                return b.name
        elif b.min_days is not None and b.max_days is None:
            if days_overdue >= b.min_days:
                return b.name

    return "120+"


def calculate_aging_totals(items: Sequence[AgingItem]) -> AgingTotals:
    """Sum totals for each aging bucket and overall outstanding balance."""
    total_current = Decimal("0.00")
    total_1_30 = Decimal("0.00")
    total_31_60 = Decimal("0.00")
    total_61_90 = Decimal("0.00")
    total_91_120 = Decimal("0.00")
    total_120_plus = Decimal("0.00")
    total_outstanding = Decimal("0.00")

    for item in items:
        total_outstanding += item.outstanding_amount
        if item.bucket == "current":
            total_current += item.outstanding_amount
        elif item.bucket == "1-30":
            total_1_30 += item.outstanding_amount
        elif item.bucket == "31-60":
            total_31_60 += item.outstanding_amount
        elif item.bucket == "61-90":
            total_61_90 += item.outstanding_amount
        elif item.bucket == "91-120":
            total_91_120 += item.outstanding_amount
        elif item.bucket == "120+":
            total_120_plus += item.outstanding_amount

    return AgingTotals(
        total_current=total_current,
        total_1_30=total_1_30,
        total_31_60=total_31_60,
        total_61_90=total_61_90,
        total_91_120=total_91_120,
        total_120_plus=total_120_plus,
        total_outstanding=total_outstanding,
    )
