'''Focused authorization and isolation tests for global and company user status.'''
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.routes import company_user_routes
from app.modules.accounting.services import audit_service


class RecordingSession:
    def __init__(self, tracked=(), scalar_result=2):
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0
        self.scalar_result = scalar_result
        self._tracked = list(tracked)
        self._active_values = {
            id(value): value.is_active
            for value in tracked
            if hasattr(value, 'is_active')
        }
        self._next_id = 1000

    def add(self, value):
        if value not in self.added:
            self.added.append(value)

    def flush(self):
        self.flushes += 1
        for value in self.added:
            if hasattr(value, 'id') and value.id is None:
                value.id = self._next_id
                self._next_id += 1

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        for value in self._tracked:
            if id(value) in self._active_values:
                value.is_active = self._active_values[id(value)]
        self.added.clear()

    def scalar(self, _statement):
        return self.scalar_result


def _user(user_id, *, active=True, superuser=False, email=None):
    return SimpleNamespace(
        id=user_id,
        email=email or f'user{user_id}@example.test',
        full_name=f'User {user_id}',
        is_active=active,
        is_superuser=superuser,
        token_version=0,
    )


def _membership(membership_id, company_id, user_id, *, active=True, role='viewer'):
    return SimpleNamespace(
        id=membership_id,
        company_id=company_id,
        user_id=user_id,
        is_active=active,
        role=role,
    )


@pytest.mark.parametrize(
    'endpoint',
    [
        company_user_routes.deactivate_user_account_endpoint,
        company_user_routes.reactivate_user_account_endpoint,
    ],
)
def test_company_admin_cannot_change_global_user_status(endpoint):
    with pytest.raises(HTTPException) as exc_info:
        endpoint(
            user_id=9,
            company_id=7,
            db=RecordingSession(),
            current_user=_user(1),
        )

    assert exc_info.value.status_code == 403


def test_superuser_global_deactivation_changes_only_user_and_audits_global_scope(
    monkeypatch,
):
    actor = _user(1, superuser=True)
    target = _user(9)
    company_a = _membership(20, 7, target.id)
    company_b = _membership(21, 8, target.id)
    db = RecordingSession([target, company_a, company_b])
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)

    result = company_user_routes.deactivate_user_account_endpoint(
        user_id=target.id,
        company_id=company_a.company_id,
        db=db,
        current_user=actor,
    )

    audit = next(value for value in db.added if isinstance(value, AuditLog))
    assert result.is_active is False
    assert company_a.is_active is True
    assert company_b.is_active is True
    assert audit.company_id is None
    assert audit.action == 'deactivate_user_account'
    assert audit.old_values['is_active'] is True
    assert audit.new_values['is_active'] is False
    assert audit.old_values['scope'] == 'global'
    assert audit.new_values['scope'] == 'global'
    assert db.commits == 1


def test_superuser_global_reactivation_changes_only_user_and_audits_global_scope(
    monkeypatch,
):
    actor = _user(1, superuser=True)
    target = _user(9, active=False)
    membership = _membership(20, 7, target.id, active=False)
    db = RecordingSession([target, membership])
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)

    result = company_user_routes.reactivate_user_account_endpoint(
        user_id=target.id,
        company_id=membership.company_id,
        db=db,
        current_user=actor,
    )

    audit = next(value for value in db.added if isinstance(value, AuditLog))
    assert result.is_active is True
    assert membership.is_active is False
    assert audit.company_id is None
    assert audit.action == 'reactivate_user_account'
    assert audit.old_values['is_active'] is False
    assert audit.new_values['is_active'] is True
    assert db.commits == 1


def test_company_access_removal_changes_only_selected_membership(monkeypatch):
    actor = _user(1)
    target = _user(9)
    company_a = _membership(20, 7, target.id)
    company_b = _membership(21, 8, target.id)
    db = RecordingSession([target, company_a, company_b])
    monkeypatch.setattr(company_user_routes, 'get_company_user', lambda **_kwargs: company_a)
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)
    monkeypatch.setattr(company_user_routes, 'ensure_company_access', lambda **_kwargs: None)

    company_user_routes.remove_company_access_endpoint(
        company_user_id=company_a.id,
        db=db,
        current_user=actor,
    )

    audit = next(value for value in db.added if isinstance(value, AuditLog))
    assert company_a.is_active is False
    assert company_b.is_active is True
    assert target.is_active is True
    assert audit.company_id == company_a.company_id
    assert audit.action == 'remove_company_access'
    assert audit.old_values == {'is_active': True}
    assert audit.new_values == {'is_active': False}


def test_company_access_restoration_changes_only_selected_membership(monkeypatch):
    actor = _user(1)
    target = _user(9)
    company_a = _membership(20, 7, target.id, active=False)
    company_b = _membership(21, 8, target.id, active=True)
    db = RecordingSession([target, company_a, company_b])
    monkeypatch.setattr(company_user_routes, 'get_company_user', lambda **_kwargs: company_a)
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)
    monkeypatch.setattr(company_user_routes, 'ensure_company_access', lambda **_kwargs: None)

    company_user_routes.restore_company_access_endpoint(
        company_user_id=company_a.id,
        db=db,
        current_user=actor,
    )

    audit = next(value for value in db.added if isinstance(value, AuditLog))
    assert company_a.is_active is True
    assert company_b.is_active is True
    assert target.is_active is True
    assert audit.action == 'restore_company_access'
    assert audit.old_values == {'is_active': False}
    assert audit.new_values == {'is_active': True}


def test_company_admin_cannot_manage_membership_in_another_company(monkeypatch):
    actor = _user(1)
    target_membership = _membership(20, 8, 9)
    db = RecordingSession([target_membership])
    monkeypatch.setattr(
        company_user_routes,
        'get_company_user',
        lambda **_kwargs: target_membership,
    )

    def deny(**_kwargs):
        raise HTTPException(status_code=403, detail='No access to target company')

    monkeypatch.setattr(company_user_routes, 'ensure_company_access', deny)

    with pytest.raises(HTTPException) as exc_info:
        company_user_routes.remove_company_access_endpoint(
            company_user_id=target_membership.id,
            db=db,
            current_user=actor,
        )

    assert exc_info.value.status_code == 403
    assert target_membership.is_active is True


def test_global_mutation_rolls_back_when_audit_insert_fails(monkeypatch):
    actor = _user(1, superuser=True)
    target = _user(9)
    membership = _membership(20, 7, target.id)
    db = RecordingSession([target, membership])
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)

    def fail(**_kwargs):
        raise RuntimeError('audit insert failed')

    monkeypatch.setattr(audit_service, 'create_audit_log', fail)

    with pytest.raises(RuntimeError, match='audit insert failed'):
        company_user_routes.deactivate_user_account_endpoint(
            user_id=target.id,
            company_id=membership.company_id,
            db=db,
            current_user=actor,
        )

    assert target.is_active is True
    assert membership.is_active is True
    assert db.commits == 0
    assert db.rollbacks == 1


def test_company_access_removal_rolls_back_when_audit_insert_fails(monkeypatch):
    actor = _user(1)
    target = _user(9)
    membership = _membership(20, 7, target.id)
    db = RecordingSession([target, membership])
    monkeypatch.setattr(company_user_routes, 'get_company_user', lambda **_kwargs: membership)
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: target)
    monkeypatch.setattr(company_user_routes, 'ensure_company_access', lambda **_kwargs: None)

    def fail(**_kwargs):
        raise RuntimeError('audit insert failed')

    monkeypatch.setattr(audit_service, 'create_audit_log', fail)

    with pytest.raises(RuntimeError, match='audit insert failed'):
        company_user_routes.remove_company_access_endpoint(
            company_user_id=membership.id,
            db=db,
            current_user=actor,
        )

    assert membership.is_active is True
    assert target.is_active is True
    assert db.commits == 0
    assert db.rollbacks == 1


def test_last_active_company_admin_still_cannot_be_removed(monkeypatch):
    actor = _user(1)
    membership = _membership(20, 7, 9, role='admin')
    db = RecordingSession([membership], scalar_result=1)
    monkeypatch.setattr(company_user_routes, 'get_company_user', lambda **_kwargs: membership)
    monkeypatch.setattr(company_user_routes, 'ensure_company_access', lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        company_user_routes.remove_company_access_endpoint(
            company_user_id=membership.id,
            db=db,
            current_user=actor,
        )

    assert exc_info.value.status_code == 400
    assert membership.is_active is True


def test_superuser_cannot_deactivate_self_or_final_active_superuser(monkeypatch):
    actor = _user(1, superuser=True)
    db = RecordingSession([actor], scalar_result=1)
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: actor)

    with pytest.raises(HTTPException) as self_error:
        company_user_routes.deactivate_user_account_endpoint(
            user_id=actor.id,
            company_id=7,
            db=db,
            current_user=actor,
        )
    assert self_error.value.status_code == 400

    final_superuser = _user(2, superuser=True)
    monkeypatch.setattr(company_user_routes, 'get_user', lambda **_kwargs: final_superuser)
    with pytest.raises(HTTPException) as final_error:
        company_user_routes.deactivate_user_account_endpoint(
            user_id=final_superuser.id,
            company_id=7,
            db=db,
            current_user=actor,
        )
    assert final_error.value.status_code == 400
