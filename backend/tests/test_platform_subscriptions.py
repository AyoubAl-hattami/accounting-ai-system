"""Platform subscription administration and tenant access enforcement."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import requests

from app.modules.accounting.services.auth_service import create_user_token


BUSINESS_ENDPOINT = "/accounts"
PLATFORM_ENDPOINT = "/platform/subscriptions"


def _headers(user):
    return {"Authorization": f"Bearer {create_user_token(user)}"}


def _platform_url(base_url: str) -> str:
    return f"{base_url}{PLATFORM_ENDPOINT}"


def _subscription_detail(response):
    detail = response.json()["detail"]
    assert isinstance(detail, dict), f"expected structured detail, got {detail!r}"
    return detail


@pytest.fixture
def tenant(accounting_factory):
    """A company with an admin member and an active, unexpiring subscription."""
    company = accounting_factory.create_company(name=f"Tenant Co {uuid4().hex[:8]}")
    user = accounting_factory.create_user(full_name="Tenant Admin")
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="active")
    accounting_factory.db.commit()
    return company, user


@pytest.fixture
def platform_admin(accounting_factory):
    user = accounting_factory.create_superuser()
    accounting_factory.db.commit()
    return user


# ── platform admin surface ────────────────────────────────────────────────────


def test_platform_admin_can_list_subscriptions(base_url, tenant, platform_admin):
    company, _ = tenant

    response = requests.get(_platform_url(base_url), headers=_headers(platform_admin))

    assert response.status_code == 200
    body = response.json()
    assert {"items", "total", "skip", "limit"} <= body.keys()
    assert body["total"] >= 1

    # Every listed row carries the tenant summary the platform page renders.
    for item in body["items"]:
        assert {
            "company_id",
            "company_name",
            "base_currency",
            "effective_status",
            "member_count",
            "subscription",
        } <= item.keys()

    # The seeded tenant is asserted through search because the shared database
    # holds far more companies than one page can return.
    found = requests.get(
        f"{_platform_url(base_url)}?search={company.name}",
        headers=_headers(platform_admin),
    ).json()["items"]
    entry = next(item for item in found if item["company_id"] == company.id)
    assert entry["company_name"] == company.name
    assert entry["effective_status"] == "active"
    assert entry["member_count"] >= 1
    assert entry["subscription"]["status"] == "active"


def test_company_admin_cannot_list_platform_subscriptions(base_url, tenant):
    _, company_admin = tenant

    response = requests.get(
        _platform_url(base_url), headers=_headers(company_admin)
    )

    assert response.status_code == 403


def test_platform_subscription_list_requires_authentication(base_url):
    response = requests.get(_platform_url(base_url))
    assert response.status_code in (401, 403)


def test_platform_admin_can_search_subscriptions_by_company_name(
    base_url, tenant, platform_admin
):
    company, _ = tenant

    response = requests.get(
        f"{_platform_url(base_url)}?search={company.name}",
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200
    assert company.id in {item["company_id"] for item in response.json()["items"]}


@pytest.mark.parametrize(
    "path,method,payload",
    [
        ("/activate", "post", {}),
        ("/suspend", "post", {"reason": "unpaid"}),
        ("/cancel", "post", {}),
        ("/extend", "post", {"period": "month"}),
    ],
)
def test_subscription_actions_require_platform_admin(
    base_url, tenant, path, method, payload
):
    company, company_admin = tenant

    response = getattr(requests, method)(
        f"{_platform_url(base_url)}/{company.id}{path}",
        json=payload,
        headers=_headers(company_admin),
    )

    assert response.status_code == 403


def test_update_subscription_requires_platform_admin(base_url, tenant):
    company, company_admin = tenant

    response = requests.patch(
        f"{_platform_url(base_url)}/{company.id}",
        json={"plan_code": "pro"},
        headers=_headers(company_admin),
    )

    assert response.status_code == 403


def test_extend_by_one_month_moves_expiry_forward(base_url, tenant, platform_admin):
    company, _ = tenant
    expires_at = datetime.now(timezone.utc) + timedelta(days=5)

    requests.patch(
        f"{_platform_url(base_url)}/{company.id}",
        json={"expires_at": expires_at.isoformat()},
        headers=_headers(platform_admin),
    )

    response = requests.post(
        f"{_platform_url(base_url)}/{company.id}/extend",
        json={"period": "month"},
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200
    extended = datetime.fromisoformat(response.json()["subscription"]["expires_at"])
    assert timedelta(days=27) < extended - expires_at < timedelta(days=32)
    assert response.json()["effective_status"] == "active"


def test_extend_by_one_year_moves_expiry_forward(base_url, tenant, platform_admin):
    company, _ = tenant
    expires_at = datetime.now(timezone.utc) + timedelta(days=5)

    requests.patch(
        f"{_platform_url(base_url)}/{company.id}",
        json={"expires_at": expires_at.isoformat()},
        headers=_headers(platform_admin),
    )

    response = requests.post(
        f"{_platform_url(base_url)}/{company.id}/extend",
        json={"period": "year"},
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200
    extended = datetime.fromisoformat(response.json()["subscription"]["expires_at"])
    assert timedelta(days=360) < extended - expires_at < timedelta(days=370)


def test_suspend_then_activate_restores_access(base_url, tenant, platform_admin):
    company, company_admin = tenant

    suspend = requests.post(
        f"{_platform_url(base_url)}/{company.id}/suspend",
        json={"reason": "payment failed"},
        headers=_headers(platform_admin),
    )
    assert suspend.status_code == 200
    assert suspend.json()["effective_status"] == "suspended"
    assert suspend.json()["subscription"]["suspension_reason"] == "payment failed"

    blocked = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(company_admin),
    )
    assert blocked.status_code == 403

    activate = requests.post(
        f"{_platform_url(base_url)}/{company.id}/activate",
        json={},
        headers=_headers(platform_admin),
    )
    assert activate.status_code == 200
    assert activate.json()["effective_status"] == "active"
    assert activate.json()["subscription"]["suspension_reason"] is None

    allowed = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(company_admin),
    )
    assert allowed.status_code == 200


def test_cancel_records_timestamp_and_blocks_the_tenant(
    base_url, tenant, platform_admin
):
    company, company_admin = tenant

    response = requests.post(
        f"{_platform_url(base_url)}/{company.id}/cancel",
        json={"reason": "customer left"},
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200
    assert response.json()["effective_status"] == "cancelled"
    assert response.json()["subscription"]["cancelled_at"] is not None

    blocked = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(company_admin),
    )
    assert blocked.status_code == 403


def test_extension_does_not_resurrect_a_cancelled_subscription(
    base_url, tenant, platform_admin
):
    company, _ = tenant

    requests.post(
        f"{_platform_url(base_url)}/{company.id}/cancel",
        json={},
        headers=_headers(platform_admin),
    )

    response = requests.post(
        f"{_platform_url(base_url)}/{company.id}/extend",
        json={"period": "year"},
        headers=_headers(platform_admin),
    )

    assert response.status_code == 200
    assert response.json()["effective_status"] == "cancelled"


def test_platform_subscription_detail_404s_for_an_unknown_company(
    base_url, platform_admin
):
    response = requests.get(
        f"{_platform_url(base_url)}/99999999",
        headers=_headers(platform_admin),
    )
    assert response.status_code == 404


# ── tenant access enforcement ─────────────────────────────────────────────────


def test_active_company_can_reach_a_business_endpoint(base_url, tenant):
    company, user = tenant

    response = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(user),
    )

    assert response.status_code == 200


def test_expired_company_is_blocked_with_subscription_inactive(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    user = accounting_factory.create_user()
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(
        company=company,
        status="active",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    accounting_factory.db.commit()

    response = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(user),
    )

    assert response.status_code == 403
    detail = _subscription_detail(response)
    assert detail["code"] == "SUBSCRIPTION_INACTIVE"
    assert detail["message"] == "Company subscription is inactive or expired."
    assert detail["status"] == "past_due"


def test_suspended_company_is_blocked_with_subscription_inactive(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    user = accounting_factory.create_user()
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="suspended")
    accounting_factory.db.commit()

    response = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(user),
    )

    assert response.status_code == 403
    assert _subscription_detail(response)["code"] == "SUBSCRIPTION_INACTIVE"


def test_company_admin_does_not_bypass_the_subscription_gate(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    admin = accounting_factory.create_user()
    accounting_factory.add_company_user(company=company, user=admin, role="admin")
    accounting_factory.set_subscription(company=company, status="cancelled")
    accounting_factory.db.commit()

    response = requests.get(
        f"{base_url}/company-users?company_id={company.id}",
        headers=_headers(admin),
    )

    assert response.status_code == 403
    assert _subscription_detail(response)["code"] == "SUBSCRIPTION_INACTIVE"


def test_locked_out_member_can_still_read_its_role_and_subscription_status(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    user = accounting_factory.create_user()
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="suspended")
    accounting_factory.db.commit()

    role = requests.get(
        f"{base_url}/company-users/me?company_id={company.id}",
        headers=_headers(user),
    )
    assert role.status_code == 200
    assert role.json()["role"] == "admin"

    status_response = requests.get(
        f"{base_url}/companies/{company.id}/subscription",
        headers=_headers(user),
    )
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["effective_status"] == "suspended"
    assert body["is_active"] is False


def test_login_and_me_are_never_blocked_by_the_subscription_gate(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    email = accounting_factory.unique_email("locked-out")
    user = accounting_factory.create_user(email=email)
    accounting_factory.add_company_user(company=company, user=user, role="admin")
    accounting_factory.set_subscription(company=company, status="cancelled")
    accounting_factory.db.commit()

    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": "Password123"},
    )
    assert login.status_code == 200

    me = requests.get(
        f"{base_url}/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


# ── tenant isolation ──────────────────────────────────────────────────────────


def test_company_user_cannot_see_or_reach_another_company(base_url, accounting_factory):
    own_company = accounting_factory.create_company(name="Own Co")
    other_company = accounting_factory.create_company(name="Other Co")
    user = accounting_factory.create_user()
    accounting_factory.add_company_user(company=own_company, user=user, role="admin")
    accounting_factory.set_subscription(company=own_company, status="active")
    accounting_factory.set_subscription(company=other_company, status="active")
    accounting_factory.db.commit()

    listed = requests.get(f"{base_url}/companies?limit=500", headers=_headers(user))
    assert listed.status_code == 200
    visible = {item["id"] for item in listed.json()["items"]}
    assert own_company.id in visible
    assert other_company.id not in visible

    reached = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={other_company.id}",
        headers=_headers(user),
    )
    assert reached.status_code == 403
    assert reached.json()["detail"] == "You do not have access to this company"


def test_non_member_is_refused_before_subscription_state_leaks(
    base_url, accounting_factory
):
    company = accounting_factory.create_company()
    outsider = accounting_factory.create_user()
    accounting_factory.set_subscription(company=company, status="suspended")
    accounting_factory.db.commit()

    response = requests.get(
        f"{base_url}{BUSINESS_ENDPOINT}?company_id={company.id}",
        headers=_headers(outsider),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have access to this company"
