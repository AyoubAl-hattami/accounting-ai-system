from sqlalchemy.orm import Session

from app.modules.accounting.schemas.account import AccountCreate, AccountSeedResult
from app.modules.accounting.services.account_service import (
    create_account,
    get_account_by_code,
)


DEFAULT_ACCOUNTS = [
    {
        "code": "1000",
        "name": "Assets",
        "account_type": "asset",
        "parent_code": None,
        "description": "Main assets category",
        "is_system": True,
    },
    {
        "code": "1110",
        "name": "Main Bank",
        "account_type": "asset",
        "parent_code": "1000",
        "description": "Main company bank account",
        "is_system": True,
    },
    {
        "code": "1200",
        "name": "Accounts Receivable",
        "account_type": "asset",
        "parent_code": "1000",
        "description": "Customer receivables",
        "is_system": True,
    },
    {
        "code": "2000",
        "name": "Liabilities",
        "account_type": "liability",
        "parent_code": None,
        "description": "Main liabilities category",
        "is_system": True,
    },
    {
        "code": "2100",
        "name": "Accounts Payable",
        "account_type": "liability",
        "parent_code": "2000",
        "description": "Supplier payables",
        "is_system": True,
    },
    {
        "code": "3000",
        "name": "Equity",
        "account_type": "equity",
        "parent_code": None,
        "description": "Main equity category",
        "is_system": True,
    },
    {
        "code": "3100",
        "name": "Owner Capital",
        "account_type": "equity",
        "parent_code": "3000",
        "description": "Owner capital",
        "is_system": True,
    },
    {
        "code": "3200",
        "name": "Retained Earnings",
        "account_type": "equity",
        "parent_code": "3000",
        "description": "Accumulated retained earnings",
        "is_system": True,
    },
    {
        "code": "4000",
        "name": "Income",
        "account_type": "income",
        "parent_code": None,
        "description": "Main income category",
        "is_system": True,
    },
    {
        "code": "4100",
        "name": "Sales Revenue",
        "account_type": "income",
        "parent_code": "4000",
        "description": "Sales revenue",
        "is_system": True,
    },
    {
        "code": "5000",
        "name": "Expenses",
        "account_type": "expense",
        "parent_code": None,
        "description": "Main expenses category",
        "is_system": True,
    },
    {
        "code": "5100",
        "name": "Rent Expense",
        "account_type": "expense",
        "parent_code": "5000",
        "description": "Office rent expense",
        "is_system": True,
    },
    {
        "code": "5200",
        "name": "Software Expense",
        "account_type": "expense",
        "parent_code": "5000",
        "description": "Software and subscription expenses",
        "is_system": True,
    },
]


def seed_default_accounts(
    db: Session,
    company_id: int,
) -> AccountSeedResult:
    created_accounts = []
    skipped_count = 0
    account_by_code = {}

    for account_def in DEFAULT_ACCOUNTS:
        existing_account = get_account_by_code(
            db=db,
            company_id=company_id,
            code=account_def["code"],
        )

        if existing_account:
            account_by_code[account_def["code"]] = existing_account
            skipped_count += 1
            continue

        parent_id = None

        if account_def["parent_code"]:
            parent_account = account_by_code.get(account_def["parent_code"])

            if parent_account is None:
                parent_account = get_account_by_code(
                    db=db,
                    company_id=company_id,
                    code=account_def["parent_code"],
                )

            if parent_account:
                parent_id = parent_account.id

        payload = AccountCreate(
            company_id=company_id,
            code=account_def["code"],
            name=account_def["name"],
            account_type=account_def["account_type"],
            parent_id=parent_id,
            description=account_def["description"],
            is_active=True,
            is_system=account_def["is_system"],
        )

        created_account = create_account(db=db, payload=payload)

        account_by_code[account_def["code"]] = created_account
        created_accounts.append(created_account)

    return AccountSeedResult(
        company_id=company_id,
        created_count=len(created_accounts),
        skipped_count=skipped_count,
        message="Default chart of accounts seeded successfully",
        accounts=created_accounts,
    )