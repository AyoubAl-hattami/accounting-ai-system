"""Tests for Unified Gemini Agent live accounting tool calling, multi-language, and action proposals."""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services.unified_gemini_agent import dispatch_unified_agent


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


def test_dispatch_unified_agent_accounting_pl_english(mock_db):
    page_ctx = PageContext(page="reports", route="/reports/profit-and-loss")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="What is our profit and loss report?",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    assert reply.reply
    assert reply.confidence in ("high", "medium")


def test_dispatch_unified_agent_accounting_pl_arabic(mock_db):
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="accountant",
        message="كم صافي الأرباح والخسائر للشركة؟",
        page_context=page_ctx,
        language="ar",
    )
    assert reply is not None
    assert reply.reply
    assert reply.confidence in ("high", "medium")


def test_dispatch_unified_agent_action_proposal(mock_db):
    page_ctx = PageContext(page="journal-entries", route="/journal-entries")
    # Mock account lookup for proposal
    mock_cash = MagicMock()
    mock_cash.id = 1
    mock_cash.code = "1010"
    mock_cash.name = "Cash"

    mock_rent = MagicMock()
    mock_rent.id = 2
    mock_rent.code = "5010"
    mock_rent.name = "Rent Expense"

    mock_db.scalars.return_value.first.side_effect = [mock_rent, mock_cash, mock_rent, mock_cash]

    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="Prepare a draft journal entry to pay 500 rent from cash account.",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    assert reply.reply
