"""The structured cards do not change when their construction moves.

The four report cards -- balance sheet, trial balance, general ledger,
account ledger -- are built inline inside _structured_report_reply, in dense
one-line expressions interleaved with the reply text. They move into
report_grounding.py one at a time so the tool path can build the same card
from the same DTO.

A move that also changes an output is not a move, and the only way to know
the difference is to have the output first. Each GOLDEN below was captured
by running the code BEFORE its builder was extracted, against a company
seeded exactly as the fixture here seeds one: a 4000.00 sale and a 1500.00
rent payment, so every section of every report has something in it.

Account ids and dates are normalised -- they differ per run and per day --
and everything else is compared literally, including the figures, the
section order, the labels and the reference filters.
"""

import json
import re
from decimal import Decimal

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import gemini_assistant_service as service
from tests.factories.accounting import JournalLineSpec

PAGE = PageContext(page="dashboard", route="/dashboard")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


# Entry numbers are JE-<random hex> from the factory, so they differ per run
# like ids and dates do.
_VOLATILE_KEYS = {"entry_number", "entry_no"}


def _normalise(value):
    """Ids, dates and generated entry numbers vary per run; nothing else may."""
    if isinstance(value, dict):
        return {
            key: (
                "<id>" if key.endswith("_id") and isinstance(value[key], int)
                else "<entry>" if key in _VOLATILE_KEYS
                else _normalise(value[key])
            )
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, str):
        return _DATE.sub("<date>", value)
    return value


@pytest.fixture
def seeded_company(accounting_factory):
    """4000.00 of sales and 1500.00 of rent, the corpus the goldens came from."""
    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        description="sale",
        lines=[
            JournalLineSpec("1110", Decimal("4000.00"), Decimal("0"), "cash in"),
            JournalLineSpec("4100", Decimal("0"), Decimal("4000.00"), "sales"),
        ],
    )
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        description="rent",
        lines=[
            JournalLineSpec("5100", Decimal("1500.00"), Decimal("0"), "rent"),
            JournalLineSpec("1110", Decimal("0"), Decimal("1500.00"), "paid"),
        ],
    )
    return bootstrap


def _card(db, company_id, message, kind, account_target=None):
    reply = service._structured_report_reply(
        db=db, company_id=company_id, message=message, language="en",
        page_context=PAGE, kind=kind, account_target=account_target,
    )
    assert reply.grounding is not None, f"{kind} produced no card to compare"
    return _normalise(json.loads(reply.grounding.model_dump_json()))


BALANCE_SHEET_GOLDEN = {
        "kind": "balance_sheet",
        "metrics": {
            "current_year_earnings": "2500.00",
            "difference": "0.00",
            "is_balanced": True,
            "liabilities_and_equity": "2500.00",
            "prior_year_earnings": "0.00",
            "total_assets": "2500.00",
            "total_equity": "2500.00",
            "total_liabilities": "0.00"
        },
        "period": {
            "as_of_date": "<date>",
            "end_date": None,
            "label": "As of <date>",
            "start_date": None
        },
        "reference": {
            "filters": {
                "as_of_date": "<date>"
            },
            "report": "balance_sheet",
            "type": "report"
        },
        "requested_metric": "assets",
        "sections": [
            {
                "accounts": [
                    {
                        "account_code": "1000",
                        "account_id": "<id>",
                        "account_name": "Assets",
                        "balance": "0.00"
                    },
                    {
                        "account_code": "1110",
                        "account_id": "<id>",
                        "account_name": "Main Bank",
                        "balance": "2500.00"
                    },
                    {
                        "account_code": "1200",
                        "account_id": "<id>",
                        "account_name": "Accounts Receivable",
                        "balance": "0.00"
                    }
                ],
                "section": "assets",
                "total": "2500.00"
            },
            {
                "accounts": [
                    {
                        "account_code": "2000",
                        "account_id": "<id>",
                        "account_name": "Liabilities",
                        "balance": "0.00"
                    },
                    {
                        "account_code": "2100",
                        "account_id": "<id>",
                        "account_name": "Accounts Payable",
                        "balance": "0.00"
                    }
                ],
                "section": "liabilities",
                "total": "0.00"
            },
            {
                "accounts": [
                    {
                        "account_code": "3000",
                        "account_id": "<id>",
                        "account_name": "Equity",
                        "balance": "0.00"
                    },
                    {
                        "account_code": "3100",
                        "account_id": "<id>",
                        "account_name": "Owner Capital",
                        "balance": "0.00"
                    },
                    {
                        "account_code": "3200",
                        "account_id": "<id>",
                        "account_name": "Retained Earnings",
                        "balance": "0.00"
                    }
                ],
                "section": "equity",
                "total": "2500.00"
            }
        ],
        "status": "grounded"
    }


def test_the_balance_sheet_card_is_unchanged(seeded_company, accounting_factory):
    card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the balance sheet",
        "balance_sheet",
    )
    assert card == BALANCE_SHEET_GOLDEN


TRIAL_BALANCE_GOLDEN = {
        "accounts": [
            {
                "account_code": "1000",
                "account_id": "<id>",
                "account_name": "Assets",
                "account_type": "asset",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "1110",
                "account_id": "<id>",
                "account_name": "Main Bank",
                "account_type": "asset",
                "credit_balance": "0.00",
                "debit_balance": "2500.00",
                "net_balance": "2500.00"
            },
            {
                "account_code": "1200",
                "account_id": "<id>",
                "account_name": "Accounts Receivable",
                "account_type": "asset",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "2000",
                "account_id": "<id>",
                "account_name": "Liabilities",
                "account_type": "liability",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "2100",
                "account_id": "<id>",
                "account_name": "Accounts Payable",
                "account_type": "liability",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "3000",
                "account_id": "<id>",
                "account_name": "Equity",
                "account_type": "equity",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "3100",
                "account_id": "<id>",
                "account_name": "Owner Capital",
                "account_type": "equity",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "3200",
                "account_id": "<id>",
                "account_name": "Retained Earnings",
                "account_type": "equity",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "4000",
                "account_id": "<id>",
                "account_name": "Income",
                "account_type": "income",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "4100",
                "account_id": "<id>",
                "account_name": "Sales Revenue",
                "account_type": "income",
                "credit_balance": "4000.00",
                "debit_balance": "0.00",
                "net_balance": "-4000.00"
            },
            {
                "account_code": "5000",
                "account_id": "<id>",
                "account_name": "Expenses",
                "account_type": "expense",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            },
            {
                "account_code": "5100",
                "account_id": "<id>",
                "account_name": "Rent Expense",
                "account_type": "expense",
                "credit_balance": "0.00",
                "debit_balance": "1500.00",
                "net_balance": "1500.00"
            },
            {
                "account_code": "5200",
                "account_id": "<id>",
                "account_name": "Software Expense",
                "account_type": "expense",
                "credit_balance": "0.00",
                "debit_balance": "0.00",
                "net_balance": "0.00"
            }
        ],
        "kind": "trial_balance",
        "metrics": {
            "difference": "0.00",
            "is_balanced": True,
            "total_credit": "5500.00",
            "total_debit": "5500.00"
        },
        "period": {
            "as_of_date": None,
            "end_date": None,
            "label": "all available data",
            "start_date": None
        },
        "reference": {
            "filters": {
                "end_date": None
            },
            "report": "trial_balance",
            "type": "report"
        },
        "requested_metric": "total_debit",
        "status": "grounded",
        "summary": {
            "has_more": False,
            "returned_accounts": 13,
            "returned_entries": 0,
            "total_accounts": 13,
            "total_entries": 0
        }
    }


def test_the_trial_balance_card_is_unchanged(seeded_company, accounting_factory):
    card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the trial balance",
        "trial_balance",
    )
    assert card == TRIAL_BALANCE_GOLDEN


GENERAL_LEDGER_GOLDEN = {
        "accounts": [
            {
                "account_code": "1000",
                "account_id": "<id>",
                "account_name": "Assets",
                "account_type": "asset",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "1110",
                "account_id": "<id>",
                "account_name": "Main Bank",
                "account_type": "asset",
                "closing_balance": "2500.00",
                "entry_count": 2,
                "opening_balance": "0.00",
                "total_credit": "1500.00",
                "total_debit": "4000.00"
            },
            {
                "account_code": "1200",
                "account_id": "<id>",
                "account_name": "Accounts Receivable",
                "account_type": "asset",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "2000",
                "account_id": "<id>",
                "account_name": "Liabilities",
                "account_type": "liability",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "2100",
                "account_id": "<id>",
                "account_name": "Accounts Payable",
                "account_type": "liability",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "3000",
                "account_id": "<id>",
                "account_name": "Equity",
                "account_type": "equity",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "3100",
                "account_id": "<id>",
                "account_name": "Owner Capital",
                "account_type": "equity",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "3200",
                "account_id": "<id>",
                "account_name": "Retained Earnings",
                "account_type": "equity",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "4000",
                "account_id": "<id>",
                "account_name": "Income",
                "account_type": "income",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "4100",
                "account_id": "<id>",
                "account_name": "Sales Revenue",
                "account_type": "income",
                "closing_balance": "4000.00",
                "entry_count": 1,
                "opening_balance": "0.00",
                "total_credit": "4000.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "5000",
                "account_id": "<id>",
                "account_name": "Expenses",
                "account_type": "expense",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            },
            {
                "account_code": "5100",
                "account_id": "<id>",
                "account_name": "Rent Expense",
                "account_type": "expense",
                "closing_balance": "1500.00",
                "entry_count": 1,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "1500.00"
            },
            {
                "account_code": "5200",
                "account_id": "<id>",
                "account_name": "Software Expense",
                "account_type": "expense",
                "closing_balance": "0.00",
                "entry_count": 0,
                "opening_balance": "0.00",
                "total_credit": "0.00",
                "total_debit": "0.00"
            }
        ],
        "kind": "general_ledger",
        "period": {
            "as_of_date": None,
            "end_date": None,
            "label": "all available data",
            "start_date": None
        },
        "reference": {
            "filters": {
                "end_date": None,
                "start_date": None
            },
            "report": "general_ledger",
            "type": "report"
        },
        "requested_metric": "accounts",
        "status": "grounded",
        "summary": {
            "has_more": False,
            "returned_accounts": 13,
            "returned_entries": 0,
            "total_accounts": 13,
            "total_entries": 0
        }
    }


def test_the_general_ledger_card_is_unchanged(seeded_company, accounting_factory):
    card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the general ledger",
        "general_ledger",
    )
    assert card == GENERAL_LEDGER_GOLDEN


ACCOUNT_LEDGER_GOLDEN = {
        "account": {
            "account_code": "1110",
            "account_id": "<id>",
            "account_name": "Main Bank",
            "account_type": "asset"
        },
        "entries": [
            {
                "credit": "0.00",
                "debit": "4000.00",
                "description": "cash in",
                "entry_date": "<date>",
                "entry_number": "<entry>",
                "journal_entry_id": "<id>",
                "running_balance": "4000.00",
                "source": "accounting_report",
                "status": "posted"
            },
            {
                "credit": "1500.00",
                "debit": "0.00",
                "description": "paid",
                "entry_date": "<date>",
                "entry_number": "<entry>",
                "journal_entry_id": "<id>",
                "running_balance": "2500.00",
                "source": "accounting_report",
                "status": "posted"
            }
        ],
        "kind": "account_ledger",
        "metrics": {
            "closing_balance": "2500.00",
            "opening_balance": "0.00",
            "total_credit": "1500.00",
            "total_debit": "4000.00"
        },
        "period": {
            "as_of_date": None,
            "end_date": None,
            "label": "all available data",
            "start_date": None
        },
        "reference": {
            "filters": {
                "account_id": "<id>",
                "end_date": None,
                "start_date": None
            },
            "report": "account_ledger",
            "type": "report"
        },
        "requested_metric": "balance",
        "status": "grounded",
        "summary": {
            "has_more": False,
            "returned_accounts": 0,
            "returned_entries": 2,
            "total_accounts": 0,
            "total_entries": 2
        }
    }


def test_the_account_ledger_card_is_unchanged(seeded_company, accounting_factory):
    card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the ledger for account 1110",
        "account_ledger", "1110",
    )
    assert card == ACCOUNT_LEDGER_GOLDEN


# ── The tool builds the same card, and honours the date it was given ─────────

def test_the_tool_and_the_handler_build_the_same_card(seeded_company, accounting_factory):
    """Same DTO, same builder, same card -- which is the point of extracting
    it: the model path cannot drift from the deterministic one."""
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    handler_card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the balance sheet",
        "balance_sheet",
    )
    tool = AccountingToolRegistry.execute_tool(
        tool_name="get_balance_sheet",
        args={},
        db=accounting_factory.db,
        company_id=seeded_company.company.id,
        user_role="admin",
    )
    tool_card = _normalise(json.loads(tool.grounding.model_dump_json()))

    # requested_metric is the one field the handler sets from the question and
    # the tool defaults; everything the report produced must match.
    handler_card.pop("requested_metric")
    tool_card.pop("requested_metric")
    assert tool_card == handler_card


def test_the_balance_sheet_tool_honours_as_of_date(accounting_factory):
    """It accepted the argument and dropped it: every answer was today's."""
    from datetime import timedelta

    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    entry_date = bootstrap.fiscal_period.start_date + timedelta(days=10)
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        entry_date=entry_date,
        description="sale",
        lines=[
            JournalLineSpec("1110", Decimal("4000.00"), Decimal("0"), "cash in"),
            JournalLineSpec("4100", Decimal("0"), Decimal("4000.00"), "sales"),
        ],
    )

    def assets_as_of(as_of):
        result = AccountingToolRegistry.execute_tool(
            tool_name="get_balance_sheet",
            args={"as_of_date": as_of.isoformat()} if as_of else {},
            db=accounting_factory.db,
            company_id=bootstrap.company.id,
            user_role="admin",
        )
        return result.data["total_assets"], result.grounding.metrics["total_assets"], result.data["as_of_date"]

    before = assets_as_of(entry_date - timedelta(days=1))
    on_the_day = assets_as_of(entry_date)

    assert before[0] == 0.0 and before[1] == "0.00", (
        "The day before a 4000.00 sale, the company did not have it yet."
    )
    assert on_the_day[0] == 4000.0 and on_the_day[1] == "4000.00"
    assert before[2] == (entry_date - timedelta(days=1)).isoformat(), (
        "The payload must say which date it answered for."
    )


def test_the_trial_balance_tool_can_be_called_at_all(accounting_factory):
    """Every call raised TypeError: it passed start_date and end_date to a
    facade whose only parameter is as_of_date, so the model got an error
    string and no report, every time."""
    from datetime import timedelta

    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    entry_date = bootstrap.fiscal_period.start_date + timedelta(days=10)
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        entry_date=entry_date,
        description="sale",
        lines=[
            JournalLineSpec("1110", Decimal("4000.00"), Decimal("0"), "cash in"),
            JournalLineSpec("4100", Decimal("0"), Decimal("4000.00"), "sales"),
        ],
    )

    def trial_balance(**args):
        result = AccountingToolRegistry.execute_tool(
            tool_name="get_trial_balance",
            args=args,
            db=accounting_factory.db,
            company_id=bootstrap.company.id,
            user_role="admin",
        )
        assert result.error is None, result.error
        return result

    everything = trial_balance()
    assert everything.data["total_debit"] == 4000.0
    assert everything.data["is_balanced"] is True
    assert everything.grounding.metrics["total_debit"] == "4000.00"

    # end_date is what the balance is taken as of.
    before = trial_balance(end_date=(entry_date - timedelta(days=1)).isoformat())
    assert before.data["total_debit"] == 0.0
    assert before.data["as_of_date"] == (entry_date - timedelta(days=1)).isoformat()

    # start_date is accepted and ignored: a trial balance is cumulative, and
    # silently reinterpreting it would answer a question nobody asked.
    with_start = trial_balance(start_date="2026-01-01", end_date=entry_date.isoformat())
    assert with_start.data["total_debit"] == 4000.0
    assert with_start.data["as_of_date"] == entry_date.isoformat()


def test_the_trial_balance_tool_and_handler_build_the_same_card(seeded_company, accounting_factory):
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    handler_card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the trial balance",
        "trial_balance",
    )
    tool = AccountingToolRegistry.execute_tool(
        tool_name="get_trial_balance",
        args={},
        db=accounting_factory.db,
        company_id=seeded_company.company.id,
        user_role="admin",
    )
    tool_card = _normalise(json.loads(tool.grounding.model_dump_json()))

    # The handler knows the metric the question asked for and the period
    # wording it derived; the tool has neither and says so with None.
    for field in ("requested_metric", "period"):
        handler_card.pop(field)
        tool_card.pop(field)
    assert tool_card == handler_card


def test_the_general_ledger_tool_can_be_called_at_all(seeded_company, accounting_factory):
    """It read gl.total_debit and gl.total_credit. GeneralLedgerRead has
    neither: the report is a list of accounts, and a total means summing their
    lines -- which is what the card has always done."""
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    result = AccountingToolRegistry.execute_tool(
        tool_name="get_general_ledger",
        args={},
        db=accounting_factory.db,
        company_id=seeded_company.company.id,
        user_role="admin",
    )

    assert result.error is None, result.error
    bank = next(row for row in result.data["accounts"] if row["code"] == "1110")
    assert bank["total_debit"] == 4000.0
    assert bank["total_credit"] == 1500.0
    assert bank["closing_balance"] == 2500.0
    assert bank["entry_count"] == 2

    # Named for what they cover: [D3] paginates this report, so a sum over the
    # accounts shown is not the ledger's total.
    assert "total_debit" not in result.data and "total_credit" not in result.data
    assert result.data["debit_of_shown_accounts"] == 5500.0
    assert result.data["accounts_shown"] == len(result.data["accounts"])
    assert result.grounding.kind == "general_ledger"


def test_the_general_ledger_tool_and_handler_build_the_same_card(seeded_company, accounting_factory):
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    handler_card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the general ledger",
        "general_ledger",
    )
    tool = AccountingToolRegistry.execute_tool(
        tool_name="get_general_ledger",
        args={},
        db=accounting_factory.db,
        company_id=seeded_company.company.id,
        user_role="admin",
    )
    tool_card = _normalise(json.loads(tool.grounding.model_dump_json()))

    for field in ("requested_metric", "period"):
        handler_card.pop(field)
        tool_card.pop(field)
    assert tool_card == handler_card


def test_a_statement_for_a_partner_that_does_not_exist_is_an_answer(accounting_factory):
    """The repository raises for an unknown partner, and a model guessing ids
    is ordinary. "No such partner" is the answer; an exception reaching the
    model leaks an internal message and reads like a fault."""
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    result = AccountingToolRegistry.execute_tool(
        tool_name="get_customer_statement",
        args={"partner_id": 999999},
        db=accounting_factory.db,
        company_id=bootstrap.company.id,
        user_role="admin",
    )

    assert result.error is None
    assert result.data["error"] == "Partner 999999 not found in this company."
    assert str(bootstrap.company.id) not in result.data["error"], (
        "The company id is not the user's business and not the model's."
    )


def test_the_account_ledger_tool_and_handler_build_the_same_card(seeded_company, accounting_factory):
    """The last of the four, and the one whose tool was already repaired in
    RAG-8; it now carries the card that repair made possible."""
    from app.modules.accounting.services.accounting_tool_registry import (
        AccountingToolRegistry,
    )

    handler_card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the ledger for account 1110",
        "account_ledger",
        "1110",
    )
    tool = AccountingToolRegistry.execute_tool(
        tool_name="get_account_ledger",
        args={"account_identifier": "1110"},
        db=accounting_factory.db,
        company_id=seeded_company.company.id,
        user_role="admin",
    )
    tool_card = _normalise(json.loads(tool.grounding.model_dump_json()))

    for field in ("requested_metric", "period"):
        handler_card.pop(field)
        tool_card.pop(field)
    assert tool_card == handler_card


def test_the_account_ledger_card_says_posted_without_checking(seeded_company, accounting_factory):
    """Recorded, not fixed.

    Every entry in this card carries status "posted". AccountLedgerLine has
    no status field, and the query behind it filters to the reportable
    statuses -- so the word is the inline code's shorthand for "this came
    from the report", carried across verbatim when the builder moved.

    It is asserted here so the claim is visible: a card that states a status
    it never read is a small lie, and it should be either checked or dropped
    in a commit that says which.
    """
    card = _card(
        accounting_factory.db,
        seeded_company.company.id,
        "show me the ledger for account 1110",
        "account_ledger",
        "1110",
    )
    assert {entry["status"] for entry in card["entries"]} == {"posted"}
