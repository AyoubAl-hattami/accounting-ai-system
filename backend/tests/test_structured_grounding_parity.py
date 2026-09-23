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


def _normalise(value):
    """Ids and dates vary per run; nothing else may."""
    if isinstance(value, dict):
        return {
            key: ("<id>" if key.endswith("_id") and isinstance(value[key], int) else _normalise(value[key]))
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
