"""Starter chart-of-accounts definitions a company may optionally seed."""

from app.application.accounts.dto import DefaultAccountDefinition


DEFAULT_ACCOUNTS: tuple[DefaultAccountDefinition, ...] = (
    DefaultAccountDefinition("1000", "Assets", "asset", None, "Main assets category", True),
    DefaultAccountDefinition("1110", "Main Bank", "asset", "1000", "Main company bank account", True, "bank"),
    DefaultAccountDefinition("1200", "Accounts Receivable", "asset", "1000", "Customer receivables", True, "receivable"),
    DefaultAccountDefinition("2000", "Liabilities", "liability", None, "Main liabilities category", True),
    DefaultAccountDefinition("2100", "Accounts Payable", "liability", "2000", "Supplier payables", True, "payable"),
    DefaultAccountDefinition("3000", "Equity", "equity", None, "Main equity category", True),
    DefaultAccountDefinition("3100", "Owner Capital", "equity", "3000", "Owner capital", True),
    DefaultAccountDefinition("3200", "Retained Earnings", "equity", "3000", "Accumulated retained earnings", True),
    DefaultAccountDefinition("4000", "Income", "income", None, "Main income category", True),
    DefaultAccountDefinition("4100", "Sales Revenue", "income", "4000", "Sales revenue", True, "revenue"),
    DefaultAccountDefinition("5000", "Expenses", "expense", None, "Main expenses category", True),
    DefaultAccountDefinition("5100", "Rent Expense", "expense", "5000", "Office rent expense", True, "expense"),
    DefaultAccountDefinition("5200", "Software Expense", "expense", "5000", "Software and subscription expenses", True, "expense"),
)


# Regional starter for businesses that settle mostly in cash and mobile wallets.
# The structural parents stay is_system so reports keep a spine; every payment
# account is an ordinary account the client can rename, re-code or delete.
YEMEN_CASH_WALLET_ACCOUNTS: tuple[DefaultAccountDefinition, ...] = (
    DefaultAccountDefinition("1000", "Assets", "asset", None, "Main assets category", True),
    DefaultAccountDefinition("1100", "Cash Box", "asset", "1000", "Physical cash box", False, "cash"),
    DefaultAccountDefinition("1110", "Al Kuraimi Bank", "asset", "1000", "Bank account", False, "bank"),
    DefaultAccountDefinition("1120", "Jawali Wallet", "asset", "1000", "Mobile wallet", False, "e_wallet"),
    DefaultAccountDefinition("1130", "One Cash Wallet", "asset", "1000", "Mobile wallet", False, "e_wallet"),
    DefaultAccountDefinition("1200", "Accounts Receivable", "asset", "1000", "Customer receivables", True, "receivable"),
    DefaultAccountDefinition("2000", "Liabilities", "liability", None, "Main liabilities category", True),
    DefaultAccountDefinition("2100", "Accounts Payable", "liability", "2000", "Supplier payables", True, "payable"),
    DefaultAccountDefinition("3000", "Equity", "equity", None, "Main equity category", True),
    DefaultAccountDefinition("3100", "Owner Capital", "equity", "3000", "Owner capital", True),
    DefaultAccountDefinition("3200", "Retained Earnings", "equity", "3000", "Accumulated retained earnings", True),
    DefaultAccountDefinition("4000", "Income", "income", None, "Main income category", True),
    DefaultAccountDefinition("4100", "Sales Revenue", "income", "4000", "Sales revenue", True, "revenue"),
    DefaultAccountDefinition("5000", "Expenses", "expense", None, "Main expenses category", True),
    DefaultAccountDefinition("5100", "Rent Expense", "expense", "5000", "Office rent expense", False, "expense"),
    DefaultAccountDefinition("5200", "Utilities Expense", "expense", "5000", "Electricity, water and internet", False, "expense"),
    DefaultAccountDefinition("5300", "Salaries Expense", "expense", "5000", "Staff salaries and wages", False, "expense"),
)


CHART_TEMPLATES: dict[str, tuple[DefaultAccountDefinition, ...]] = {
    "default": DEFAULT_ACCOUNTS,
    "yemen_cash_wallet": YEMEN_CASH_WALLET_ACCOUNTS,
}


def resolve_chart_template(template: str | None) -> tuple[DefaultAccountDefinition, ...]:
    """Return the accounts for a template name, falling back to the generic chart."""
    return CHART_TEMPLATES.get(template or "default", DEFAULT_ACCOUNTS)
