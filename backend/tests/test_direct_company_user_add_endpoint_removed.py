# COVERAGE GAP: this asserts the route is unregistered, not that the server answers
# 405 to a live request. A reviewer must run the HTTP check named in
# `test_post_company_users_has_no_registered_handler` against staging.
"""``POST /company-users`` must stay removed.

The route let any company admin post an arbitrary ``user_id`` and receive back
that account's email and full name, because nothing tied the target user to the
caller's company.  Probing integer ids answered 404 for "no such account", 201
for "account exists, here is who it is", and 409 for "already a member" -- a
complete cross-tenant directory, with an unrequested membership in the
attacker's company as a side effect.

Membership is granted through ``POST /company-users/invitations`` instead, which
keys on an email address the caller already knows and answers only
``{status, message}``.

This file exists so that reintroducing the route fails the suite rather than
passing quietly.  It reads the application's route table directly rather than
issuing HTTP calls, so it runs in the static CI job with no database or server
-- which is the point: the guard fires on every pull request, not only in the
db-backed job.
"""

from app.main import app


def _routed_pairs(prefix: str) -> set[tuple[str, str]]:
    """Every (path, method) the application actually serves under ``prefix``.

    HEAD and OPTIONS are dropped: Starlette synthesises them and they say
    nothing about which handlers this module declares.
    """
    return {
        (route.path, method)
        for route in app.routes
        if getattr(route, "path", "").startswith(prefix)
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    }


# The full surface as it stands after the direct-add route was removed.  Pinned
# as a set rather than a count so that deleting some *other* route -- or quietly
# widening one -- fails here instead of sliding past a matching total.
EXPECTED_COMPANY_USER_ROUTES = {
    ("/company-users", "GET"),
    ("/company-users/invitations", "GET"),
    ("/company-users/invitations", "POST"),
    ("/company-users/invitations/accept", "POST"),
    ("/company-users/invitations/validate", "GET"),
    ("/company-users/invitations/{invitation_id}", "DELETE"),
    ("/company-users/me", "GET"),
    ("/company-users/users/{user_id}/deactivate", "PATCH"),
    ("/company-users/users/{user_id}/reactivate", "PATCH"),
    ("/company-users/{company_user_id}", "GET"),
    ("/company-users/{company_user_id}", "PATCH"),
    ("/company-users/{company_user_id}/remove-access", "PATCH"),
    ("/company-users/{company_user_id}/restore-access", "PATCH"),
}


def test_post_company_users_has_no_registered_handler():
    """No POST handler on the collection path.

    Staging equivalent this does not cover -- run it by hand before release:

        curl -s -o /dev/null -w '%{http_code}' -X POST \\
          https://<APP_DOMAIN>/api/company-users \\
          -H "Authorization: Bearer $COMPANY_ADMIN_TOKEN" \\
          -H 'Content-Type: application/json' \\
          -d '{"company_id":1,"user_id":1,"role":"viewer","is_active":true}'

    Expect 405 (Starlette answers 405, not 404, because the path is registered
    for GET).  A 2xx means the route is back; 401 or 403 means it is back and
    merely refusing those credentials.
    """
    assert ("/company-users", "POST") not in _routed_pairs("/company-users"), (
        "POST /company-users is registered again. It allowed a company admin to "
        "add an arbitrary user_id and read back that account's email and full "
        "name. Grant membership through POST /company-users/invitations instead."
    )


def test_remaining_company_user_routes_are_unchanged():
    """Only the direct-add route went; everything else still answers.

    Without this, deleting any other handler in the module would leave the test
    above passing.
    """
    assert _routed_pairs("/company-users") == EXPECTED_COMPANY_USER_ROUTES
