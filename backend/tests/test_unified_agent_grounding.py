"""Tests for Unified Gemini Agent Project Grounding, Hallucination Prevention, and Citations."""

import time
from unittest.mock import MagicMock

import pytest

from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services.unified_gemini_agent import dispatch_unified_agent


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture(autouse=True)
def rate_limit_delay():
    yield
    time.sleep(6)


def test_grounding_test_a_existing_class(mock_db):
    """Test A: Ask about an existing class in the project (InvoiceRepository)."""
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="What is the InvoiceRepository class in this project and which file implements it?",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    assert "InvoiceRepository" in reply.reply
    # Verify citations or file path mentioned
    has_invoice_ref = any("invoice_repository" in c.file_path.lower() for c in reply.citations) or "invoice_repository" in reply.reply.lower()
    assert has_invoice_ref, f"Expected invoice_repository reference in reply or citations: {reply.reply}"


def test_grounding_test_b_non_existent_class(mock_db):
    """Test B: Ask about a non-existent class (QuantumLedgerOptimizer). Must not hallucinate."""
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="What is the QuantumLedgerOptimizer class in this project and what methods does it have?",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    reply_lower = reply.reply.lower()
    assert any(
        phrase in reply_lower
        for phrase in (
            "not verified",
            "not found",
            "does not exist",
            "no such",
            "cannot find",
            "غير متحقق",
            "غير موجود",
        )
    ), f"Expected refusal or not verified, got: {reply.reply}"


def test_grounding_test_c_non_existent_field(mock_db):
    """Test C: Ask about a non-existent field in Invoice model. Must not hallucinate."""
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="Does the Invoice model in this project have a quantum_settlement_hash field?",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    reply_lower = reply.reply.lower()
    assert any(
        phrase in reply_lower
        for phrase in (
            "no",
            "not verified",
            "does not have",
            "does not exist",
            "not found",
            "لا",
            "غير موجود",
        )
    ), f"Expected negative or not verified answer, got: {reply.reply}"


def test_grounding_test_d_cur_rules(mock_db):
    """Test D: Ask about CUR-1 to CUR-3 rules. Must extract from project knowledge."""
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="What are the CUR-1, CUR-2, and CUR-3 rules in this project?",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    reply_text = reply.reply
    assert "CUR-1" in reply_text or "cur-1" in reply_text.lower()
    assert "currenc" in reply_text.lower() or "عملة" in reply_text or "العملات" in reply_text


def test_grounding_test_e_cross_file_flow(mock_db):
    """Test E: Ask about cross-file architectural flow: Invoice -> Payment -> Allocation -> Aging -> Statement."""
    page_ctx = PageContext(page="dashboard", route="/dashboard")
    reply = dispatch_unified_agent(
        db=mock_db,
        company_id=1,
        user_role="admin",
        message="Explain the flow from Invoice -> Payment -> Allocation -> Aging -> Statement and list the files implementing it in this project.",
        page_context=page_ctx,
        language="en",
    )
    assert reply is not None
    reply_lower = reply.reply.lower()
    assert "invoice" in reply_lower
    assert "payment" in reply_lower
    assert "allocation" in reply_lower
    assert "aging" in reply_lower
    assert "statement" in reply_lower
