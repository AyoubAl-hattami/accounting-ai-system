"""Default chart-of-accounts definitions."""

from app.application.accounts.dto import DefaultAccountDefinition


DEFAULT_ACCOUNTS: tuple[DefaultAccountDefinition, ...] = (
    DefaultAccountDefinition("1000", "Assets", "asset", None, "Main assets category", True),
    DefaultAccountDefinition("1110", "Main Bank", "asset", "1000", "Main company bank account", True),
    DefaultAccountDefinition("1200", "Accounts Receivable", "asset", "1000", "Customer receivables", True),
    DefaultAccountDefinition("2000", "Liabilities", "liability", None, "Main liabilities category", True),
    DefaultAccountDefinition("2100", "Accounts Payable", "liability", "2000", "Supplier payables", True),
    DefaultAccountDefinition("3000", "Equity", "equity", None, "Main equity category", True),
    DefaultAccountDefinition("3100", "Owner Capital", "equity", "3000", "Owner capital", True),
    DefaultAccountDefinition("3200", "Retained Earnings", "equity", "3000", "Accumulated retained earnings", True),
    DefaultAccountDefinition("4000", "Income", "income", None, "Main income category", True),
    DefaultAccountDefinition("4100", "Sales Revenue", "income", "4000", "Sales revenue", True),
    DefaultAccountDefinition("5000", "Expenses", "expense", None, "Main expenses category", True),
    DefaultAccountDefinition("5100", "Rent Expense", "expense", "5000", "Office rent expense", True),
    DefaultAccountDefinition("5200", "Software Expense", "expense", "5000", "Software and subscription expenses", True),
)
