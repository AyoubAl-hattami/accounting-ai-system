"""Tests for Project Knowledge Service, security filtering, and manifest indexing."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.modules.accounting.services.project_knowledge_service import (
    DENYLIST_PATTERNS,
    ProjectKnowledgeService,
    classify_document,
    is_file_allowed,
)


def test_denylist_strictly_rejects_sensitive_files():
    forbidden = [
        ".env",
        ".env.local",
        ".env.production",
        ".env.test",
        "backend/.env",
        "backend/.env.example",
        "secrets/jwt.pem",
        "config/database_credentials.json",
        "api_key.txt",
        "node_modules/react/index.js",
        "backend/.venv/bin/activate",
        "backend/.venv/Lib/site-packages/fastapi/__init__.py",
        "backend/__pycache__/main.cpython-313.pyc",
        "dist/bundle.js",
        "build/index.html",
        ".git/HEAD",
        ".git/config",
        "app.db",
        "test.sqlite3",
        "logo.png",
        "banner.jpg",
        "favicon.ico",
        "server.log",
        "backup.tar.gz",
    ]
    for path in forbidden:
        assert not is_file_allowed(path), f"Security violation: {path} was allowed!"


def test_allowlist_accepts_valid_project_files():
    allowed = [
        "backend/app/application/payments/use_cases.py",
        "backend/app/infrastructure/database/sqlalchemy/repositories/invoice_repository.py",
        "backend/app/domain/invoices/entities.py",
        "backend/app/modules/accounting/services/gemini_assistant_service.py",
        "backend/tests/test_payments.py",
        "backend/tests/test_currency_guard.py",
        "frontend/src/features/ai/GeminiAssistantPanel.tsx",
        "frontend/src/features/ai/useGeminiAssistant.ts",
        "alembic/versions/2026_01_01_init.py",
        "README.md",
        "agent_rag_audit_report.md",
        "phase_ai1_walkthrough.md",
        "docs/architecture.md",
    ]
    for path in allowed:
        assert is_file_allowed(path), f"Valid project file was rejected: {path}"


def test_classify_document_metadata():
    layer, domain, lang = classify_document("backend/app/application/payments/use_cases.py")
    assert layer == "application"
    assert domain == "payments"
    assert lang == "python"

    layer, domain, lang = classify_document("backend/app/infrastructure/database/sqlalchemy/repositories/invoice_repository.py")
    assert layer == "infrastructure"
    assert domain == "invoices"
    assert lang == "python"

    layer, domain, lang = classify_document("backend/tests/test_currency_guard.py")
    assert layer == "test"
    assert domain == "currency"
    assert lang == "python"

    layer, domain, lang = classify_document("frontend/src/features/ai/GeminiAssistantPanel.tsx")
    assert layer == "frontend"
    assert domain == "ai"
    assert lang == "typescript-react"

    layer, domain, lang = classify_document("agent_rag_audit_report.md")
    assert layer == "documentation"
    assert lang == "markdown"


def test_incremental_manifest_plan(tmp_path):
    manifest_file = tmp_path / "test_manifest.json"
    service = ProjectKnowledgeService(api_key="test-key")
    service.manifest_path = manifest_file

    initial_manifest = {
        "store_name": "fileSearchStores/test-store",
        "display_name": "accounting-ai-system-knowledge",
        "git_commit": "abc1234",
        "last_indexed_at": "2026-09-19T10:00:00Z",
        "documents": {
            "backend/app/application/payments/use_cases.py": {
                "sha256": "old_hash",
                "remote_document_name": "doc-1",
            },
            "deleted_file.py": {
                "sha256": "deleted_hash",
                "remote_document_name": "doc-2",
            },
        },
    }
    manifest_file.write_text(json.dumps(initial_manifest))

    mock_client = MagicMock()
    mock_store = MagicMock()
    mock_store.name = "fileSearchStores/test-store"
    mock_client.file_search_stores.get.return_value = mock_store

    mock_op = MagicMock()
    mock_op.response.document_name = "doc-new"
    mock_client.file_search_stores.upload_to_file_search_store.return_value = mock_op

    service._client = mock_client

    # Create dummy files for scan
    f1 = tmp_path / "use_cases.py"
    f1.write_text("updated content")

    f2 = tmp_path / "new_file.py"
    f2.write_text("new content")

    mock_files = {
        "backend/app/application/payments/use_cases.py": f1,
        "backend/app/application/new_file.py": f2,
    }

    with patch.object(service, "scan_repository", return_value=mock_files):
        stats = service.index_project()

    assert stats["added"] == 1  # new_file.py
    assert stats["modified"] == 1  # use_cases.py hash changed
    assert stats["removed"] == 1  # deleted_file.py
    assert stats["unchanged"] == 0

    # Verify remote delete was called for deleted_file and old use_cases
    assert mock_client.file_search_stores.documents.delete.call_count >= 2
