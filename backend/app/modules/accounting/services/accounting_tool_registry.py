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
from pydantic import BaseModel
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
# The trace query and the evidence card, from the deterministic path. One
# definition of each: see tool_trace_amount for why a second was worse than
# an import of the module that owns them.
from app.modules.accounting.services.gemini_assistant_service import (
    _build_journal_evidence,
    _tool_trace_amount,
)
from app.modules.accounting.services.reports_application_facade import (
    get_account_ledger,
    get_balance_sheet,
    get_general_ledger,
    get_profit_and_loss,
    get_trial_balance,
)
from app.core.clock import get_today_date
from app.modules.accounting.services.report_grounding import (
    account_ledger_grounding,
    account_totals,
    balance_sheet_grounding,
    general_ledger_grounding,
    profit_and_loss_grounding,
    trial_balance_grounding,
)
from app.application.reports.policies import REPORTABLE_ENTRY_STATUSES
from app.application.reports.aging_dto import AgingQuery
from app.application.reports.statement_dto import PartnerStatementQuery
from app.application.reports.use_cases import GetAgingReport, GetPartnerStatement
from app.infrastructure.database.sqlalchemy.repositories.report_repository import SqlAlchemyReportRepository

logger = logging.getLogger(__name__)

# How many ledger lines a tool result carries. The model reads these; a longer
# list costs tokens without adding evidence, and the count of what was left
# out travels with it.
_LEDGER_LINES_SHOWN = 20

# The general ledger card shows 20 accounts; the payload matches it, so the
# model and the card describe the same page.
_GENERAL_LEDGER_ACCOUNTS_SHOWN = 20


def _lifecycle_envelope(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a lifecycle listing with what the statuses in it mean.

    These two tools list entries at every status, which is deliberate and
    matches the deterministic handlers: a user asking what happened to an
    entry has to be able to see that it was voided. What was missing is the
    consequence -- a draft is a real row with a real amount, and nothing in
    the payload said it is not in any report.

    Filtering them out instead was the other option and it is the wrong one
    here: it would answer "what happened to JE-42?" with "no such entry",
    which is worse than a labelled draft. The report tools do filter, because
    they produce figures; these produce a list.
    """
    return {
        "entries": entries,
        "reportable_statuses": list(REPORTABLE_ENTRY_STATUSES),
        "note": (
            "Only entries whose status is in reportable_statuses affect report "
            "totals. An entry with counts_in_reports=false exists but is not "
            "part of any reported figure; state its status when mentioning it, "
            "and never add it to a total."
        ),
    }


@dataclass
class ToolExecutionResult:
    data: Any
    is_mutation_proposal: bool = False
    suggested_action: SuggestedAction | None = None
    data_source: str = "database"
    error: str | None = None
    # The card for this result, built from the DTO the service returned.
    # It travels beside the data, never inside it: the model reads `data`,
    # and this is attached to the reply afterwards, if the gate vouches.
    grounding: BaseModel | None = None


# ── 1. Read Tools Implementation ──────────────────────────────────────────────

def tool_get_profit_loss(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> ToolExecutionResult:
    """The report, flattened for the model, and the card, built from the same
    object. The model gets the first and never sees the second."""
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    report = get_profit_and_loss(db=db, company_id=company_id, start_date=sd, end_date=ed)
    data = {
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
    return ToolExecutionResult(
        data=data,
        grounding=profit_and_loss_grounding(report, start_date=sd, end_date=ed),
    )


def tool_get_balance_sheet(
    db: Session, company_id: int, as_of_date: str | None = None
) -> ToolExecutionResult:
    """The balance sheet as of a date, and the card for it.

    as_of_date was accepted and dropped: the call went out with no date at
    all, so "what did we own at the end of March?" was answered with today's
    figures and nothing said otherwise. The deterministic path has always
    passed it.
    """
    as_of = date.fromisoformat(as_of_date) if as_of_date else get_today_date()
    bs = get_balance_sheet(db=db, company_id=company_id, as_of_date=as_of)
    data = {
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
        "as_of_date": bs.as_of_date.isoformat() if bs.as_of_date else None,
    }
    return ToolExecutionResult(data=data, grounding=balance_sheet_grounding(bs))


def tool_get_trial_balance(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> ToolExecutionResult:
    """The trial balance as of a date, and the card for it.

    Every call to this tool raised TypeError. It passed start_date and
    end_date to a facade whose only parameter is as_of_date, so the model
    received "Error executing get_trial_balance: got an unexpected keyword
    argument 'start_date'" and nothing else, every time.

    A trial balance is cumulative: it has an as-of date and no start. The
    parameters stay because the declaration advertises them, end_date is what
    the report is taken as of, and start_date is accepted and ignored rather
    than silently changing what a caller asked for. The payload says which
    date it answered for.
    """
    as_of = date.fromisoformat(end_date) if end_date else None
    tb = get_trial_balance(db=db, company_id=company_id, as_of_date=as_of)
    data = {
        "total_debit": float(tb.total_debit),
        "total_credit": float(tb.total_credit),
        "is_balanced": tb.is_balanced,
        "currency": tb.currency,
        "as_of_date": tb.as_of_date.isoformat() if tb.as_of_date else None,
        "accounts": [
            {
                "code": line.account_code,
                "name": line.account_name,
                "debit": float(line.debit_balance),
                "credit": float(line.credit_balance),
            }
            for line in tb.lines
            if line.debit_balance != 0 or line.credit_balance != 0
        ][:30],
    }
    return ToolExecutionResult(data=data, grounding=trial_balance_grounding(tb))


def tool_get_account_ledger(
    db: Session, company_id: int, account_identifier: str, start_date: str | None = None, end_date: str | None = None
) -> ToolExecutionResult:
    # Resolve the account, and refuse to guess between several.
    #
    # This matched code OR name-contains and took .first(), so "expense"
    # against a chart with five expense accounts answered about whichever the
    # database returned -- a real ledger for the wrong account, which reads
    # exactly like a real ledger for the right one. An exact code wins
    # outright; otherwise the caller is told what the candidates are, the way
    # the deterministic handler already asks.
    identifier = account_identifier.strip()
    acc = db.scalars(
        select(AccountModel).where(
            AccountModel.company_id == company_id, AccountModel.code == identifier
        )
    ).first()
    if acc is None:
        matches = list(
            db.scalars(
                select(AccountModel)
                .where(
                    AccountModel.company_id == company_id,
                    AccountModel.name.ilike(f"%{identifier}%"),
                )
                .order_by(AccountModel.code.asc())
            ).all()
        )
        if len(matches) > 1:
            return ToolExecutionResult(
                data={
                    "error": (
                        f"'{identifier}' matches {len(matches)} accounts. Ask "
                        "which one is meant, by code."
                    ),
                    "candidates": [
                        {"code": match.code, "name": match.name} for match in matches[:10]
                    ],
                }
            )
        acc = matches[0] if matches else None
    if not acc:
        return ToolExecutionResult(
            data={"error": f"Account '{account_identifier}' not found in company chart of accounts."}
        )

    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    ledger = get_account_ledger(db=db, company_id=company_id, account_id=acc.id, start_date=sd, end_date=ed)
    if ledger is None:
        return ToolExecutionResult(
            data={
                "error": (
                    f"The ledger for account '{acc.code} - {acc.name}' could not be "
                    "produced for that period."
                )
            }
        )

    # Debits and credits are summed from the lines returned, and said so.
    #
    # AccountLedgerRead has no total_debit or total_credit -- reading them is
    # what made every call to this tool raise AttributeError -- and inventing
    # window totals from a page would be worse than not having them: [D3]
    # paginates this report, so `lines` can be a page of a longer window.
    shown = ledger.lines[:_LEDGER_LINES_SHOWN]
    data = {
        "account_id": acc.id,
        "account_code": acc.code,
        "account_name": acc.name,
        # The report's unit, not the account's: [CUR-2] resolves a report to
        # one currency, and that is the unit these figures are in.
        "currency": ledger.currency or acc.currency,
        "opening_balance": float(ledger.opening_balance),
        "closing_balance": float(ledger.closing_balance),
        "period": {"start_date": str(sd) if sd else None, "end_date": str(ed) if ed else None},
        "lines_total": ledger.total_lines,
        "lines_shown": len(shown),
        "debit_of_shown_lines": float(sum(line.debit for line in shown)),
        "credit_of_shown_lines": float(sum(line.credit for line in shown)),
        "truncated": ledger.total_lines > len(shown),
        "entries": [
            {
                "entry_no": line.entry_no,
                "date": str(line.entry_date),
                "description": line.description,
                "debit": float(line.debit),
                "credit": float(line.credit),
                "running_balance": float(line.running_balance),
            }
            for line in shown
        ],
    }
    return ToolExecutionResult(
        data=data,
        grounding=account_ledger_grounding(ledger, acc, start_date=sd, end_date=ed),
    )


def tool_get_general_ledger(
    db: Session, company_id: int, start_date: str | None = None, end_date: str | None = None
) -> ToolExecutionResult:
    """The general ledger, and the card for it.

    Every call raised AttributeError: it read gl.total_debit and
    gl.total_credit, which GeneralLedgerRead does not have. The report is a
    list of accounts, each carrying its own lines, and a total means summing
    them -- which is what the card has always done and what account_totals
    does now, in one place.

    The figures are named for what they cover. [D3] paginates this report, so
    `accounts` can be a page of a longer ledger, and a sum over a page is not
    the ledger's total.
    """
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    gl = get_general_ledger(db=db, company_id=company_id, start_date=sd, end_date=ed)

    shown = gl.accounts[:_GENERAL_LEDGER_ACCOUNTS_SHOWN]
    debit_shown = Decimal("0.00")
    credit_shown = Decimal("0.00")
    rows = []
    for account in shown:
        debit, credit = account_totals(account)
        debit_shown += debit
        credit_shown += credit
        rows.append(
            {
                "code": account.account_code,
                "name": account.account_name,
                "opening_balance": float(account.opening_balance),
                "total_debit": float(debit),
                "total_credit": float(credit),
                "closing_balance": float(account.closing_balance),
                "entry_count": len(account.lines),
            }
        )

    data = {
        "currency": gl.currency,
        "period": {"start_date": start_date, "end_date": end_date},
        "accounts_total": gl.total_accounts or len(gl.accounts),
        "accounts_shown": len(rows),
        "truncated": (gl.total_accounts or len(gl.accounts)) > len(rows),
        "debit_of_shown_accounts": float(debit_shown),
        "credit_of_shown_accounts": float(credit_shown),
        "accounts": rows,
    }
    return ToolExecutionResult(
        data=data,
        grounding=general_ledger_grounding(gl, start_date=sd, end_date=ed),
    )


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
) -> dict[str, Any]:
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
            "counts_in_reports": e.status in REPORTABLE_ENTRY_STATUSES,
            "total_debit": float(sum(l.debit for l in e.lines)),
            "total_credit": float(sum(l.credit for l in e.lines)),
        })
    return _lifecycle_envelope(result)


def tool_trace_amount(
    db: Session, company_id: int, amount: float, account_hint: str | None = None
) -> ToolExecutionResult:
    """Trace an exact amount, and carry the evidence card for what it found.

    The query is the deterministic path's, not a second one. This tool had
    written its own: a join with DISTINCT, ordered by date alone, with no
    actor, no source, no match reason and no total count -- which is most of
    what JournalEvidenceGrounding records, so it could not have produced a
    card at all. The one in gemini_assistant_service orders posted entries
    first, resolves who created and who posted each one, counts the matches
    beyond the page, and says which side matched. Two implementations of
    "find this amount" is one more than a ledger should have.

    account_hint is accepted and ignored, here and in the handler this
    delegates to. It was declared in the tool schema and never read; leaving
    the parameter keeps the declaration honest about what a caller may send
    while the behaviour stays what it has always been.
    """
    target = Decimal(str(amount))
    matches = _tool_trace_amount(
        db=db, company_id=company_id, amount=target, account_hint=account_hint
    )
    if matches is None:
        return ToolExecutionResult(
            data={"error": f"The trace for {target} could not be completed."},
            error="trace_failed",
        )

    entries = [
        {
            "entry_no": match["entry_no"],
            "entry_date": match["entry_date"],
            "description": match["description"],
            "status": match["status"],
            "counts_in_reports": match["status"] in REPORTABLE_ENTRY_STATUSES,
            "matched_amount": match["total_debit"] if match["match_reason"] == "debit_line" else match["total_credit"],
            "total_debit": match["total_debit"],
            "total_credit": match["total_credit"],
            "match_side": "debit" if match["match_reason"] == "debit_line" else "credit",
            "debit_accounts": match["debit_accounts"],
            "credit_accounts": match["credit_accounts"],
            "created_by": match["created_by"],
        }
        for match in matches
    ]
    data = _lifecycle_envelope(entries)
    data["query"] = {"amount": target.quantize(Decimal("0.01")).to_eng_string()}
    data["total_matches"] = int(matches[0]["total_matches"]) if matches else 0

    return ToolExecutionResult(
        data=data,
        grounding=_build_journal_evidence(matches, target) if matches else None,
    )


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
    try:
        stmt = GetPartnerStatement(repo).execute(
            PartnerStatementQuery(company_id=company_id, partner_id=partner_id, currency="", date_from=sd, date_to=ed)
        )
    except ValueError:
        # The repository raises for a partner this company does not have,
        # which is an ordinary thing for a model to ask about -- it guesses
        # ids. An answer of "no such partner" is the answer; an exception
        # reaching the model as "Error executing get_customer_statement:
        # Partner 1 not found for company 24599" leaks an internal message
        # and reads like a fault.
        return {"error": f"Partner {partner_id} not found in this company."}
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
        description=(
            "Get Trial Balance with debit and credit totals and account balances. "
            "The report is cumulative as of a date; there is no start date."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "start_date": types.Schema(type="STRING", description="Ignored: a trial balance has no start date"),
                "end_date": types.Schema(type="STRING", description="Date to take the balance as of, YYYY-MM-DD (optional)"),
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
