import uuid
from dataclasses import dataclass

import pytest
import requests
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.gemini_assistant_schemas import PageContext
from app.modules.accounting.services import assistant_conversation_service
from app.modules.accounting.services.assistant_conversation_service import (
    create_conversation,
    send_conversation_message,
)
from app.modules.accounting.services.auth_service import create_user_token


@dataclass
class ConversationActors:
    owner_id: int
    other_id: int
    second_company_id: int
    created_cash_account_id: int | None
    owner_headers: dict[str, str]
    other_headers: dict[str, str]


@pytest.fixture
def conversation_actors(default_company_id):
    marker = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        owner = User(
            email=f"conversation-owner-{marker}@example.test",
            full_name="Conversation Owner",
            hashed_password="not-used-by-this-test",
            is_active=True,
            is_superuser=False,
        )
        other = User(
            email=f"conversation-other-{marker}@example.test",
            full_name="Conversation Other",
            hashed_password="not-used-by-this-test",
            is_active=True,
            is_superuser=False,
        )
        second_company = Company(
            name=f"Conversation Company {marker}",
            base_currency="USD",
        )
        db.add_all([owner, other, second_company])
        db.flush()
        cash_account = db.scalar(
            select(Account).where(
                Account.company_id == default_company_id,
                Account.name == "Cash",
                Account.is_active.is_(True),
            )
        )
        created_cash_account_id = None
        if cash_account is None:
            cash_account = Account(
                company_id=default_company_id,
                code=f"TEST-CASH-{marker}",
                name="Cash",
                account_type="asset",
                is_active=True,
                is_system=False,
            )
            db.add(cash_account)
            db.flush()
            created_cash_account_id = cash_account.id
        db.add_all(
            [
                CompanyUser(
                    company_id=default_company_id,
                    user_id=owner.id,
                    role="admin",
                    is_active=True,
                ),
                CompanyUser(
                    company_id=second_company.id,
                    user_id=owner.id,
                    role="admin",
                    is_active=True,
                ),
                CompanyUser(
                    company_id=default_company_id,
                    user_id=other.id,
                    role="viewer",
                    is_active=True,
                ),
            ]
        )
        db.commit()
        db.refresh(owner)
        db.refresh(other)
        actors = ConversationActors(
            owner_id=owner.id,
            other_id=other.id,
            second_company_id=second_company.id,
            created_cash_account_id=created_cash_account_id,
            owner_headers={"Authorization": f"Bearer {create_user_token(owner)}"},
            other_headers={"Authorization": f"Bearer {create_user_token(other)}"},
        )

    try:
        yield actors
    finally:
        with SessionLocal() as db:
            conversations = list(
                db.scalars(
                    select(AssistantConversation).where(
                        AssistantConversation.user_id.in_([actors.owner_id, actors.other_id])
                    )
                )
            )
            for conversation in conversations:
                db.delete(conversation)
            db.flush()
            if actors.created_cash_account_id is not None:
                cash_account = db.get(Account, actors.created_cash_account_id)
                if cash_account:
                    db.delete(cash_account)
                db.flush()
            memberships = list(
                db.scalars(
                    select(CompanyUser).where(
                        CompanyUser.user_id.in_([actors.owner_id, actors.other_id])
                    )
                )
            )
            for membership in memberships:
                db.delete(membership)
            db.flush()
            for user_id in [actors.owner_id, actors.other_id]:
                user = db.get(User, user_id)
                if user:
                    db.delete(user)
            company = db.get(Company, actors.second_company_id)
            if company:
                db.delete(company)
            db.commit()


def _create_conversation(base_url, headers, company_id, language="en"):
    response = requests.post(
        f"{base_url}/ai/conversations",
        headers=headers,
        json={"company_id": company_id, "language": language},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _send_message(
    base_url,
    headers,
    company_id,
    conversation_id,
    message,
    language="en",
    client_message_id=None,
):
    payload = {
        "company_id": company_id,
        "message": message,
        "language": language,
        "client_message_id": client_message_id or f"test-{uuid.uuid4().hex}",
        "page_context": {
            "route": "/dashboard",
            "page": "dashboard",
            "filters": {},
        },
    }
    return requests.post(
        f"{base_url}/ai/conversations/{conversation_id}/messages",
        headers=headers,
        json=payload,
    ), payload


def test_create_save_reload_and_list_newest_first(
    base_url, default_company_id, conversation_actors,
):
    first = _create_conversation(
        base_url, conversation_actors.owner_headers, default_company_id
    )
    second = _create_conversation(
        base_url, conversation_actors.owner_headers, default_company_id
    )
    response, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        first["id"],
        "سلام عليكم",
    )
    assert response.status_code == 201, response.text
    exchange = response.json()
    assert exchange["user_message"]["content"] == "سلام عليكم"
    assert exchange["assistant_message"]["role"] == "assistant"
    assert exchange["assistant_message"]["created_at"]
    assert exchange["assistant_reply"]["intent"] == "greeting"
    assert exchange["assistant_message"]["content"].startswith("وعليكم السلام")

    reloaded = requests.get(
        f"{base_url}/ai/conversations/{first['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert reloaded.status_code == 200, reloaded.text
    detail = reloaded.json()
    assert detail["messages_total"] == 2
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["title"] == "سلام عليكم"

    accounting, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        first["id"],
        "كم صافي الربح؟",
        language="en",
    )
    assert accounting.status_code == 201, accounting.text
    assert accounting.json()["assistant_reply"]["intent"] == "answer_report_question"
    accounting_reply = accounting.json()["assistant_message"]["content"]
    assert "profit_loss_report" in accounting.json()["assistant_reply"]["data_sources"]
    assert "وعليكم السلام" not in accounting_reply
    assert any(character.isdigit() for character in accounting_reply)

    reloaded_after_accounting = requests.get(
        f"{base_url}/ai/conversations/{first['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert reloaded_after_accounting.status_code == 200
    assert reloaded_after_accounting.json()["messages_total"] == 4
    assert reloaded_after_accounting.json()["messages"][-2]["content"] == "كم صافي الربح؟"
    journal, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        first["id"],
        "دفعت كهرباء 500 ريال",
        language="en",
    )
    assert journal.status_code == 201, journal.text
    assert journal.json()["assistant_reply"]["intent"] in {
        "clarification",
        "create_journal_draft",
    }
    assert "وعليكم السلام" not in journal.json()["assistant_message"]["content"]
    assert journal.json()["assistant_reply"]["intent"] != "greeting"

    listed = requests.get(
        f"{base_url}/ai/conversations",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert listed.status_code == 200, listed.text
    ids = [item["id"] for item in listed.json()["items"]]
    assert ids.index(first["id"]) < ids.index(second["id"])
    assert listed.json()["items"][0]["last_message_preview"]


def test_conversations_are_private_to_owner_and_company(
    base_url, admin_headers, default_company_id, conversation_actors,
):
    conversation = _create_conversation(
        base_url, conversation_actors.owner_headers, default_company_id
    )
    foreign_user = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.other_headers,
        params={"company_id": default_company_id},
    )
    assert foreign_user.status_code == 404
    assert foreign_user.json() == {"detail": "Conversation not found"}

    superuser = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=admin_headers,
        params={"company_id": default_company_id},
    )
    assert superuser.status_code == 404

    other_company_list = requests.get(
        f"{base_url}/ai/conversations",
        headers=conversation_actors.owner_headers,
        params={"company_id": conversation_actors.second_company_id},
    )
    assert other_company_list.status_code == 200
    assert conversation["id"] not in {
        item["id"] for item in other_company_list.json()["items"]
    }
    wrong_company = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": conversation_actors.second_company_id},
    )
    assert wrong_company.status_code == 404


def test_inactive_user_old_token_is_denied(
    base_url, default_company_id, conversation_actors,
):
    with SessionLocal() as db:
        user = db.get(User, conversation_actors.owner_id)
        user.is_active = False
        db.commit()
    try:
        response = requests.get(
            f"{base_url}/ai/conversations",
            headers=conversation_actors.owner_headers,
            params={"company_id": default_company_id},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Inactive user"
    finally:
        with SessionLocal() as db:
            user = db.get(User, conversation_actors.owner_id)
            user.is_active = True
            db.commit()


def test_inactive_company_membership_is_denied(
    base_url, default_company_id, conversation_actors,
):
    with SessionLocal() as db:
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == default_company_id,
                CompanyUser.user_id == conversation_actors.owner_id,
            )
        )
        membership.is_active = False
        db.commit()
    try:
        response = requests.get(
            f"{base_url}/ai/conversations",
            headers=conversation_actors.owner_headers,
            params={"company_id": default_company_id},
        )
        assert response.status_code == 403
    finally:
        with SessionLocal() as db:
            membership = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id == default_company_id,
                    CompanyUser.user_id == conversation_actors.owner_id,
                )
            )
            membership.is_active = True
            db.commit()

def test_missing_archive_and_delete_contract(
    base_url, default_company_id, conversation_actors,
):
    missing = requests.get(
        f"{base_url}/ai/conversations/999999999",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert missing.status_code == 404

    conversation = _create_conversation(
        base_url, conversation_actors.owner_headers, default_company_id
    )
    archived = requests.patch(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        json={"company_id": default_company_id, "status": "archived"},
    )
    assert archived.status_code == 200, archived.text
    rejected, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        conversation["id"],
        "Hello after archive",
    )
    assert rejected.status_code == 409

    deleted = requests.delete(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert deleted.status_code == 204, deleted.text
    after_delete = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert after_delete.status_code == 404


def test_duplicate_client_message_id_is_idempotent(
    base_url, default_company_id, conversation_actors,
):
    conversation = _create_conversation(
        base_url, conversation_actors.owner_headers, default_company_id
    )
    client_message_id = f"duplicate-{uuid.uuid4().hex}"
    first, payload = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        conversation["id"],
        "Who are you?",
        client_message_id=client_message_id,
    )
    assert first.status_code == 201, first.text
    second = requests.post(
        f"{base_url}/ai/conversations/{conversation['id']}/messages",
        headers=conversation_actors.owner_headers,
        json=payload,
    )
    assert second.status_code == 201, second.text
    assert second.json()["idempotent_replay"] is True
    assert second.json()["user_message"]["id"] == first.json()["user_message"]["id"]
    assert second.json()["assistant_message"]["id"] == first.json()["assistant_message"]["id"]

    detail = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    ).json()
    assert detail["messages_total"] == 2


def test_provider_failure_preserves_user_and_safe_error(
    monkeypatch, default_company_id, conversation_actors,
):
    with SessionLocal() as db:
        conversation = create_conversation(
            db,
            company_id=default_company_id,
            user_id=conversation_actors.owner_id,
            title=None,
            language="en",
        )
        conversation_id = conversation.id
        monkeypatch.setattr(
            assistant_conversation_service,
            "dispatch_gemini_assistant",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider detail")),
        )
        user_message, assistant_message, reply, _ = send_conversation_message(
            db,
            conversation=conversation,
            user_role="admin",
            message="A message that must remain",
            language="en",
            page_context=PageContext(),
            client_message_id=f"failure-{uuid.uuid4().hex}",
        )
        assert user_message.id
        assert assistant_message.message_type == "error"
        assert reply.intent == "error"
        assert "provider detail" not in assistant_message.content

    with SessionLocal() as db:
        persisted = list(
            db.scalars(
                select(AssistantMessage)
                .where(AssistantMessage.conversation_id == conversation_id)
                .order_by(AssistantMessage.id)
            )
        )
        assert [message.role for message in persisted] == ["user", "assistant"]


def test_arabic_messages_and_pending_clarification_survive_reload(
    base_url, default_company_id, conversation_actors,
):
    conversation = _create_conversation(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        language="en",
    )
    greeting, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        conversation["id"],
        "السلام عليكم",
        language="en",
    )
    assert greeting.status_code == 201, greeting.text
    assert greeting.json()["assistant_reply"]["intent"] == "greeting"
    assert greeting.json()["user_message"]["language"] == "ar"
    assert greeting.json()["assistant_message"]["language"] == "ar"
    assert "وعليكم السلام" in greeting.json()["assistant_message"]["content"]

    pending, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        conversation["id"],
        "دفعت كهرباء 500 ريال",
        language="en",
    )
    assert pending.status_code == 201, pending.text
    pending_reply = pending.json()["assistant_reply"]
    assert pending_reply["intent"] == "clarification"
    assert pending_reply["pending_transaction"]

    reloaded = requests.get(
        f"{base_url}/ai/conversations/{conversation['id']}",
        headers=conversation_actors.owner_headers,
        params={"company_id": default_company_id},
    )
    assert reloaded.status_code == 200
    assert reloaded.json()["messages"][-1]["metadata"]["pending_transaction"]

    resolved, _ = _send_message(
        base_url,
        conversation_actors.owner_headers,
        default_company_id,
        conversation["id"],
        "من الصندوق",
        language="en",
    )
    assert resolved.status_code == 201, resolved.text
    assert resolved.json()["assistant_reply"]["suggested_action"], resolved.json()
    assert resolved.json()["assistant_reply"]["pending_transaction"] is None


def test_viewer_can_chat_but_cannot_confirm_journal(
    base_url, default_company_id, conversation_actors,
):
    conversation = _create_conversation(
        base_url, conversation_actors.other_headers, default_company_id
    )
    chat, _ = _send_message(
        base_url,
        conversation_actors.other_headers,
        default_company_id,
        conversation["id"],
        "Hello",
    )
    assert chat.status_code == 201, chat.text

    confirm = requests.post(
        f"{base_url}/ai/gemini-assistant/confirm-action",
        headers=conversation_actors.other_headers,
        json={
            "company_id": default_company_id,
            "action_type": "create_journal_entry_draft",
            "payload": {
                "company_id": default_company_id,
                "entry_date": "2026-01-01",
                "description": "viewer must not create",
                "lines": [
                    {"account_id": 5, "debit": 1, "credit": 0},
                    {"account_id": 11, "debit": 0, "credit": 1},
                ],
            },
        },
    )
    assert confirm.status_code == 403