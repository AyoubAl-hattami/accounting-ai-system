import requests


def test_company_users_require_authentication(base_url, default_company_id):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
    )

    assert response.status_code in (401, 403)


def test_company_users_work_with_token(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
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
    assert first_link["company_id"] == default_company_id


def test_company_users_pagination_metadata(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        (
            f"{base_url}/company-users"
            f"?company_id={default_company_id}&skip=0&limit=5"
        ),
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) <= 5
    assert data["total"] >= len(data["items"])
    assert data["skip"] == 0
    assert data["limit"] == 5


def test_cannot_remove_last_admin(
    base_url,
    admin_headers,
    default_company_id,
):
    response = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()

    admin_user = next((u for u in data["items"] if u["role"] == "admin"), None)
    assert admin_user is not None

    company_user_id = admin_user["id"]

    # Try to demote
    patch_response = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=admin_headers,
        json={"role": "accountant"},
    )
    assert patch_response.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response.text

    # Try to remove
    patch_response_2 = requests.patch(
        f"{base_url}/company-users/{company_user_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert patch_response_2.status_code == 400
    assert "Cannot demote or remove the only admin" in patch_response_2.text


def test_remove_company_access_flow(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"remove_access_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Rem User"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    # 2. Login user to get headers
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 3. Add to company
    add_member = requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": unique_email, "role": "viewer"},
        headers=admin_headers,
    )
    assert add_member.status_code == 200
    assert add_member.json()["status"] == "added_existing"

    # Get company user ID
    cu_list = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert cu_list.status_code == 200
    company_user_rec = next((item for item in cu_list.json()["items"] if item["user_id"] == user_id), None)
    assert company_user_rec is not None
    company_user_id = company_user_rec["id"]

    # 4. User can access company
    acc_check = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
        headers=user_headers,
    )
    assert acc_check.status_code == 200

    # 5. Non-admin cannot remove access
    bad_remove = requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=user_headers,
    )
    assert bad_remove.status_code in (401, 403)

    # 6. Admin can remove access
    ok_remove = requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=admin_headers,
    )
    assert ok_remove.status_code == 200
    assert ok_remove.json()["is_active"] is False

    # 7. User can no longer access company
    acc_check_blocked = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
        headers=user_headers,
    )
    assert acc_check_blocked.status_code in (401, 403)

    # 8. Check audit log
    audit = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "remove_company_access"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == company_user_id


def test_deactivate_user_account_flow(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"deactivate_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Deac User"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    # 2. Add to company
    add_member = requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": unique_email, "role": "viewer"},
        headers=admin_headers,
    )
    assert add_member.status_code == 200

    # 3. Non-admin cannot deactivate
    bad_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={default_company_id}",
    )
    assert bad_deactivate.status_code in (401, 403)

    # 4. Admin can deactivate
    ok_deactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert ok_deactivate.status_code == 200
    assert ok_deactivate.json()["is_active"] is False

    # 5. User login is blocked
    bad_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert bad_login.status_code == 401

    # 6. Check audit log
    audit = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "deactivate_user_account"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == user_id


def test_cannot_deactivate_last_admin(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"last_admin_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Sole Admin"},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    # 2. Login user to get headers
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 3. Create a new company where they are the sole admin
    create_co = requests.post(
        f"{base_url}/companies",
        headers=user_headers,
        json={
            "name": f"SoleCo_{int(time.time())}",
            "base_currency": "USD",
        },
    )
    assert create_co.status_code == 201
    co_id = create_co.json()["id"]

    # 4. Try to deactivate them using the seed admin (who is admin of that company? No, seed admin is not admin of that new company, but wait, the endpoint check allows admin of the query parameter company_id. If seed admin is NOT admin of the new company, they will be blocked with 403. So we should call deactivate using their own user_headers, but wait, they are admin of that company, so they can deactivate users if they have permission, but they can't deactivate themselves if they are the last admin).
    # Let's call deactivate with their own user_headers or admin_headers? Wait, if we call with user_headers, they are admin of co_id, so they can call it.
    res = requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={co_id}",
        headers=user_headers,
    )
    assert res.status_code == 400
    assert "Cannot delete/deactivate the last active admin" in res.text


def test_cancel_invitation_flow(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"cancel_invite_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register a regular user to use for non-admin headers
    reg_user = requests.post(
        f"{base_url}/auth/register",
        json={"email": f"non_admin_{int(time.time())}@example.com", "password": password, "full_name": "Non Admin"},
    )
    assert reg_user.status_code == 201
    login_user = requests.post(
        f"{base_url}/auth/login",
        json={"email": reg_user.json()["email"], "password": password},
    )
    user_headers = {"Authorization": f"Bearer {login_user.json()['access_token']}"}

    # 2. Admin creates invitation for unique_email
    invite_res = requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": unique_email, "role": "viewer"},
        headers=admin_headers,
    )
    assert invite_res.status_code == 200
    invite_data = invite_res.json()
    assert invite_data["status"] == "invited"
    
    # To get invitation ID
    pending_res = requests.get(
        f"{base_url}/company-users/invitations?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert pending_res.status_code == 200
    invites = pending_res.json()
    my_invite = next((inv for inv in invites if inv["email"] == unique_email), None)
    assert my_invite is not None
    invitation_id = my_invite["id"]
    invite_token = invite_data["invite_url"].split("token=")[1]

    # 3. Non-admin cannot revoke/cancel invitation
    bad_cancel = requests.delete(
        f"{base_url}/company-users/invitations/{invitation_id}",
        headers=user_headers,
    )
    assert bad_cancel.status_code in (401, 403)

    # 4. Admin can cancel invitation
    ok_cancel = requests.delete(
        f"{base_url}/company-users/invitations/{invitation_id}",
        headers=admin_headers,
    )
    assert ok_cancel.status_code == 200

    # 5. Revoked invitation cannot be validated/accepted
    validate_res = requests.get(
        f"{base_url}/auth/validate-invite?token={invite_token}"
    )
    assert validate_res.status_code in (400, 404)

    accept_res = requests.post(
        f"{base_url}/auth/accept-invite?token={invite_token}",
        json={"password": "NewPassword123", "full_name": "Should Fail"},
    )
    assert accept_res.status_code in (400, 404)

    # 6. Audit log check
    audit = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "cancel_invitation"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == invitation_id
    assert invite_token not in str(audit_events[0])


def test_restore_company_access_flow(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"restore_access_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register and login user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Restore User"},
    )
    user_id = reg.json()["id"]
    login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 2. Add to company
    add_member = requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": unique_email, "role": "viewer"},
        headers=admin_headers,
    )
    assert add_member.status_code == 200

    # Get company user ID
    cu_list = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
    )
    company_user_rec = next((item for item in cu_list.json()["items"] if item["user_id"] == user_id), None)
    company_user_id = company_user_rec["id"]

    # 3. Remove Access
    requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=admin_headers,
    )

    # 4. User blocked from company access
    acc_check = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
        headers=user_headers,
    )
    assert acc_check.status_code in (401, 403)

    # 5. Non-admin cannot restore access
    bad_restore = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=user_headers,
    )
    assert bad_restore.status_code in (401, 403)

    # 6. Admin can restore access
    ok_restore = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=admin_headers,
    )
    assert ok_restore.status_code == 200
    assert ok_restore.json()["is_active"] is True

    # 7. User can access company again
    acc_check_ok = requests.get(
        f"{base_url}/accounts?company_id={default_company_id}",
        headers=user_headers,
    )
    assert acc_check_ok.status_code == 200

    # 8. Deactivate user global account
    requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={default_company_id}",
        headers=admin_headers,
    )

    # 9. Cannot restore company access for globally deactivated account
    res_deactivated = requests.patch(
        f"{base_url}/company-users/{company_user_id}/restore-access",
        headers=admin_headers,
    )
    assert res_deactivated.status_code == 400
    assert "account is deactivated" in res_deactivated.text.lower() or "reactivate account first" in res_deactivated.text.lower()


def test_reactivate_user_account_flow(base_url, admin_headers, default_company_id):
    import time
    unique_email = f"reactivate_{int(time.time())}@example.com"
    password = "Password123"

    # 1. Register user
    reg = requests.post(
        f"{base_url}/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Reac User"},
    )
    user_id = reg.json()["id"]

    # 2. Add to company
    requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": unique_email, "role": "viewer"},
        headers=admin_headers,
    )

    # 3. Deactivate user account
    requests.patch(
        f"{base_url}/company-users/users/{user_id}/deactivate?company_id={default_company_id}",
        headers=admin_headers,
    )

    # 4. Regular login is blocked
    bad_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert bad_login.status_code == 401

    # 5. Non-admin cannot reactivate user
    other_email = f"other_{int(time.time())}@example.com"
    reg_other = requests.post(
        f"{base_url}/auth/register",
        json={"email": other_email, "password": password, "full_name": "Other User"},
    )
    login_other = requests.post(
        f"{base_url}/auth/login",
        json={"email": other_email, "password": password},
    )
    other_headers = {"Authorization": f"Bearer {login_other.json()['access_token']}"}

    bad_reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/reactivate?company_id={default_company_id}",
        headers=other_headers,
    )
    assert bad_reactivate.status_code in (401, 403)

    # 6. Admin can reactivate user
    ok_reactivate = requests.patch(
        f"{base_url}/company-users/users/{user_id}/reactivate?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert ok_reactivate.status_code == 200
    assert ok_reactivate.json()["is_active"] is True

    # 7. Reactivated user can login again
    ok_login = requests.post(
        f"{base_url}/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert ok_login.status_code == 200

    # 8. Check audit log for reactivation
    audit = requests.get(
        f"{base_url}/audit-logs?company_id={default_company_id}",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    audit_events = [ev for ev in audit.json()["items"] if ev["action"] == "reactivate_user_account"]
    assert len(audit_events) > 0
    assert audit_events[0]["entity_id"] == user_id


def test_current_user_company_role_resolutions(base_url, admin_headers, default_company_id):
    import time
    password = "Password123"

    # 1. Create accountant user
    acc_email = f"accountant_{int(time.time())}@example.com"
    reg1 = requests.post(
        f"{base_url}/auth/register",
        json={"email": acc_email, "password": password, "full_name": "Acc User"},
    )
    assert reg1.status_code == 201
    
    # Add to company as accountant
    requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": acc_email, "role": "accountant"},
        headers=admin_headers,
    )
    
    # Login accountant
    login1 = requests.post(
        f"{base_url}/auth/login",
        json={"email": acc_email, "password": password},
    )
    acc_headers = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    # 2. Accountant can call current-role /me endpoint
    me_res1 = requests.get(
        f"{base_url}/company-users/me?company_id={default_company_id}",
        headers=acc_headers,
    )
    assert me_res1.status_code == 200
    assert me_res1.json()["role"] == "accountant"
    assert me_res1.json()["is_active"] is True

    # 3. Create viewer user
    view_email = f"viewer_{int(time.time())}@example.com"
    reg2 = requests.post(
        f"{base_url}/auth/register",
        json={"email": view_email, "password": password, "full_name": "View User"},
    )
    # Add to company as viewer
    requests.post(
        f"{base_url}/company-users/invitations",
        json={"company_id": default_company_id, "email": view_email, "role": "viewer"},
        headers=admin_headers,
    )
    # Login viewer
    login2 = requests.post(
        f"{base_url}/auth/login",
        json={"email": view_email, "password": password},
    )
    view_headers = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    # Viewer can call current-role /me endpoint
    me_res2 = requests.get(
        f"{base_url}/company-users/me?company_id={default_company_id}",
        headers=view_headers,
    )
    assert me_res2.status_code == 200
    assert me_res2.json()["role"] == "viewer"
    assert me_res2.json()["is_active"] is True

    # 4. Inactive member receives 403
    cu_list = requests.get(
        f"{base_url}/company-users?company_id={default_company_id}",
        headers=admin_headers,
    )
    company_user_rec = next((item for item in cu_list.json()["items"] if item["user_id"] == reg2.json()["id"]), None)
    company_user_id = company_user_rec["id"]

    # Remove access
    requests.patch(
        f"{base_url}/company-users/{company_user_id}/remove-access",
        headers=admin_headers,
    )
    
    # Now viewer /me returns 403
    me_res3 = requests.get(
        f"{base_url}/company-users/me?company_id={default_company_id}",
        headers=view_headers,
    )
    assert me_res3.status_code == 403

    # 5. Non-member user receives 403
    non_member_email = f"non_member_{int(time.time())}@example.com"
    reg3 = requests.post(
        f"{base_url}/auth/register",
        json={"email": non_member_email, "password": password, "full_name": "Non Member"},
    )
    login3 = requests.post(
        f"{base_url}/auth/login",
        json={"email": non_member_email, "password": password},
    )
    non_member_headers = {"Authorization": f"Bearer {login3.json()['access_token']}"}

    me_res4 = requests.get(
        f"{base_url}/company-users/me?company_id={default_company_id}",
        headers=non_member_headers,
    )
    assert me_res4.status_code == 403
