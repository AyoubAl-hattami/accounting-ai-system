import uuid
import time

import requests
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User

PASSWORD = "Password123"


def _register_and_login(base_url, prefix, full_name="Test User"):
    email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
    assert reg.status_code == 201, reg.text
    user_id = reg.json()["id"]
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return user_id, email, headers


def _create_company(base_url, headers, prefix="Company"):
    response = requests.post(
        f"{base_url}/companies",
        headers=headers,
        json={"name": f"{prefix}_{uuid.uuid4().hex[:10]}", "base_currency": "USD"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _add_company_user(base_url, auth_headers, company_id, user_id, role="viewer"):
    response = requests.post(
        f"{base_url}/company-users",
        headers=auth_headers,
        json={"company_id": company_id, "user_id": user_id, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_company_users_require_authentication(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(f"{base_url}/company-users?company_id={bs.company_id}")
    assert response.status_code in (401, 403)


def test_company_users_work_with_token(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/company-users?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= len(data["items"])
    assert len(data["items"]) > 0

    first_link = data["items"][0]
    assert "id" in first_link
    assert "company_id" in first_link
    assert "user_id" in first_link
    assert "role" in first_link
    assert "is_active" in first_link
    assert first_link["company_id"] == bs.company_id


def test_company_users_pagination_metadata(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/company-users?company_id={bs.company_id}&skip=0&limit=5",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5


def test_cannot_remove_last_admin(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    response = requests.get(
        f"{base_url}/company-users?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    admin_user = next((u for u in data["items"] if u["role"] == "admin"), None)
    assert admin_user is not None
    company_user_id = admin_user["id"]

    patch_response = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=bs.auth_headers,
        json={"role": "accountant"},
    )
    assert patch_response.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response.text

    patch_response_2 = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=bs.auth_headers,
        json={"is_active": False},
    )
    assert patch_response_2.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response_2.text


def test_remove_company_access_flow(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    unique_email = f"remove_access_{uuid.uuid4().hex[:12]}@example.com"

    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": PASSWORD, "full_name": "Rem User"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    add_member = requests.post(
        f"{base_url}/company-users",
        json={"company_id": bs.company_id, "user_id": user_id, "role": "viewer"},
        headers=bs.auth_headers,
    )
    assert add_member.status_code == 201
    company_user_id = add_member.json()["id"]

    acc_check = requests.get(
        f"{base_url}/accounts?company_id={bs.company_id}",
        headers=user_headers,
    )
    assert acc_check.status_code == 200

    bad_remove = requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=user_headers,
    )
    assert bad_remove.status_code in (401, 403)

    ok_remove = requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=bs.auth_headers,
    )
    assert ok_remove.status_code == 200
    assert ok_remove.json()["is_active"] is False

    acc_check_blocked = requests.get(
        f"{base_url}/accounts?company_id={bs.company_id}",
        headers=user_headers,
    )
    assert acc_check_blocked.status_code in (401, 403)

    audit = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "remove_company_access"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == company_user_id


def test_global_deactivation_requires_platform_superuser(
    base_url, deterministic_accounting_bootstrap, deterministic_superuser_headers
):
    bs = deterministic_accounting_bootstrap
    superuser_headers = deterministic_superuser_headers

    unique_email = f"deactivate_{uuid.uuid4().hex[:12]}@example.com"
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": PASSWORD, "full_name": "Deac User"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": bs.company_id, "email": unique_email, "role": "viewer"},
        headers=bs.auth_headers,
    )

    bad_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
    )
    assert bad_deactivate.status_code in (401, 403)

    with SessionLocal() as db:
        audit_count_before = db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "deactivate_user_account",
                AuditLog.entity_id == user_id,
            )
        ) or 0

    denied_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert denied_deactivate.status_code == 403

    with SessionLocal() as db:
        db_user = db.get(User, user_id)
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == bs.company_id,
                CompanyUser.user_id == user_id,
            )
        )
        audit_count_after_denial = db.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "deactivate_user_account",
                AuditLog.entity_id == user_id,
            )
        ) or 0
        assert db_user is not None and db_user.is_active is True
        assert membership is not None and membership.is_active is True
        assert audit_count_after_denial == audit_count_before

    login_after_denial = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert login_after_denial.status_code == 200

    ok_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=superuser_headers,
    )
    assert ok_deactivate.status_code == 200
    assert ok_deactivate.json()["is_active"] is False

    with SessionLocal() as db:
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == bs.company_id,
                CompanyUser.user_id == user_id,
            )
        )
        assert membership is not None and membership.is_active is True

    bad_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert bad_login.status_code == 401

    with SessionLocal() as db:
        audit_event = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "deactivate_user_account",
                AuditLog.entity_id == user_id,
            ).order_by(AuditLog.id.desc())
        )
        assert audit_event is not None
        assert audit_event.company_id is None
        assert audit_event.old_values["is_active"] is True
        assert audit_event.new_values["is_active"] is False
        assert audit_event.old_values["scope"] == "global"
        assert audit_event.new_values["scope"] == "global"
        actor = db.get(User, audit_event.actor_user_id)
        assert actor is not None and actor.is_superuser is True


def test_cannot_deactivate_last_admin(base_url):
    unique_email = f"last_admin_{uuid.uuid4().hex[:12]}@example.com"

    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": PASSWORD, "full_name": "Sole Admin"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    create_co = requests.post(
        f"{base_url}/companies",
        headers=user_headers,
        json={"name": f"SoleCo_{uuid.uuid4().hex[:8]}", "base_currency": "USD"},
    )
    assert create_co.status_code == 201
    co_id = create_co.json()["id"]

    res = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={co_id}",
        headers=user_headers,
    )
    assert res.status_code == 403
    assert "platform superuser" in res.text.lower()


def test_cancel_invitation_flow(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap
    unique_email = f"cancel_invite_{uuid.uuid4().hex[:12]}@example.com"

    reg_user = requests.post(
        f"{base_url}/auth/register",
        json={"email": f"non_admin_{uuid.uuid4().hex[:12]}@example.com", "password": PASSWORD, "full_name": "Non Admin"},
    )
    assert reg_user.status_code == 201
    login_user = requests.post(
        f"{base_url}/auth/login",
        json={"email": reg_user.json()["email"], "password": PASSWORD},
    )
    user_headers = {"Authorization": f"Bearer {login_user.json()['access_token']}"}

    invite_res = requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": bs.company_id, "email": unique_email, "role": "viewer"},
        headers=bs.auth_headers,
    )
    assert invite_res.status_code == 200
    invite_data = invite_res.json()
    assert invite_data["status"] == "invited"

    pending_res = requests.get(
        f"{base_url}/company-users/invitations?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert pending_res.status_code == 200
    invites = pending_res.json()
    my_invite = next((inv for inv in invites if inv["email"] == unique_email), None)
    assert my_invite is not None
    invitation_id = my_invite["id"]
    invite_token = invite_data["invite_url"].split("token=")[1]

    bad_cancel = requests.delete(
        f"{base_url}/company-users/invitations/{invitation_id}",
        headers=user_headers,
    )
    assert bad_cancel.status_code in (401, 403)

    ok_cancel = requests.delete(
        f"{base_url}/company-users/invitations/{invitation_id}",
        headers=bs.auth_headers,
    )
    assert ok_cancel.status_code == 200

    validate_res = requests.get(f"{base_url}/auth/validate-invite?token={invite_token}")
    assert validate_res.status_code in (400, 404)

    accept_res = requests.post(
        f"{base_url}/auth/accept-invite?token={invite_token}",
        json={"password": "NewPassword123", "full_name": "Should Fail"},
    )
    assert accept_res.status_code in (400, 404)

    audit = requests.get(
        f"{base_url}/audit-logs?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "cancel_invitation"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == invitation_id
    assert invite_token not in str(audit_events[0])


def test_restore_company_access_flow(
    base_url, deterministic_accounting_bootstrap, deterministic_superuser_headers
):
    bs = deterministic_accounting_bootstrap
    superuser_headers = deterministic_superuser_headers
    unique_email = f"restore_access_{uuid.uuid4().hex[:12]}@example.com"

    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": PASSWORD, "full_name": "Restore User"},
    )
    user_id = reg.json()["id"]
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    add_member = requests.post(
        f"{base_url}/company-users",
        json={"company_id": bs.company_id, "user_id": user_id, "role": "viewer"},
        headers=bs.auth_headers,
    )
    assert add_member.status_code == 201
    company_user_id = add_member.json()["id"]

    requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=bs.auth_headers,
    )

    acc_check = requests.get(
        f"{base_url}/accounts?company_id={bs.company_id}",
        headers=user_headers,
    )
    assert acc_check.status_code in (401, 403)

    bad_restore = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=user_headers,
    )
    assert bad_restore.status_code in (401, 403)

    ok_restore = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=bs.auth_headers,
    )
    assert ok_restore.status_code == 200
    assert ok_restore.json()["is_active"] is True

    acc_check_ok = requests.get(
        f"{base_url}/accounts?company_id={bs.company_id}",
        headers=user_headers,
    )
    assert acc_check_ok.status_code == 200

    denied_global = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert denied_global.status_code == 403

    with SessionLocal() as db:
        db_user = db.get(User, user_id)
        membership = db.get(CompanyUser, company_user_id)
        assert db_user is not None and db_user.is_active is True
        assert membership is not None and membership.is_active is True

    global_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=superuser_headers,
    )
    assert global_deactivate.status_code == 200

    with SessionLocal() as db:
        db_user = db.get(User, user_id)
        membership = db.get(CompanyUser, company_user_id)
        assert db_user is not None and db_user.is_active is False
        assert membership is not None and membership.is_active is True

    res_deactivated = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=bs.auth_headers,
    )
    assert res_deactivated.status_code == 400
    assert "account is deactivated" in res_deactivated.text.lower() or "reactivate account first" in res_deactivated.text.lower()


def test_reactivate_user_account_flow(
    base_url, deterministic_accounting_bootstrap, deterministic_superuser_headers
):
    bs = deterministic_accounting_bootstrap
    superuser_headers = deterministic_superuser_headers
    unique_email = f"reactivate_{uuid.uuid4().hex[:12]}@example.com"

    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": PASSWORD, "full_name": "Reac User"},
    )
    user_id = reg.json()["id"]

    requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": bs.company_id, "email": unique_email, "role": "viewer"},
        headers=bs.auth_headers,
    )

    denied_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert denied_deactivate.status_code == 403

    deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={bs.company_id}",
        headers=superuser_headers,
    )
    assert deactivate.status_code == 200

    bad_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert bad_login.status_code == 401

    other_email = f"other_{uuid.uuid4().hex[:12]}@example.com"
    requests.post(
        f"{base_url}/auth/register",
        json={"email": other_email, "password": PASSWORD, "full_name": "Other User"},
    )
    login_other = requests.post(
        f"{base_url}/auth/login",
        json={"email": other_email, "password": PASSWORD},
    )
    other_headers = {"Authorization": f"Bearer {login_other.json()['access_token']}"}

    bad_reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/reactivate?company_id={bs.company_id}",
        headers=other_headers,
    )
    assert bad_reactivate.status_code in (401, 403)

    admin_reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/reactivate?company_id={bs.company_id}",
        headers=bs.auth_headers,
    )
    assert admin_reactivate.status_code == 403

    ok_reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/reactivate?company_id={bs.company_id}",
        headers=superuser_headers,
    )
    assert ok_reactivate.status_code == 200
    assert ok_reactivate.json()["is_active"] is True

    with SessionLocal() as db:
        membership = db.scalar(
            select(CompanyUser).where(
                CompanyUser.company_id == bs.company_id,
                CompanyUser.user_id == user_id,
            )
        )
        assert membership is not None and membership.is_active is True

    ok_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": PASSWORD},
    )
    assert ok_login.status_code == 200

    with SessionLocal() as db:
        audit_event = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "reactivate_user_account",
                AuditLog.entity_id == user_id,
            ).order_by(AuditLog.id.desc())
        )
        assert audit_event is not None
        assert audit_event.company_id is None
        assert audit_event.old_values["is_active"] is False
        assert audit_event.new_values["is_active"] is True
        assert audit_event.old_values["scope"] == "global"
        assert audit_event.new_values["scope"] == "global"


def test_current_user_company_role_resolutions(base_url, deterministic_accounting_bootstrap):
    bs = deterministic_accounting_bootstrap

    acc_email = f"accountant_{uuid.uuid4().hex[:12]}@example.com"
    reg1 = requests.post(
        f"{base_url}/auth/register",
        json={"email": acc_email, "password": PASSWORD, "full_name": "Acc User"},
    )
    assert reg1.status_code == 201
    acc_user_id = reg1.json()["id"]

    add1 = requests.post(
        f"{base_url}/company-users",
        json={"company_id": bs.company_id, "user_id": acc_user_id, "role": "accountant"},
        headers=bs.auth_headers,
    )
    assert add1.status_code == 201, f"Failed to add accountant: {add1.text}"

    login1 = requests.post(f"{base_url}/auth/login", json={"email": acc_email, "password": PASSWORD})
    acc_headers = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    me_res1 = requests.get(
        f"{base_url}/company-users/me?company_id={bs.company_id}",
        headers=acc_headers,
    )
    assert me_res1.status_code == 200
    assert me_res1.json()["role"] == "accountant"
    assert me_res1.json()["is_active"] is True

    view_email = f"viewer_{uuid.uuid4().hex[:12]}@example.com"
    reg2 = requests.post(
        f"{base_url}/auth/register",
        json={"email": view_email, "password": PASSWORD, "full_name": "View User"},
    )
    assert reg2.status_code == 201
    view_user_id = reg2.json()["id"]

    add2 = requests.post(
        f"{base_url}/company-users",
        json={"company_id": bs.company_id, "user_id": view_user_id, "role": "viewer"},
        headers=bs.auth_headers,
    )
    assert add2.status_code == 201, f"Failed to add viewer: {add2.text}"
    view_company_user_id = add2.json()["id"]

    login2 = requests.post(f"{base_url}/auth/login", json={"email": view_email, "password": PASSWORD})
    view_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    me_res2 = requests.get(
        f"{base_url}/company-users/me?company_id={bs.company_id}",
        headers=view_headers,
    )
    assert me_res2.status_code == 200
    assert me_res2.json()["role"] == "viewer"
    assert me_res2.json()["is_active"] is True

    requests.patch(
        f"{base_url}/company-users/{view_company_user_id}/remove-access",
        headers=bs.auth_headers,
    )

    me_res3 = requests.get(
        f"{base_url}/company-users/me?company_id={bs.company_id}",
        headers=view_headers,
    )
    assert me_res3.status_code == 403

    non_member_email = f"non_member_{uuid.uuid4().hex[:12]}@example.com"
    requests.post(
        f"{base_url}/auth/register",
        json={"email": non_member_email, "password": PASSWORD, "full_name": "Non Member"},
    )
    login3 = requests.post(f"{base_url}/auth/login", json={"email": non_member_email, "password": PASSWORD})
    non_member_headers = {"Authorization": f"Bearer {login3.json()['access_token']}"}

    me_res4 = requests.get(
        f"{base_url}/company-users/me?company_id={bs.company_id}",
        headers=non_member_headers,
    )
    assert me_res4.status_code == 403


def test_company_admin_cannot_deactivate_or_reactivate_user_from_another_company(base_url):
    admin_a_id, _, admin_a_headers = _register_and_login(base_url, "admin_a", "Admin A")
    user_b_id, _, user_b_headers = _register_and_login(base_url, "user_b", "User B")

    company_a_id = _create_company(base_url, admin_a_headers, "CompanyA")
    _create_company(base_url, user_b_headers, "CompanyB")

    deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_b_id}/deactivate?company_id={company_a_id}",
        headers=admin_a_headers,
    )
    assert deactivate.status_code == 403
    assert "platform superuser" in deactivate.text.lower()

    reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_b_id}/reactivate?company_id={company_a_id}",
        headers=admin_a_headers,
    )
    assert reactivate.status_code == 403
    assert "platform superuser" in reactivate.text.lower()

    assert admin_a_id != user_b_id


def test_company_admin_cannot_globally_change_user_in_same_company(base_url):
    _, _, auth_headers = _register_and_login(base_url, "same_company_admin", "Same Company Admin")
    target_user_id, target_email, _ = _register_and_login(base_url, "same_company_target", "Same Company Target")
    company_id = _create_company(base_url, auth_headers, "SameCompany")
    _add_company_user(base_url, auth_headers, company_id, target_user_id, "viewer")

    deactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user_id}/deactivate?company_id={company_id}",
        headers=auth_headers,
    )
    assert deactivate.status_code == 403, deactivate.text

    login_still_allowed = requests.post(
        f"{base_url}/auth/login",
        json={"email": target_email, "password": PASSWORD},
    )
    assert login_still_allowed.status_code == 200

    reactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user_id}/reactivate?company_id={company_id}",
        headers=auth_headers,
    )
    assert reactivate.status_code == 403, reactivate.text


def test_viewer_cannot_deactivate_or_reactivate_company_user(
    base_url, accounting_factory
):
    admin_user = accounting_factory.create_user(full_name="Role Admin")
    viewer_user = accounting_factory.create_user(full_name="Role Viewer")
    target_user = accounting_factory.create_user(full_name="Role Target")
    accounting_factory.db.commit()

    auth_headers = accounting_factory.auth_headers_for(admin_user)
    viewer_headers = accounting_factory.auth_headers_for(viewer_user)

    company_id = _create_company(base_url, auth_headers, "RoleCompany")
    _add_company_user(base_url, auth_headers, company_id, viewer_user.id, "viewer")
    _add_company_user(base_url, auth_headers, company_id, target_user.id, "viewer")

    bad_deactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user.id}/deactivate?company_id={company_id}",
        headers=viewer_headers,
    )
    assert bad_deactivate.status_code == 403

    admin_deactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user.id}/deactivate?company_id={company_id}",
        headers=auth_headers,
    )
    assert admin_deactivate.status_code == 403, admin_deactivate.text

    bad_reactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user.id}/reactivate?company_id={company_id}",
        headers=viewer_headers,
    )
    assert bad_reactivate.status_code == 403

    admin_reactivate = requests.patch(
        f"{base_url}/company-users/users/{target_user.id}/reactivate?company_id={company_id}",
        headers=auth_headers,
    )
    assert admin_reactivate.status_code == 403, admin_reactivate.text


def test_cross_company_access_isolated_from_global_account_status(
    base_url, deterministic_superuser_headers
):
    superuser_headers = deterministic_superuser_headers
    _, _, admin_a_headers = _register_and_login(base_url, "cross_tenant_admin_a", "Cross Tenant Admin A")
    target_id, target_email, target_headers = _register_and_login(base_url, "cross_tenant_target", "Cross Tenant Target")

    company_a_id = _create_company(base_url, admin_a_headers, "CrossTenantA")
    company_b_id = _create_company(base_url, target_headers, "CrossTenantB")
    membership_a_id = _add_company_user(base_url, admin_a_headers, company_a_id, target_id, "viewer")

    removed = requests.patch(
        f"{base_url}/company-users/{membership_a_id}/remove-access",
        headers=admin_a_headers,
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["is_active"] is False
    assert removed.json()["user_is_active"] is True

    company_b_access = requests.get(
        f"{base_url}/accounts?company_id={company_b_id}",
        headers=target_headers,
    )
    assert company_b_access.status_code == 200, company_b_access.text

    forbidden_global = requests.patch(
        f"{base_url}/company-users/users/{target_id}/deactivate",
        params={"company_id": company_a_id},
        headers=admin_a_headers,
    )
    assert forbidden_global.status_code == 403

    globally_deactivated = requests.patch(
        f"{base_url}/company-users/users/{target_id}/deactivate",
        params={"company_id": company_a_id},
        headers=superuser_headers,
    )
    assert globally_deactivated.status_code == 200, globally_deactivated.text
    assert globally_deactivated.json()["is_active"] is False

    with SessionLocal() as db:
        db_user = db.get(User, target_id)
        memberships = list(db.scalars(select(CompanyUser).where(CompanyUser.user_id == target_id)).all())
        membership_by_company = {m.company_id: m for m in memberships}
        assert db_user is not None and db_user.is_active is False
        assert membership_by_company[company_a_id].is_active is False
        assert membership_by_company[company_b_id].is_active is True

    rejected_globally = requests.get(
        f"{base_url}/accounts?company_id={company_b_id}",
        headers=target_headers,
    )
    assert rejected_globally.status_code == 403

    cleanup = requests.patch(
        f"{base_url}/company-users/users/{target_id}/reactivate",
        params={"company_id": company_a_id},
        headers=superuser_headers,
    )
    assert cleanup.status_code == 200, cleanup.text
    assert cleanup.json()["is_active"] is True
    assert target_email
