"""Guard: fiscal year dates cannot be changed once journal entries exist."""
import requests


def test_fiscal_year_dates_cannot_change_when_entries_exist(
    base_url,
    deterministic_accounting_bootstrap,
    accounting_factory,
):
    """PATCH /fiscal-years/{id} must return 400 when entries are linked."""
    factory = accounting_factory
    bs = deterministic_accounting_bootstrap

    # Create a journal entry linked to the factory fiscal year.
    factory.create_balanced_journal(bootstrap=bs)
    factory.db.commit()

    response = requests.patch(
        f"{base_url}/fiscal-years/{bs.fiscal_year.id}",
        headers=bs.auth_headers,
        json={"start_date": "2000-01-01"},
    )

    assert response.status_code == 400
    assert "journal entries already exist" in response.json()["detail"]
