"""Conversation memory: what the assistant remembers, and who it must not remember it for."""

import uuid

import pytest
import requests
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.accounting.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.gemini_assistant_schemas import ConversationTurn
from app.modules.accounting.services.auth_service import create_user_token
from app.modules.accounting.services.gemini_transaction_parser import (
    MAX_FOLLOWUP_TURNS,
    _build_parser_prompt,
    build_followup_message,
)


def _turns(*pairs: tuple[str, str]) -> list[ConversationTurn]:
    return [ConversationTurn(role=role, content=content) for role, content in pairs]


# ── Follow-up merging (pure) ──────────────────────────────────────────────────


def test_followup_message_merges_only_user_turns():
    merged = build_followup_message(
        "it was 300 from the bank",
        _turns(
            ("user", "I paid the office rent"),
            ("assistant", "How much was it? I can draft an entry for 999."),
        ),
    )

    assert merged is not None
    assert "I paid the office rent" in merged
    assert "it was 300 from the bank" in merged
    # Assistant replies quote amounts from earlier drafts; merging them would
    # let "999" leak into amount extraction.
    assert "999" not in merged


def test_followup_message_without_usable_history_returns_none():
    assert build_followup_message("it was 300", None) is None
    assert build_followup_message("it was 300", []) is None
    assert build_followup_message("it was 300", _turns(("assistant", "Hello"))) is None


def test_followup_message_keeps_only_the_newest_user_turns():
    merged = build_followup_message(
        "from the bank",
        _turns(
            ("user", "oldest turn"),
            ("user", "middle turn"),
            ("user", "newest turn"),
        ),
    )

    assert merged is not None
    assert "oldest turn" not in merged
    assert merged.count(". ") == MAX_FOLLOWUP_TURNS
    assert merged.endswith("from the bank")


def test_followup_message_strips_control_characters_and_caps_length():
    merged = build_followup_message(
        "now\x00300",
        _turns(("user", "I paid rent\x07 " + "x" * 900)),
    )

    assert merged is not None
    assert "\x00" not in merged
    assert "\x07" not in merged
    # Each merged turn is truncated, so a long turn cannot crowd out the prompt.
    assert len(merged) < 700


def test_parser_prompt_carries_bounded_conversation_and_subtypes():
    prompt = _build_parser_prompt(
        message="it was 300 from the wallet",
        accounts_context=[
            {
                "code": "1120",
                "name": "Jawali Wallet",
                "account_type": "asset",
                "account_subtype": "e_wallet",
                "is_active": True,
            }
        ],
        language="en",
        conversation_history=_turns(("user", "I paid the office rent")),
    )

    rendered = str(prompt)
    assert "bounded_recent_conversation" in rendered
    assert "I paid the office rent" in rendered
    assert "e_wallet" in rendered


# ── Persisted memory over HTTP ────────────────────────────────────────────────


@pytest.fixture
def memory_actors(deterministic_accounting_bootstrap):
    """Owner plus a second user and a second company, for isolation checks."""
    bs = deterministic_accounting_bootstrap
    marker = uuid.uuid4().hex[:12]

    with SessionLocal() as db:
        stranger = User(
            email=f"memory-stranger-{marker}@accounting-ai-test.dev",
            full_name="Memory Stranger",
            hashed_password="not-used-by-this-test",
            is_active=True,
            is_superuser=False,
        )
        second_company = Company(
            name=f"Memory Company {marker}",
            base_currency="USD",
        )
        db.add_all([stranger, second_company])
        db.flush()
        db.add_all(
            [
                CompanyUser(
                    company_id=bs.company_id,
                    user_id=stranger.id,
                    role="accountant",
                    is_active=True,
                ),
                CompanyUser(
                    company_id=second_company.id,
                    user_id=bs.user.id,
                    role="admin",
                    is_active=True,
                ),
            ]
        )
        db.commit()
        db.refresh(stranger)
        actors = {
            "company_id": bs.company_id,
            "second_company_id": second_company.id,
            "owner_id": bs.user.id,
            "stranger_id": stranger.id,
            "owner_headers": bs.auth_headers,
            "stranger_headers": {
                "Authorization": f"Bearer {create_user_token(stranger)}"
            },
        }

    try:
        yield actors
    finally:
        with SessionLocal() as db:
            for conversation in db.scalars(
                select(AssistantConversation).where(
                    AssistantConversation.user_id.in_(
                        [actors["owner_id"], actors["stranger_id"]]
                    )
                )
            ):
                db.delete(conversation)
            db.flush()
            for membership in db.scalars(
                select(CompanyUser).where(
                    CompanyUser.user_id == actors["stranger_id"]
                )
            ):
                db.delete(membership)
            owner_second = db.scalar(
                select(CompanyUser).where(
                    CompanyUser.company_id == actors["second_company_id"],
                    CompanyUser.user_id == actors["owner_id"],
                )
            )
            if owner_second:
                db.delete(owner_second)
            db.flush()
            stranger = db.get(User, actors["stranger_id"])
            if stranger:
                db.delete(stranger)
            company = db.get(Company, actors["second_company_id"])
            if company:
                db.delete(company)
            db.commit()


def _new_conversation(base_url, headers, company_id):
    response = requests.post(
        f"{base_url}/ai/conversations",
        headers=headers,
        json={"company_id": company_id, "language": "en", "title": None},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _say(base_url, headers, company_id, conversation_id, message):
    response = requests.post(
        f"{base_url}/ai/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "company_id": company_id,
            "message": message,
            "language": "en",
            "client_message_id": f"memory-{uuid.uuid4().hex}",
            "page_context": {"route": "/dashboard", "page": "dashboard", "filters": {}},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_followup_turn_reuses_the_previous_subject(base_url, memory_actors):
    """"it was 300 from the bank" only means something next to the turn before it."""
    company_id = memory_actors["company_id"]
    headers = memory_actors["owner_headers"]
    conversation_id = _new_conversation(base_url, headers, company_id)

    _say(base_url, headers, company_id, conversation_id, "I paid the office rent")
    followup = _say(
        base_url, headers, company_id, conversation_id, "it was 300 from the bank"
    )

    action = followup["assistant_reply"].get("suggested_action")
    assert action is not None, followup["assistant_reply"]
    assert action["type"] == "create_journal_entry_draft"
    # The amount comes from this turn, the rent subject only from the one before.
    assert "300" in str(action)
    assert "rent" in str(action).lower()


def test_the_same_followup_alone_has_nothing_to_remember(base_url, memory_actors):
    """The follow-up must not draft an entry when no earlier turn supplies the subject."""
    company_id = memory_actors["company_id"]
    headers = memory_actors["owner_headers"]
    conversation_id = _new_conversation(base_url, headers, company_id)

    reply = _say(
        base_url, headers, company_id, conversation_id, "it was 300 from the bank"
    )["assistant_reply"]

    assert reply.get("suggested_action") is None


def test_memory_never_crosses_into_another_company(base_url, memory_actors):
    """Same user, two companies: the second conversation starts with no history."""
    headers = memory_actors["owner_headers"]
    first_company = memory_actors["company_id"]
    second_company = memory_actors["second_company_id"]

    first_conversation = _new_conversation(base_url, headers, first_company)
    _say(base_url, headers, first_company, first_conversation, "I paid the office rent")

    second_conversation = _new_conversation(base_url, headers, second_company)
    reply = _say(
        base_url,
        headers,
        second_company,
        second_conversation,
        "it was 300 from the bank",
    )["assistant_reply"]

    assert reply.get("suggested_action") is None

    detail = requests.get(
        f"{base_url}/ai/conversations/{second_conversation}",
        headers=headers,
        params={"company_id": second_company},
    )
    assert detail.status_code == 200, detail.text
    contents = [message["content"] for message in detail.json()["messages"]]
    assert "I paid the office rent" not in contents


def test_memory_never_crosses_into_another_user(base_url, memory_actors):
    """A colleague in the same company cannot read or reuse someone else's thread."""
    company_id = memory_actors["company_id"]
    owner_headers = memory_actors["owner_headers"]
    stranger_headers = memory_actors["stranger_headers"]

    owner_conversation = _new_conversation(base_url, owner_headers, company_id)
    _say(
        base_url,
        owner_headers,
        company_id,
        owner_conversation,
        "I paid the office rent",
    )

    forbidden = requests.get(
        f"{base_url}/ai/conversations/{owner_conversation}",
        headers=stranger_headers,
        params={"company_id": company_id},
    )
    assert forbidden.status_code == 404, forbidden.text

    listed = requests.get(
        f"{base_url}/ai/conversations",
        headers=stranger_headers,
        params={"company_id": company_id},
    )
    assert listed.status_code == 200, listed.text
    assert owner_conversation not in {
        item["id"] for item in listed.json()["items"]
    }


def test_memory_is_scoped_to_one_thread(base_url, memory_actors):
    """A new conversation in the same company does not inherit the old one's turns."""
    company_id = memory_actors["company_id"]
    headers = memory_actors["owner_headers"]

    first = _new_conversation(base_url, headers, company_id)
    _say(base_url, headers, company_id, first, "I paid the office rent")

    second = _new_conversation(base_url, headers, company_id)
    reply = _say(base_url, headers, company_id, second, "it was 300 from the bank")[
        "assistant_reply"
    ]

    assert reply.get("suggested_action") is None

    with SessionLocal() as db:
        stored = list(
            db.scalars(
                select(AssistantMessage).where(
                    AssistantMessage.conversation_id == second
                )
            )
        )
    assert all("office rent" not in message.content for message in stored)
