"""Every read tool, called once, against a company with data in it.

Three of the twenty-one could never succeed, and each was found by hand,
one at a time:

  get_account_ledger   AttributeError: 'AccountLedgerRead' has no
                       attribute 'total_debit'                        [RAG-8]
  get_trial_balance    TypeError: got an unexpected keyword argument
                       'start_date'                                   [TB-CARD]
  get_general_ledger   AttributeError: 'GeneralLedgerRead' has no
                       attribute 'total_debit'                        here

RAG-8 found one because one is what I executed. The registry tests check that
the right roles are offered the right tools, and every one of those passed
while three tools returned an error string to the model on every call -- a
gate test cannot see that the thing behind the gate is broken.

This test calls each of them once. It does not check what they return: the
per-tool tests do that. It checks that they return.
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.modules.accounting.services.accounting_tool_registry import (
    AccountingToolRegistry,
)
from tests.factories.accounting import JournalLineSpec

# Arguments for the tools that need one to do anything. A tool missing from
# here is called with none, which is the case the model exercises most.
TOOL_ARGUMENTS = {
    "get_account_ledger": {"account_identifier": "1110"},
    "trace_amount": {"amount": 4000.0},
    "get_customer_statement": {"partner_id": 1},
    "get_vendor_statement": {"partner_id": 1},
    "propose_journal_entry": {
        "debit_account": "5100",
        "credit_account": "1110",
        "amount": 100.0,
        "description": "probe",
    },
}


def _read_tools():
    """Every registered tool. Proposals are included: they mutate nothing."""
    return sorted(AccountingToolRegistry._HANDLERS)


@pytest.fixture
def company_with_data(accounting_factory):
    bootstrap = accounting_factory.create_accounting_bootstrap(role="admin")
    entry_date = bootstrap.fiscal_period.start_date + timedelta(days=5)
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        entry_date=entry_date,
        description="sale",
        lines=[
            JournalLineSpec("1110", Decimal("4000.00"), Decimal("0"), "cash in"),
            JournalLineSpec("4100", Decimal("0"), Decimal("4000.00"), "sales"),
        ],
    )
    accounting_factory.create_journal(
        bootstrap=bootstrap,
        entry_date=entry_date,
        description="rent",
        lines=[
            JournalLineSpec("5100", Decimal("1500.00"), Decimal("0"), "rent"),
            JournalLineSpec("1110", Decimal("0"), Decimal("1500.00"), "paid"),
        ],
    )
    return bootstrap


def test_the_tool_list_is_not_empty():
    """Guard the guard: an empty registry would make this file pass silently."""
    assert len(_read_tools()) >= 20


@pytest.mark.parametrize("tool_name", _read_tools())
def test_the_tool_answers_rather_than_raising(tool_name, company_with_data, accounting_factory):
    result = AccountingToolRegistry.execute_tool(
        tool_name=tool_name,
        args=dict(TOOL_ARGUMENTS.get(tool_name, {})),
        db=accounting_factory.db,
        company_id=company_with_data.company.id,
        user_role="admin",
    )

    assert result.error is None, (
        f"{tool_name} could not be called at all: {result.error}. Every call "
        "returns this string to the model in place of an answer."
    )
    assert result.data is not None

    # A tool may legitimately say "not found" for a probe argument -- partner
    # 1 belongs to another company, and that IS the answer. What it may not do
    # is fail to run.
    if isinstance(result.data, dict) and "error" in result.data:
        message = str(result.data["error"]).lower()
        assert any(word in message for word in ("not found", "no ", "could not be")), (
            f"{tool_name} returned an error that is not a 'not found': "
            f"{result.data['error']}"
        )
