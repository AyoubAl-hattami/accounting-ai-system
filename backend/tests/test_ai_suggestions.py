import requests


COMPANY_ID = 3

# Sample accounts matching the default seeded chart of accounts
SAMPLE_ACCOUNTS = [
    {
        "id": 1,
        "code": "1000",
        "name": "Assets",
        "account_type": "asset",
        "is_active": True,
    },
    {
        "id": 2,
        "code": "1110",
        "name": "Main Bank",
        "account_type": "asset",
        "is_active": True,
    },
    {
        "id": 3,
        "code": "1200",
        "name": "Accounts Receivable",
        "account_type": "asset",
        "is_active": True,
    },
    {
        "id": 4,
        "code": "2000",
        "name": "Liabilities",
        "account_type": "liability",
        "is_active": True,
    },
    {
        "id": 5,
        "code": "2100",
        "name": "Accounts Payable",
        "account_type": "liability",
        "is_active": True,
    },
    {
        "id": 6,
        "code": "3000",
        "name": "Equity",
        "account_type": "equity",
        "is_active": True,
    },
    {
        "id": 7,
        "code": "3100",
        "name": "Owner Capital",
        "account_type": "equity",
        "is_active": True,
    },
    {
        "id": 8,
        "code": "4000",
        "name": "Income",
        "account_type": "income",
        "is_active": True,
    },
    {
        "id": 9,
        "code": "4100",
        "name": "Sales Revenue",
        "account_type": "income",
        "is_active": True,
    },
    {
        "id": 10,
        "code": "5000",
        "name": "Expenses",
        "account_type": "expense",
        "is_active": True,
    },
    {
        "id": 11,
        "code": "5100",
        "name": "Rent Expense",
        "account_type": "expense",
        "is_active": True,
    },
    {
        "id": 12,
        "code": "5200",
        "name": "Software Expense",
        "account_type": "expense",
        "is_active": True,
    },
]


def test_ai_suggestions_requires_authentication(base_url):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Paid rent from bank for 1000",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
    )

    assert response.status_code in (401, 403)


def test_ai_suggestions_rent_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Paid rent from bank for 1000",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "rent_lease"
    assert data["confidence"] == "high"
    assert data["amount"] == 1000.0
    assert data["source"] == "backend_rules"

    # Debit should be Rent Expense (id=11)
    assert data["debit_account_id"] == 11
    # Credit should be Main Bank (id=2)
    assert data["credit_account_id"] == 2

    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0
    assert isinstance(data["warnings"], list)


def test_ai_suggestions_sales_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Received sales income 2500 into bank",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "sales_revenue"
    assert data["confidence"] == "high"
    assert data["amount"] == 2500.0

    # Debit should be Main Bank (id=2)
    assert data["debit_account_id"] == 2
    # Credit should be Sales Revenue (id=9)
    assert data["credit_account_id"] == 9


def test_ai_suggestions_owner_investment_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Owner invested 5000 into bank",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "owner_investment"
    assert data["confidence"] == "high"
    assert data["amount"] == 5000.0

    # Debit should be Main Bank (id=2)
    assert data["debit_account_id"] == 2
    # Credit should be Owner Capital (id=7)
    assert data["credit_account_id"] == 7


def test_ai_suggestions_unknown_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "random text with no accounting keywords",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "unknown"
    assert data["confidence"] == "low"
    assert data["debit_account_id"] is None
    assert data["credit_account_id"] is None


def test_ai_suggestions_no_amount_medium_confidence(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Paid rent from bank",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "rent_lease"
    assert data["confidence"] == "medium"
    assert data["amount"] is None
    assert data["debit_account_id"] == 11
    assert data["credit_account_id"] == 2

    # Should have a warning about missing amount
    assert any("amount" in w.lower() for w in data["warnings"])


def test_ai_suggestions_arabic_rent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "تم دفع الإيجار من البنك بمبلغ 1000",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "ar",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "rent_lease"
    assert data["confidence"] == "high"
    assert data["amount"] == 1000.0
    assert data["source"] == "backend_rules"


def test_ai_suggestions_validates_empty_description(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 422
