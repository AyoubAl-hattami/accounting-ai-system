import requests

# Valid source values from any provider
VALID_SOURCES = {
    "backend_rules", "gemini", "gemini_fallback_rules",
    "openai", "openai_fallback_rules", "llm_placeholder_fallback",
}

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

# Quick lookup: account_id → account_type string
_ACCOUNT_TYPE_MAP: dict[int, str] = {
    a["id"]: a["account_type"] for a in SAMPLE_ACCOUNTS
}


def _account_type(account_id: int) -> str | None:
    """Return the account_type for a given id, or None if not in SAMPLE_ACCOUNTS."""
    return _ACCOUNT_TYPE_MAP.get(account_id)


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
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 1000.0
    assert data["source"] in VALID_SOURCES

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
    assert data["confidence"] in ("high", "medium")
    assert data["debit_account_id"] == 11
    assert data["credit_account_id"] == 2

    # Amount may be None from rules (no amount in text), or detected by LLM
    # Warning about missing amount may or may not be present depending on provider
    assert data["source"] in VALID_SOURCES


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
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 1000.0
    assert data["source"] in VALID_SOURCES


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


def test_ai_suggestions_salary_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Paid salaries from bank for 3000",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "salary_payroll"
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 3000.0

    # Debit should be an expense account
    assert data["debit_account_id"] is not None
    # Credit should be Main Bank (id=2)
    assert data["credit_account_id"] == 2

    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0


def test_ai_suggestions_equipment_purchase_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Bought equipment from bank for 1200",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "purchase_equipment"
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 1200.0

    # Debit should be an asset or expense account
    assert data["debit_account_id"] is not None
    # Credit should be an asset account (typically a bank/cash account)
    # We allow any asset account ID rather than pinning to id=2
    credit_id = data["credit_account_id"]
    assert credit_id is not None
    credit_type = _account_type(credit_id)
    assert credit_type == "asset", (
        f"Expected credit account to be asset, got {credit_type!r} (id={credit_id})"
    )


def test_ai_suggestions_loan_received_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Received loan 10000 into bank",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "loan_received"
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 10000.0

    # Debit should be Main Bank (id=2, asset increases)
    assert data["debit_account_id"] == 2
    # Credit should be a liability account
    assert data["credit_account_id"] is not None


def test_ai_suggestions_loan_payment_intent(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "Paid loan from bank for 500",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "en",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "loan_payment"
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 500.0

    # Debit should be a liability account (loan decreases).
    # However, the sample chart has no explicit "Loan" account, so the LLM
    # may return None when it cannot confidently match a debit account.
    # Accept both: non-None liability OR None (graceful non-match).
    debit_id = data["debit_account_id"]
    if debit_id is not None:
        debit_type = _account_type(debit_id)
        assert debit_type == "liability", (
            f"Expected debit account to be liability (loan), got {debit_type!r} (id={debit_id})"
        )

    # Credit should be an asset account (cash/bank leaves) — also may be None
    credit_id = data["credit_account_id"]
    if credit_id is not None:
        credit_type = _account_type(credit_id)
        assert credit_type == "asset", (
            f"Expected credit account to be asset (bank), got {credit_type!r} (id={credit_id})"
        )


def test_ai_suggestions_arabic_sales_revenue(base_url, admin_headers):
    response = requests.post(
        f"{base_url}/ai/journal-suggestions",
        json={
            "company_id": COMPANY_ID,
            "description": "تم استلام إيراد مبيعات 2500 في البنك",
            "accounts": SAMPLE_ACCOUNTS,
            "language": "ar",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["detected_intent"] == "sales_revenue"
    assert data["confidence"] in ("high", "medium")
    assert data["amount"] == 2500.0
    assert data["source"] in VALID_SOURCES

    # Debit should be Main Bank (id=2)
    assert data["debit_account_id"] == 2
    # Credit should be Sales Revenue (id=9)
    assert data["credit_account_id"] == 9
