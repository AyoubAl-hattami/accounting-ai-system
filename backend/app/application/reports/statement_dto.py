from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PartnerStatementQuery:
    company_id: int
    partner_id: int
    currency: str
    date_from: date
    date_to: date


@dataclass(frozen=True, slots=True)
class StatementTransactionItem:
    date: date
    type: str  # "invoice" or "payment"
    document_no: str
    reference: str | None
    description: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


@dataclass(frozen=True, slots=True)
class PartnerStatementRead:
    company_id: int
    partner_id: int
    partner_name: str
    partner_code: str
    partner_type: str  # "customer", "vendor", or "both"
    currency: str
    date_from: date
    date_to: date
    opening_balance: Decimal
    transactions: list[StatementTransactionItem]
    closing_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
