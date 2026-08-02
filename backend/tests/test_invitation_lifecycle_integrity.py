'''Focused invitation lifecycle, integrity, audit, and concurrency coverage.'''
import importlib.util
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.company_user_invitation import CompanyUserInvitation
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.company_user_invitation import (
    CompanyUserInvitationAccept,
    CompanyUserInvitationCreate,
)
from app.modules.accounting.services import audit_service
from app.modules.accounting.services.auth_service import get_user_by_email
from app.modules.accounting.services.company_user_invitation_service import (
    accept_invitation,
    cancel_invitation,
    create_invitation,
)


def _email(prefix='invite'):
    return f'{prefix}_{uuid.uuid4().hex}@example.com'


def _create_invite(base_url, headers, company_id, email, role='viewer'):
    return requests.post(
        f'{base_url}/company-users/invitations',
        headers=headers,
        json={'company_id': company_id, 'email': email, 'role': role},
    )


def _create_company(base_url, headers):
    response = requests.post(
        f'{base_url}/companies',
        headers=headers,
        json={'name': f'Invite Company {uuid.uuid4().hex}', 'base_currency': 'USD'},
    )
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_legacy_mixed_case_padded_user_email_lookup():
    canonical_email = _email('legacy_lookup')
    legacy_email = f'  {canonical_email.upper()}  '
    with SessionLocal() as db:
        user = User(
            email=legacy_email,
            full_name='Legacy Email Lookup',
            hashed_password='not-used-by-this-test',
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    try:
        with SessionLocal() as db:
            found = get_user_by_email(db, canonical_email)
            assert found is not None
            assert found.id == user_id
    finally:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            if user is not None:
                db.delete(user)
                db.commit()


def test_normalized_email_blocks_duplicate_live_invitation(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('normalized')
    first = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    second = _create_invite(base_url, bs.auth_headers, bs.company_id, f'  {email.upper()}  ')

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    with SessionLocal() as db:
        live_count = db.scalar(
            select(func.count()).select_from(CompanyUserInvitation).where(
                CompanyUserInvitation.company_id == bs.company_id,
                CompanyUserInvitation.normalized_email == email,
                CompanyUserInvitation.accepted_at.is_(None),
                CompanyUserInvitation.cancelled_at.is_(None),
            )
        )
        assert live_count == 1


def test_different_companies_may_invite_same_normalized_email(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('multi_company')
    other_company_id = _create_company(base_url, bs.auth_headers)

    first = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    second = _create_invite(base_url, bs.auth_headers, other_company_id, email.upper())

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text


def test_expired_invitation_reissue_preserves_and_supersedes_old_row(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('expired_reissue')
    first = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    assert first.status_code == 200, first.text
    old_id = int(first.json()['token'].split(':', 1)[0])
    with SessionLocal() as db:
        old_invite = db.get(CompanyUserInvitation, old_id)
        old_invite.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    replacement = _create_invite(base_url, bs.auth_headers, bs.company_id, email.upper())
    assert replacement.status_code == 200, replacement.text
    new_id = int(replacement.json()['token'].split(':', 1)[0])
    assert new_id != old_id

    with SessionLocal() as db:
        old_invite = db.get(CompanyUserInvitation, old_id)
        new_invite = db.get(CompanyUserInvitation, new_id)
        assert old_invite is not None
        assert old_invite.cancelled_at is not None
        assert old_invite.accepted_at is None
        assert new_invite is not None and new_invite.status == 'pending'


def test_expired_invitation_validation_and_acceptance_are_rejected(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, _email('expired_reject'))
    token = created.json()['token']
    invitation_id = int(token.split(':', 1)[0])
    with SessionLocal() as db:
        invite = db.get(CompanyUserInvitation, invitation_id)
        invite.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    validation = requests.get(
        f'{base_url}/company-users/invitations/validate', params={'token': token}
    )
    acceptance = requests.post(
        f'{base_url}/company-users/invitations/accept',
        json={'token': token, 'full_name': 'Expired', 'password': 'Password123'},
    )
    assert validation.status_code == 410
    assert acceptance.status_code == 410


def test_database_partial_unique_index_rejects_duplicate_live_rows(
    deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    admin = bs.user
    email = _email('database_unique')
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        first = CompanyUserInvitation(
            company_id=bs.company_id,
            email=email,
            normalized_email=email,
            role='viewer',
            token_hash=f'hash-{uuid.uuid4().hex}',
            expires_at=now + timedelta(days=1),
            invited_by_user_id=admin.id,
        )
        db.add(first)
        db.commit()

    with SessionLocal() as db:
        duplicate = CompanyUserInvitation(
            company_id=bs.company_id,
            email=email.upper(),
            normalized_email=email,
            role='viewer',
            token_hash=f'hash-{uuid.uuid4().hex}',
            expires_at=now + timedelta(days=1),
            invited_by_user_id=admin.id,
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_cancellation_preserves_row_and_rejects_validation_acceptance_and_repeat(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('cancelled')
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    token = created.json()['token']
    invitation_id = int(token.split(':', 1)[0])

    cancelled = requests.delete(
        f'{base_url}/company-users/invitations/{invitation_id}',
        headers=bs.auth_headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert requests.get(
        f'{base_url}/company-users/invitations/validate', params={'token': token}
    ).status_code == 410
    assert requests.post(
        f'{base_url}/company-users/invitations/accept',
        json={'token': token, 'full_name': 'Cancelled', 'password': 'Password123'},
    ).status_code == 410
    repeated = requests.delete(
        f'{base_url}/company-users/invitations/{invitation_id}',
        headers=bs.auth_headers,
    )
    assert repeated.status_code == 410

    with SessionLocal() as db:
        invite = db.get(CompanyUserInvitation, invitation_id)
        audit_count = db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == 'cancel_invitation',
                AuditLog.entity_id == invitation_id,
            )
        )
        assert invite is not None and invite.cancelled_at is not None
        assert audit_count == 1


def test_accept_once_without_duplicate_user_membership_or_audit_and_cannot_cancel(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('accept_once')
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    token = created.json()['token']
    invitation_id = int(token.split(':', 1)[0])
    payload = {'token': token, 'full_name': 'Accepted User', 'password': 'Password123'}

    first = requests.post(f'{base_url}/company-users/invitations/accept', json=payload)
    second = requests.post(f'{base_url}/company-users/invitations/accept', json=payload)
    cancel = requests.delete(
        f'{base_url}/company-users/invitations/{invitation_id}',
        headers=bs.auth_headers,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 409
    assert cancel.status_code == 409
    assert cancel.json()['detail'] == 'Invitation has already been accepted.'

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        user_count = db.scalar(select(func.count()).select_from(User).where(User.email == email))
        membership_count = db.scalar(
            select(func.count()).select_from(CompanyUser).where(
                CompanyUser.company_id == bs.company_id,
                CompanyUser.user_id == user.id,
            )
        )
        audit_count = db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == 'accept_invitation',
                AuditLog.entity_id == invitation_id,
            )
        )
        assert user_count == 1
        assert membership_count == 1
        assert audit_count == 1


def test_inactive_existing_membership_requires_restore(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('inactive_member')
    registration = requests.post(
        f'{base_url}/auth/register',
        json={'email': email, 'password': 'Password123', 'full_name': 'Inactive'},
    )
    user_id = registration.json()['id']
    added = requests.post(
        f'{base_url}/company-users',
        headers=bs.auth_headers,
        json={'company_id': bs.company_id, 'user_id': user_id, 'role': 'viewer'},
    )
    membership_id = added.json()['id']
    removed = requests.patch(
        f'{base_url}/company-users/{membership_id}/remove-access',
        headers=bs.auth_headers,
    )
    assert removed.status_code == 200

    invitation = _create_invite(base_url, bs.auth_headers, bs.company_id, email.upper())
    assert invitation.status_code == 409
    assert 'restore company access' in invitation.text.lower()


@pytest.mark.parametrize('password', ['alllowercase1', 'ALLUPPERCASE1', 'NoDigitsHere'])
def test_invitation_acceptance_uses_registration_password_policy(
    base_url, deterministic_accounting_bootstrap, password,
):
    bs = deterministic_accounting_bootstrap
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, _email('weak_password'))
    response = requests.post(
        f'{base_url}/company-users/invitations/accept',
        json={'token': created.json()['token'], 'full_name': 'Weak Password', 'password': password},
    )
    assert response.status_code == 422


def test_invitation_audits_never_contain_raw_token_or_token_hash(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, _email('audit_token'))
    raw_token = created.json()['token']
    invitation_id = int(raw_token.split(':', 1)[0])
    with SessionLocal() as db:
        invite = db.get(CompanyUserInvitation, invitation_id)
        logs = list(db.scalars(select(AuditLog).where(AuditLog.entity_id == invitation_id)).all())
        serialized = repr([(log.old_values, log.new_values) for log in logs])
        assert raw_token not in serialized
        assert invite.token_hash not in serialized


def test_audit_failure_rolls_back_creation_acceptance_and_cancellation(
    monkeypatch, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    admin = bs.user

    accept_email = _email('rollback_accept')
    cancel_email = _email('rollback_cancel')
    with SessionLocal() as db:
        accept_response = create_invitation(
            db,
            CompanyUserInvitationCreate(company_id=bs.company_id, email=accept_email, role='viewer'),
            db.merge(admin),
        )
        # Route-owned transaction: commit setup invitation so it is visible in later sessions.
        db.commit()
    with SessionLocal() as db:
        cancel_response = create_invitation(
            db,
            CompanyUserInvitationCreate(company_id=bs.company_id, email=cancel_email, role='viewer'),
            db.merge(admin),
        )
        # Route-owned transaction: commit setup invitation so it is visible in later sessions.
        db.commit()
    cancel_id = int(cancel_response.token.split(':', 1)[0])

    def fail(**_kwargs):
        raise RuntimeError('audit insert failed')

    monkeypatch.setattr(audit_service, 'create_audit_log', fail)

    create_email = _email('rollback_create')
    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match='audit insert failed'):
            create_invitation(
                db,
                CompanyUserInvitationCreate(company_id=bs.company_id, email=create_email, role='viewer'),
                db.merge(admin),
            )
    with SessionLocal() as db:
        assert db.scalar(
            select(CompanyUserInvitation).where(CompanyUserInvitation.normalized_email == create_email)
        ) is None

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match='audit insert failed'):
            accept_invitation(
                db,
                CompanyUserInvitationAccept(
                    token=accept_response.token, full_name='Rollback Accept', password='Password123',
                ),
            )
    with SessionLocal() as db:
        accept_invite = db.get(CompanyUserInvitation, int(accept_response.token.split(':', 1)[0]))
        assert accept_invite.accepted_at is None
        assert db.scalar(select(User).where(User.email == accept_email)) is None

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match='audit insert failed'):
            cancel_invitation(db, cancel_id, db.merge(admin))
    with SessionLocal() as db:
        cancel_invite = db.get(CompanyUserInvitation, cancel_id)
        assert cancel_invite is not None
        assert cancel_invite.cancelled_at is None


def test_migration_backfill_and_duplicate_cleanup_are_non_destructive(monkeypatch):
    migration_path = (
        Path(__file__).parents[1]
        / 'alembic'
        / 'versions'
        / 'a6f4c2d8e1b7_invitation_lifecycle_integrity.py'
    )
    spec = importlib.util.spec_from_file_location('invitation_migration', migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    class RecordingOp:
        def __init__(self):
            self.sql = []
            self.indexes = []

        def __getattr__(self, name):
            if name == 'execute':
                return lambda sql: self.sql.append(str(sql))
            if name == 'create_index':
                return lambda *args, **kwargs: self.indexes.append((args, kwargs))
            return lambda *args, **kwargs: None

    recording_op = RecordingOp()
    monkeypatch.setattr(migration, 'op', recording_op)
    migration.upgrade()
    migration_sql = '\n'.join(recording_op.sql).lower()

    assert 'lower(btrim(email))' in migration_sql
    assert 'row_number() over' in migration_sql
    assert 'update company_user_invitations' in migration_sql
    assert 'delete from company_user_invitations' not in migration_sql
    assert any(
        args[0] == 'uq_company_user_invitations_live'
        and kwargs['postgresql_where'] is not None
        for args, kwargs in recording_op.indexes
    )


@pytest.mark.skipif(
    not os.getenv('DATABASE_URL', '').startswith('postgresql'),
    reason='PostgreSQL concurrency coverage',
)
def test_postgresql_concurrent_duplicate_creation_has_one_winner(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('concurrent_create')

    def create():
        return _create_invite(base_url, bs.auth_headers, bs.company_id, email).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _value: create(), range(2)))

    assert sorted(statuses) == [200, 409]


@pytest.mark.skipif(
    not os.getenv('DATABASE_URL', '').startswith('postgresql'),
    reason='PostgreSQL concurrency coverage',
)
def test_postgresql_concurrent_double_accept_has_one_success(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    email = _email('concurrent_accept')
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, email)
    token = created.json()['token']
    invitation_id = int(token.split(':', 1)[0])
    payload = {'token': token, 'full_name': 'Concurrent Accept', 'password': 'Password123'}

    def accept():
        return requests.post(f'{base_url}/company-users/invitations/accept', json=payload).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _value: accept(), range(2)))

    assert sorted(statuses) == [200, 409]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        assert db.scalar(
            select(func.count()).select_from(CompanyUser).where(
                CompanyUser.company_id == bs.company_id,
                CompanyUser.user_id == user.id,
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == 'accept_invitation',
                AuditLog.entity_id == invitation_id,
            )
        ) == 1


@pytest.mark.skipif(
    not os.getenv('DATABASE_URL', '').startswith('postgresql'),
    reason='PostgreSQL concurrency coverage',
)
def test_postgresql_concurrent_accept_and_cancel_has_one_terminal_state(
    base_url, deterministic_accounting_bootstrap,
):
    bs = deterministic_accounting_bootstrap
    created = _create_invite(base_url, bs.auth_headers, bs.company_id, _email('accept_cancel'))
    token = created.json()['token']
    invitation_id = int(token.split(':', 1)[0])

    def accept():
        return requests.post(
            f'{base_url}/company-users/invitations/accept',
            json={'token': token, 'full_name': 'Accept Cancel Race', 'password': 'Password123'},
        )

    def cancel():
        return requests.delete(
            f'{base_url}/company-users/invitations/{invitation_id}',
            headers=bs.auth_headers,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(accept), executor.submit(cancel)]
        responses = [result.result() for result in results]

    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == 1
    assert 500 not in statuses
    assert sorted(statuses)[1] in {409, 410}
    losing_response = next(response for response in responses if response.status_code != 200)
    assert losing_response.json()['detail'] in {
        'Invitation has already been accepted.',
        'Invitation has been cancelled.',
    }
    with SessionLocal() as db:
        invite = db.get(CompanyUserInvitation, invitation_id)
        assert (invite.accepted_at is not None) != (invite.cancelled_at is not None)
        user = db.scalar(select(User).where(User.email == invite.normalized_email))
        membership_count = 0
        if user is not None:
            membership_count = db.scalar(
                select(func.count()).select_from(CompanyUser).where(
                    CompanyUser.company_id == bs.company_id,
                    CompanyUser.user_id == user.id,
                )
            )
        if invite.accepted_at is not None:
            assert user is not None
            assert membership_count == 1
        else:
            assert user is None
            assert membership_count == 0
        successful_audits = db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.entity_id == invitation_id,
                AuditLog.action.in_(['accept_invitation', 'cancel_invitation']),
            )
        )
        assert successful_audits == 1
