"""
Accounting Tool Registry for Unified Gemini Agent.

Defines all callable tools as Gemini FunctionDeclarations with strict schemas,
enforces tenant isolation and RBAC permissions, and executes tool logic safely.

Tools are split into:
1. READ TOOLS: Directly executed against live database after role check.
2. WRITE / MUTATING TOOLS: Build a validated proposal draft with a confirmation
   requirement. Never mutates database directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from google.genai import types
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.accounting.models.account import Account as AccountModel
from app.modules.accounting.models.audit_log import AuditLog as AuditLogModel
from app.modules.accounting.models.company_user import CompanyUser as CompanyUserModel
from app.modules.accounting.models.credit_note import (
    CreditNote as CreditNoteModel,
    CreditNoteAllocation as CreditNoteAllocationModel,
    CreditNoteLine as CreditNoteLineModel,
)
from app.modules.accounting.models.invoice import Invoice as InvoiceModel, InvoiceLine as InvoiceLineModel
from app.modules.accounting.models.journal_entry import JournalEntry as JournalEntryModel
from app.modules.accounting.models.journal_line import JournalLine as JournalLineModel
from app.modules.accounting.models.payment import Payment as PaymentModel, PaymentAllocation as PaymentAllocationModel
from app.modules.accounting.models.refund import Refund as RefundModel
from app.modules.accounting.schemas.gemini_assistant_schemas import (
    SuggestedAction,
    SuggestedJournalLine,
    SuggestedJournalPayload,
)
from app.modules.accounting.services.ai_accounting_application_facade import (
    get_account,
    list_accounts,
    list_journal_entries,
)
# The permission vocabulary is imported, never restated.
#
# This module used to define its own four _CAN_* sets, and they had drifted
# wider than the ones every other path uses: a viewer could read every member's
# email and an accountant could read the audit log through the assistant, both
# of which REST answers with 403. A second copy of a role set is not a
# duplicate that eventually diverges -- it is a duplicate that already had.
from app.modules.accounting.services.assistant_handler_registry import (
    _CAN_CREATE_DRAFT,
    _CAN_READ_AUDIT_LOGS,
    _CAN_READ_CREDIT_NOTES,
    _CAN_READ_REPORTS,
    _CAN_READ_SUBLEDGER,
    _CAN_READ_USERS,
)
from app.modules.accounting.services.company_user_service import list_company_users
from app.modules.accounting.services.reports_application_facade import (
    get_account_ledger,
    get_balance_sheet,
    get_general_ledger,
    get_profit_and_loss,
    get_trial_balance,
)
from app.application.reports.aging_dto import AgingQuery
from app.application.reports.statement_dto import PartnerStatementQuery
from app.application.reports.use_cases import GetAgingReport, GetPartnerStatement
from app.infrastructure.database.sqlalchemy.repositories.report_repository import SqlAlchemyReportRepository

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionResult:
    data: Any
    is_mutation_proposal: bool = False
    suggested_action: SuggestedAction | None = None
    data_source: str = "database"
    error: str | None = None


# ── 1. Read Tools Implementation ──────────────────────────────────────────────

def tool_get_profit_loss(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    report = get_profit_and_loss(db=db, company_id=company_id, start_date=sd, end_date=ed)
    return {
        "total_revenue": float(report.total_income),
        "total_expenses": float(report.total_expenses),
        "net_profit": float(report.net_profit),
        "currency": report.currency,
        "revenue_lines": [
            {"account_name": l.account_name, "account_code": l.account_code, "amount": float(l.amount)}
            for l in report.income_lines if float(l.amount) != 0
        ][:15],
        "expense_lines": [
            {"account_name": l.account_name, "account_code": l.account_code, "amount": float(l.amount)}
            for l in report.expense_lines if float(l.amount) != 0
        ][:15],
    }


def tool_get_balance_sheet(db: Session, company_id: int, as_of_date: str | None = None) -> dict[str, Any]:
    bs = get_balance_sheet(db=db, company_id=company_id)
    return {
        "total_assets": float(bs.total_assets),
        "total_liabilities": float(bs.total_liabilities),
        "total_equity": float(bs.total_equity),
        "is_balanced": bs.is_balanced,
        "currency": bs.currency,
        "asset_lines": [
            {"account_name": l.account_name, "account_code": l.account_code, "amount": float(l.amount)}
            for l in bs.asset_lines if float(l.amount) != 0
        ][:15],
        "liability_lines": [
            {"account_name": l.account_name, "account_code": l.account_code, "amount": float(l.amount)}
            for l in bs.liability_lines if float(l.amount) != 0
        ][:15],
        "equity_lines": [
            {"account_name": l.account_name, "account_code": l.account_code, "amount": float(l.amount)}
            for l in bs.equity_lines if float(l.amount) != 0
        ][:15],
    }


def tool_get_trial_balance(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    tb = get_trial_balance(db=db, company_id=company_id, start_date=sd, end_date=ed)
    return {
        "total_debit": float(tb.total_debit),
        "total_credit": float(tb.total_credit),
        "is_balanced": tb.is_balanced,
        "currency": tb.currency,
        "accounts": [
            {
                "code": a.account_code,
                "name": a.account_name,
                "debit": float(a.debit),
                "credit": float(a.credit),
            }
            for a in tb.accounts if (float(a.debit) != 0 or float(a.credit) != 0)
        ][:30],
    }


def tool_get_account_ledger(
    db: Session, company_id: int, account_identifier: str, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    # Resolve account by code or name
    acc = db.scalars(
        select(AccountModel).where(
            AccountModel.company_id == company_id,
            or_(
                AccountModel.code == account_identifier.strip(),
                AccountModel.name.ilike(f"%{account_identifier.strip()}%"),
            ),
        )
    ).first()
    if not acc:
        return {"error": f"Account '{account_identifier}' not found in company chart of accounts."}

    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    ledger = get_account_ledger(db=db, company_id=company_id, account_id=acc.id, start_date=sd, end_date=ed)
    return {
        "account_id": acc.id,
        "account_code": acc.code,
        "account_name": acc.name,
        "currency": acc.currency,
        "opening_balance": float(ledger.opening_balance),
        "closing_balance": float(ledger.closing_balance),
        "total_debit": float(ledger.total_debit),
        "total_credit": float(ledger.total_credit),
        "entries": [
            {
                "entry_no": e.entry_no,
                "date": str(e.entry_date),
                "description": e.description,
                "debit": float(e.debit),
                "credit": float(e.credit),
                "running_balance": float(e.running_balance),
            }
            for e in ledger.lines[:20]
        ],
    }


def tool_get_general_ledger(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    gl = get_general_ledger(db=db, company_id=company_id, start_date=sd, end_date=ed)
    return {
        "total_debit": float(gl.total_debit),
        "total_credit": float(gl.total_credit),
        "accounts_count": len(gl.accounts),
        "accounts": [
            {
                "code": a.account_code,
                "name": a.account_name,
                "opening_balance": float(a.opening_balance),
                "closing_balance": float(a.closing_balance),
            }
            for a in gl.accounts[:20]
        ],
    }


def tool_get_accounts(
    db: Session, company_id: int, search: str | None = None, account_type: str | None = None
) -> list[dict[str, Any]]:
    accounts = list_accounts(db=db, company_id=company_id, limit=200)
    result = []
    s = search.lower().strip() if search else None
    t = account_type.lower().strip() if account_type else None
    for a in accounts:
        if s and (s not in a.code.lower() and s not in a.name.lower()):
            continue
        if t and (t != a.account_type.lower()):
            continue
        result.append({
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "account_type": a.account_type,
            "currency": a.currency,
            "is_active": a.is_active,
        })
    return result[:50]


def tool_get_journal_entries(
    db: Session, company_id: int, entry_no: str | None = None, status: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    entries = list_journal_entries(db=db, company_id=company_id, status=status, limit=min(limit, 50))
    result = []
    e_no = entry_no.strip() if entry_no else None
    for e in entries:
        if e_no and e_no != e.entry_no:
            continue
        result.append({
            "id": e.id,
            "entry_no": e.entry_no,
            "entry_date": str(e.entry_date),
            "description": e.description,
            "status": e.status,
            "total_debit": float(sum(l.debit for l in e.lines)),
            "total_credit": float(sum(l.credit for l in e.lines)),
        })
    return result


def tool_trace_amount(
    db: Session, company_id: int, amount: float, account_hint: str | None = None
) -> list[dict[str, Any]]:
    target = Decimal(str(amount))
    line_match = or_(JournalLineModel.debit == target, JournalLineModel.credit == target)
    stmt = (
        select(JournalEntryModel)
        .join(JournalLineModel, JournalLineModel.journal_entry_id == JournalEntryModel.id)
        .where(
            JournalEntryModel.company_id == company_id,
            JournalLineModel.company_id == company_id,
            line_match,
        )
        .distinct()
        .order_by(JournalEntryModel.entry_date.desc())
        .limit(10)
    )
    entries = list(db.scalars(stmt).all())
    result = []
    for e in entries:
        matched_lines = [l for l in e.lines if l.debit == target or l.credit == target]
        result.append({
            "entry_no": e.entry_no,
            "entry_date": str(e.entry_date),
            "description": e.description,
            "status": e.status,
            "matched_amount": float(target),
            "total_amount": float(sum(l.debit for l in e.lines)),
            "match_side": "debit" if any(l.debit == target for l in matched_lines) else "credit",
        })
    return result


def tool_get_audit_logs(
    db: Session, company_id: int, action: str | None = None, entity_type: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    stmt = select(AuditLogModel).where(AuditLogModel.company_id == company_id)
    if action:
        stmt = stmt.where(AuditLogModel.action == action.strip())
    if entity_type:
        stmt = stmt.where(AuditLogModel.entity_type == entity_type.strip())
    stmt = stmt.order_by(AuditLogModel.created_at.desc()).limit(min(limit, 30))
    logs = list(db.scalars(stmt).all())
    return [
        {
            "action": l.action,
            "actor": l.actor_name or l.actor_email or l.actor,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "description": l.description,
        }
        for l in logs
    ]


def tool_get_company_users(db: Session, company_id: int) -> list[dict[str, Any]]:
    users = list_company_users(db=db, company_id=company_id)
    return [
        {
            "role": u.role,
            "is_active": u.is_active,
            "name": u.user.full_name if hasattr(u, "user") and u.user else None,
            "email": u.user.email if hasattr(u, "user") and u.user else None,
        }
        for u in users
    ]


def tool_get_invoices(
    db: Session,
    company_id: int,
    partner_id: int | None = None,
    invoice_type: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(InvoiceModel).where(InvoiceModel.company_id == company_id)
    if partner_id:
        stmt = stmt.where(InvoiceModel.partner_id == partner_id)
    if invoice_type:
        stmt = stmt.where(InvoiceModel.invoice_type == invoice_type.strip())
    if status:
        stmt = stmt.where(InvoiceModel.status == status.strip())
    stmt = stmt.order_by(InvoiceModel.created_at.desc()).limit(min(limit, 30))
    invoices = list(db.scalars(stmt).all())
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_no,
            "partner_id": inv.partner_id,
            "invoice_type": inv.invoice_type,
            "status": inv.status,
            "currency": inv.currency,
            "total_amount": float(inv.total_amount),
            "paid_amount": float(inv.paid_amount),
            "outstanding_amount": float(inv.residual_amount),
            "issue_date": str(inv.issue_date),
            "due_date": str(inv.due_date),
        }
        for inv in invoices
    ]


def tool_get_invoice_details(
    db: Session,
    company_id: int,
    invoice_id: int | None = None,
    invoice_number: str | None = None,
) -> dict[str, Any]:
    stmt = select(InvoiceModel).where(InvoiceModel.company_id == company_id)
    if invoice_id is not None:
        stmt = stmt.where(InvoiceModel.id == invoice_id)
    elif invoice_number:
        stmt = stmt.where(InvoiceModel.invoice_no == invoice_number.strip())
    inv = db.scalars(stmt).first()
    if not inv:
        return {"error": f"Invoice '{invoice_number or invoice_id}' not found in company."}

    lines = list(db.scalars(select(InvoiceLineModel).where(InvoiceLineModel.invoice_id == inv.id)).all())
    allocs = list(db.scalars(select(PaymentAllocationModel).where(PaymentAllocationModel.invoice_id == inv.id)).all())
    try:
        credit_allocs = list(
            db.scalars(select(CreditNoteAllocationModel).where(CreditNoteAllocationModel.invoice_id == inv.id)).all()
        )
    except Exception as exc:
        logger.warning(f"Could not load credit allocations for invoice {inv.id}: {exc}")
        credit_allocs = []

    return {
        "id": inv.id,
        "invoice_number": inv.invoice_no,
        "partner_id": inv.partner_id,
        "invoice_type": inv.invoice_type,
        "status": inv.status,
        "currency": inv.currency,
        "subtotal": float(inv.subtotal),
        "tax_amount": float(inv.tax_amount),
        "total_amount": float(inv.total_amount),
        "original_amount": float(inv.total_amount),
        "paid_amount": float(inv.paid_amount),
        "credited_amount": float(inv.credited_amount),
        "outstanding_amount": float(inv.residual_amount),
        "issue_date": str(inv.issue_date),
        "due_date": str(inv.due_date),
        "lines": [
            {
                "description": l.description,
                "quantity": float(l.quantity),
                "unit_price": float(l.unit_price),
                "subtotal": float(l.subtotal),
            }
            for l in lines
        ],
        "allocations": [
            {
                "payment_id": a.payment_id,
                "allocated_amount": float(a.amount),
                "allocation_date": str(a.created_at.date()) if a.created_at else None,
            }
            for a in allocs
        ],
        "credit_allocations": [
            {
                "credit_note_id": ca.credit_note_id,
                "allocated_amount": float(ca.amount),
                "allocation_date": str(ca.created_at.date()) if ca.created_at else None,
            }
            for ca in credit_allocs
        ],
    }


def tool_get_credit_notes(
    db: Session,
    company_id: int,
    partner_id: int | None = None,
    note_type: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(CreditNoteModel).where(CreditNoteModel.company_id == company_id)
    if partner_id:
        stmt = stmt.where(CreditNoteModel.partner_id == partner_id)
    if note_type:
        stmt = stmt.where(CreditNoteModel.note_type == note_type.strip())
    if status:
        stmt = stmt.where(CreditNoteModel.status == status.strip())
    stmt = stmt.order_by(CreditNoteModel.created_at.desc()).limit(min(limit, 30))
    cns = list(db.scalars(stmt).all())
    return [
        {
            "id": c.id,
            "credit_note_no": c.credit_note_no,
            "partner_id": c.partner_id,
            "note_type": c.note_type,
            "status": c.status,
            "currency": c.currency,
            "total_amount": float(c.total_amount),
            "allocated_amount": float(c.allocated_amount),
            "unallocated_amount": float(c.unallocated_amount),
            "reason": c.reason,
            "issue_date": str(c.issue_date),
        }
        for c in cns
    ]


def tool_get_credit_note_details(
    db: Session,
    company_id: int,
    credit_note_id: int | None = None,
    credit_note_no: str | None = None,
) -> dict[str, Any]:
    stmt = select(CreditNoteModel).where(CreditNoteModel.company_id == company_id)
    if credit_note_id is not None:
        stmt = stmt.where(CreditNoteModel.id == credit_note_id)
    elif credit_note_no:
        stmt = stmt.where(CreditNoteModel.credit_note_no == credit_note_no.strip())
    cn = db.scalars(stmt).first()
    if not cn:
        return {"error": f"Credit/Debit note '{credit_note_no or credit_note_id}' not found in company."}

    lines = list(db.scalars(select(CreditNoteLineModel).where(CreditNoteLineModel.credit_note_id == cn.id)).all())
    allocs = list(
        db.scalars(select(CreditNoteAllocationModel).where(CreditNoteAllocationModel.credit_note_id == cn.id)).all()
    )

    return {
        "id": cn.id,
        "credit_note_no": cn.credit_note_no,
        "partner_id": cn.partner_id,
        "note_type": cn.note_type,
        "status": cn.status,
        "currency": cn.currency,
        "subtotal": float(cn.subtotal),
        "tax_amount": float(cn.tax_amount),
        "total_amount": float(cn.total_amount),
        "allocated_amount": float(cn.allocated_amount),
        "unallocated_amount": float(cn.unallocated_amount),
        "reason": cn.reason,
        "issue_date": str(cn.issue_date),
        "lines": [
            {
                "description": l.description,
                "quantity": float(l.quantity),
                "unit_price": float(l.unit_price),
                "subtotal": float(l.subtotal),
            }
            for l in lines
        ],
        "allocations": [
            {
                "invoice_id": a.invoice_id,
                "allocated_amount": float(a.amount),
                "allocation_date": str(a.created_at.date()) if a.created_at else None,
            }
            for a in allocs
        ],
    }


def tool_get_refunds(
    db: Session,
    company_id: int,
    partner_id: int | None = None,
    refund_type: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(RefundModel).where(RefundModel.company_id == company_id)
    if partner_id:
        stmt = stmt.where(RefundModel.partner_id == partner_id)
    if refund_type:
        stmt = stmt.where(RefundModel.refund_type == refund_type.strip())
    if status:
        stmt = stmt.where(RefundModel.status == status.strip())
    stmt = stmt.order_by(RefundModel.created_at.desc()).limit(min(limit, 30))
    refunds = list(db.scalars(stmt).all())
    return [
        {
            "id": r.id,
            "partner_id": r.partner_id,
            "refund_type": r.refund_type,
            "status": r.status,
            "currency": r.currency_code,
            "amount": float(r.amount),
            "refund_date": str(r.refund_date),
            "reference": r.reference,
            "memo": r.memo,
        }
        for r in refunds
    ]


def tool_get_payments(
    db: Session,
    company_id: int,
    partner_id: int | None = None,
    payment_type: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(PaymentModel).where(PaymentModel.company_id == company_id)
    if partner_id:
        stmt = stmt.where(PaymentModel.partner_id == partner_id)
    if payment_type:
        stmt = stmt.where(PaymentModel.payment_type == payment_type.strip())
    if status:
        stmt = stmt.where(PaymentModel.status == status.strip())
    stmt = stmt.order_by(PaymentModel.created_at.desc()).limit(min(limit, 30))
    payments = list(db.scalars(stmt).all())
    return [
        {
            "id": p.id,
            "reference": p.reference,
            "partner_id": p.partner_id,
            "payment_type": p.payment_type,
            "status": p.status,
            "currency": p.currency_code,
            "amount": float(p.amount),
            "memo": p.memo,
            "payment_date": str(p.payment_date),
        }
        for p in payments
    ]


def tool_get_ar_aging(db: Session, company_id: int, as_of_date: str | None = None, partner_id: int | None = None) -> dict[str, Any]:
    ref_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    repo = SqlAlchemyReportRepository(db)
    report = GetAgingReport(repo).execute(
        AgingQuery(company_id=company_id, report_type="ar", as_of_date=ref_date, currency="", partner_id=partner_id)
    )
    return {
        "as_of_date": str(report.as_of_date),
        "total_outstanding": float(report.totals.total_outstanding),
        "buckets": {
            "current": float(report.totals.total_current),
            "1_30_days": float(report.totals.total_1_30),
            "31_60_days": float(report.totals.total_31_60),
            "61_90_days": float(report.totals.total_61_90),
            "over_90_days": float(report.totals.total_91_120 + report.totals.total_120_plus),
        },
        "items_count": len(report.items),
    }


def tool_get_ap_aging(db: Session, company_id: int, as_of_date: str | None = None, partner_id: int | None = None) -> dict[str, Any]:
    ref_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
    repo = SqlAlchemyReportRepository(db)
    report = GetAgingReport(repo).execute(
        AgingQuery(company_id=company_id, report_type="ap", as_of_date=ref_date, currency="", partner_id=partner_id)
    )
    return {
        "as_of_date": str(report.as_of_date),
        "total_outstanding": float(report.totals.total_outstanding),
        "buckets": {
            "current": float(report.totals.total_current),
            "1_30_days": float(report.totals.total_1_30),
            "31_60_days": float(report.totals.total_31_60),
            "61_90_days": float(report.totals.total_61_90),
            "over_90_days": float(report.totals.total_91_120 + report.totals.total_120_plus),
        },
        "items_count": len(report.items),
    }


def tool_get_customer_statement(
    db: Session, company_id: int, partner_id: int, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    sd = date.fromisoformat(start_date) if start_date else date(date.today().year, 1, 1)
    ed = date.fromisoformat(end_date) if end_date else date.today()
    repo = SqlAlchemyReportRepository(db)
    stmt = GetPartnerStatement(repo).execute(
        PartnerStatementQuery(company_id=company_id, partner_id=partner_id, currency="", date_from=sd, date_to=ed)
    )
    return {
        "partner_id": stmt.partner_id,
        "partner_name": stmt.partner_name,
        "currency": stmt.currency,
        "opening_balance": float(stmt.opening_balance),
        "closing_balance": float(stmt.closing_balance),
        "total_debit": float(stmt.total_debit),
        "total_credit": float(stmt.total_credit),
        "transactions_count": len(stmt.transactions),
    }


def tool_get_vendor_statement(
    db: Session, company_id: int, partner_id: int, start_date: str | None = None, end_date: str | None = None
) -> dict[str, Any]:
    return tool_get_customer_statement(db, company_id, partner_id, start_date, end_date)


# ── 2. Write / Proposal Tools (Confirmation Mandatory) ────────────────────────

def tool_propose_journal_entry(
    db: Session,
    company_id: int,
    debit_account: str,
    credit_account: str,
    amount: float,
    description: str,
    entry_date: str | None = None,
) -> ToolExecutionResult:
    # Resolve debit account
    d_acc = db.scalars(
        select(AccountModel).where(
            AccountModel.company_id == company_id,
            or_(AccountModel.code == debit_account.strip(), AccountModel.name.ilike(f"%{debit_account.strip()}%")),
        )
    ).first()

    # Resolve credit account
    c_acc = db.scalars(
        select(AccountModel).where(
            AccountModel.company_id == company_id,
            or_(AccountModel.code == credit_account.strip(), AccountModel.name.ilike(f"%{credit_account.strip()}%")),
        )
    ).first()

    if not d_acc:
        return ToolExecutionResult(
            data={"error": f"Debit account '{debit_account}' not found."},
            error=f"Debit account '{debit_account}' not found.",
        )
    if not c_acc:
        return ToolExecutionResult(
            data={"error": f"Credit account '{credit_account}' not found."},
            error=f"Credit account '{credit_account}' not found.",
        )

    action = SuggestedAction(
        type="create_journal_entry_draft",
        requires_confirmation=True,
        payload=SuggestedJournalPayload(
            entry_date=date.fromisoformat(entry_date) if entry_date else date.today(),
            description=description,
            amount=amount,
            lines=[
                SuggestedJournalLine(
                    account_id=d_acc.id,
                    account_name=d_acc.name,
                    account_code=d_acc.code,
                    debit=Decimal(str(amount)),
                    credit=Decimal("0.00"),
                    description=description,
                ),
                SuggestedJournalLine(
                    account_id=c_acc.id,
                    account_name=c_acc.name,
                    account_code=c_acc.code,
                    debit=Decimal("0.00"),
                    credit=Decimal(str(amount)),
                    description=description,
                ),
            ],
        ),
    )

    return ToolExecutionResult(
        data={
            "status": "proposal_created",
            "message": "Draft journal entry prepared. Requires user confirmation.",
            "debit_account": f"{d_acc.code} - {d_acc.name}",
            "credit_account": f"{c_acc.code} - {c_acc.name}",
            "amount": amount,
            "description": description,
        },
        is_mutation_proposal=True,
        suggested_action=action,
        data_source="action_draft",
    )


# ── Registry Definition ───────────────────────────────────────────────────────

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_profit_loss",
        description="Get Profit and Loss financial report with total income, total expenses, net profit, and breakdown lines.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD (optional)"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_balance_sheet",
        description="Get Balance Sheet report with assets, liabilities, equity totals and line breakdowns.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "as_of_date": types.Schema(type="STRING", description="As-of date YYYY-MM-DD (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_trial_balance",
        description="Get Trial Balance with debit and credit totals and account balances.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD (optional)"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_account_ledger",
        description="Get detailed ledger movements, running balances, and journal lines for a specific account.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "account_identifier": types.Schema(type="STRING", description="Account code (e.g. '1010') or account name"),
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD (optional)"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD (optional)"),
            },
            required=["account_identifier"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_general_ledger",
        description="Get summary of all account balances and total debits/credits in General Ledger.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD (optional)"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_accounts",
        description="Search or list company chart of accounts by name, code, or account_type (asset, liability, equity, income, expense).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "search": types.Schema(type="STRING", description="Search substring in account code or name"),
                "account_type": types.Schema(type="STRING", description="Account type filter: asset, liability, equity, income, expense"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_journal_entries",
        description="List recent journal entries or find a specific entry by number.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "entry_no": types.Schema(type="STRING", description="Specific journal entry number (optional)"),
                "status": types.Schema(type="STRING", description="Status filter: posted, draft, void"),
                "limit": types.Schema(type="INTEGER", description="Max entries to return (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="trace_amount",
        description="Find journal entries containing an exact monetary amount in debit or credit.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "amount": types.Schema(type="NUMBER", description="Monetary amount to trace"),
                "account_hint": types.Schema(type="STRING", description="Optional account name hint"),
            },
            required=["amount"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_audit_logs",
        description="Query system audit logs to see who performed actions (posting, creating, updating).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "action": types.Schema(type="STRING", description="Audit action filter: post_journal_entry, create_journal_entry, etc."),
                "entity_type": types.Schema(type="STRING", description="Entity type: journal_entry, invoice, payment"),
                "limit": types.Schema(type="INTEGER", description="Max logs (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_company_users",
        description="List active users and their roles in the current company.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="get_invoices",
        description="List sales or purchase invoices with status and outstanding balances.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Filter by customer or vendor partner ID"),
                "invoice_type": types.Schema(type="STRING", description="sales_invoice or purchase_invoice"),
                "status": types.Schema(type="STRING", description="draft, posted, void"),
                "limit": types.Schema(type="INTEGER", description="Max invoices (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_invoice_details",
        description="Get full invoice details including total amount, paid amount, outstanding balance, lines, and payment allocations.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "invoice_id": types.Schema(type="INTEGER", description="Invoice ID (optional)"),
                "invoice_number": types.Schema(type="STRING", description="Invoice number e.g. 'INV-2026-001' (optional)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_payments",
        description="List customer receipts or vendor payments.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Filter by partner ID"),
                "payment_type": types.Schema(type="STRING", description="customer_receipt or vendor_payment"),
                "status": types.Schema(type="STRING", description="draft, posted, void"),
                "limit": types.Schema(type="INTEGER", description="Max payments (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_ar_aging",
        description="Get Accounts Receivable Aging report showing overdue customer balances grouped by aging buckets.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "as_of_date": types.Schema(type="STRING", description="Aging cutoff date YYYY-MM-DD"),
                "partner_id": types.Schema(type="INTEGER", description="Optional partner ID"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_ap_aging",
        description="Get Accounts Payable Aging report showing overdue vendor balances grouped by aging buckets.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "as_of_date": types.Schema(type="STRING", description="Aging cutoff date YYYY-MM-DD"),
                "partner_id": types.Schema(type="INTEGER", description="Optional partner ID"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_customer_statement",
        description="Get Customer Account Statement showing invoices, receipts, and running balance.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Customer Partner ID"),
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD"),
            },
            required=["partner_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_vendor_statement",
        description="Get Vendor Account Statement showing bills, payments, and running balance.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Vendor Partner ID"),
                "start_date": types.Schema(type="STRING", description="Start date YYYY-MM-DD"),
                "end_date": types.Schema(type="STRING", description="End date YYYY-MM-DD"),
            },
            required=["partner_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_credit_notes",
        description="Get Credit Notes and Debit Notes for a company with optional filters.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Optional partner ID"),
                "note_type": types.Schema(
                    type="STRING",
                    description="customer_credit_note (Sales Credit Note) or vendor_debit_note (Purchase Debit Note)",
                ),
                "status": types.Schema(type="STRING", description="draft, posted, void"),
                "limit": types.Schema(type="INTEGER", description="Max documents (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_credit_note_details",
        description="Get complete details of a Credit or Debit Note including lines and invoice allocations.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "credit_note_id": types.Schema(type="INTEGER", description="Credit note ID"),
                "credit_note_no": types.Schema(type="STRING", description="Credit note number e.g. CN-001"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="get_refunds",
        description="Get Customer or Vendor Refunds with optional filters.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "partner_id": types.Schema(type="INTEGER", description="Optional partner ID"),
                "refund_type": types.Schema(
                    type="STRING",
                    description="customer_refund or vendor_refund",
                ),
                "status": types.Schema(type="STRING", description="draft, posted, void"),
                "limit": types.Schema(type="INTEGER", description="Max refunds (default 10)"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="propose_journal_entry",
        description="Propose a new draft journal entry. Does not post or write directly; prepares a validated draft for user confirmation.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "debit_account": types.Schema(type="STRING", description="Debit account code or name"),
                "credit_account": types.Schema(type="STRING", description="Credit account code or name"),
                "amount": types.Schema(type="NUMBER", description="Entry amount"),
                "description": types.Schema(type="STRING", description="Entry description"),
                "entry_date": types.Schema(type="STRING", description="Entry date YYYY-MM-DD (optional)"),
            },
            required=["debit_account", "credit_account", "amount", "description"],
        ),
    ),
]


class AccountingToolRegistry:
    """Registry that maps tool names to handlers with RBAC and tenant enforcement."""

    _HANDLERS: dict[str, tuple[Callable[..., Any], frozenset[str], bool]] = {
        "get_profit_loss": (tool_get_profit_loss, _CAN_READ_REPORTS, False),
        "get_balance_sheet": (tool_get_balance_sheet, _CAN_READ_REPORTS, False),
        "get_trial_balance": (tool_get_trial_balance, _CAN_READ_REPORTS, False),
        "get_account_ledger": (tool_get_account_ledger, _CAN_READ_REPORTS, False),
        "get_general_ledger": (tool_get_general_ledger, _CAN_READ_REPORTS, False),
        "get_accounts": (tool_get_accounts, _CAN_READ_REPORTS, False),
        "get_journal_entries": (tool_get_journal_entries, _CAN_READ_REPORTS, False),
        "trace_amount": (tool_trace_amount, _CAN_READ_REPORTS, False),
        "get_audit_logs": (tool_get_audit_logs, _CAN_READ_AUDIT_LOGS, False),
        "get_company_users": (tool_get_company_users, _CAN_READ_USERS, False),
        "get_invoices": (tool_get_invoices, _CAN_READ_SUBLEDGER, False),
        "get_invoice_details": (tool_get_invoice_details, _CAN_READ_SUBLEDGER, False),
        "get_payments": (tool_get_payments, _CAN_READ_SUBLEDGER, False),
        # Aging and partner statements keep the reports set: their REST routes
        # take no allowed_roles, so every member can already read them there.
        "get_ar_aging": (tool_get_ar_aging, _CAN_READ_REPORTS, False),
        "get_ap_aging": (tool_get_ap_aging, _CAN_READ_REPORTS, False),
        "get_customer_statement": (tool_get_customer_statement, _CAN_READ_REPORTS, False),
        "get_vendor_statement": (tool_get_vendor_statement, _CAN_READ_REPORTS, False),
        "get_credit_notes": (tool_get_credit_notes, _CAN_READ_CREDIT_NOTES, False),
        "get_credit_note_details": (tool_get_credit_note_details, _CAN_READ_CREDIT_NOTES, False),
        "get_refunds": (tool_get_refunds, _CAN_READ_CREDIT_NOTES, False),
        "propose_journal_entry": (tool_propose_journal_entry, _CAN_CREATE_DRAFT, True),
    }

    @classmethod
    def get_tool_declarations_for_role(cls, user_role: str) -> list[types.FunctionDeclaration]:
        """Return allowlisted tool declarations based on user role."""
        allowed_declarations = []
        for decl in TOOL_DECLARATIONS:
            entry = cls._HANDLERS.get(decl.name)
            if entry and user_role in entry[1]:
                allowed_declarations.append(decl)
        return allowed_declarations

    @classmethod
    def execute_tool(
        cls,
        tool_name: str,
        args: dict[str, Any],
        db: Session,
        company_id: int,
        user_role: str,
    ) -> ToolExecutionResult:
        """Execute a tool with strict RBAC and tenant enforcement."""
        entry = cls._HANDLERS.get(tool_name)
        if not entry:
            return ToolExecutionResult(
                data={"error": f"Unknown tool '{tool_name}'"},
                error=f"Unknown tool '{tool_name}'",
            )

        handler, allowed_roles, is_proposal = entry
        if user_role not in allowed_roles:
            return ToolExecutionResult(
                data={"error": "Access denied. Insufficient permissions for this tool."},
                error="Access denied.",
            )

        # Force company_id from auth context (never allow model override)
        clean_args = {k: v for k, v in args.items() if k != "company_id"}

        try:
            raw_result = handler(db=db, company_id=company_id, **clean_args)
            if isinstance(raw_result, ToolExecutionResult):
                return raw_result
            return ToolExecutionResult(data=raw_result, is_mutation_proposal=is_proposal)
        except Exception as exc:
            logger.error("Error executing tool %s: %s", tool_name, exc, exc_info=True)
            return ToolExecutionResult(
                data={"error": f"Error executing {tool_name}: {exc}"},
                error=str(exc),
            )
