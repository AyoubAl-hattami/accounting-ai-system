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
#
# Names are Arabic because the companies this serves keep their books in Arabic.
# Nothing matches on them: account_mapper scores an Arabic alias and the
# account_subtype equally, so a wallet is found by being an e_wallet, not by
# being spelled a particular way.
YEMEN_CASH_WALLET_ACCOUNTS: tuple[DefaultAccountDefinition, ...] = (
    DefaultAccountDefinition("1000", "الأصول", "asset", None, "المجموعة الرئيسية للأصول", True),
    DefaultAccountDefinition("1100", "الصندوق", "asset", "1000", "النقدية في الصندوق", False, "cash"),
    DefaultAccountDefinition("1110", "بنك الكريمي", "asset", "1000", "حساب بنكي", False, "bank"),
    DefaultAccountDefinition("1120", "محفظة جوالي", "asset", "1000", "محفظة إلكترونية", False, "e_wallet"),
    DefaultAccountDefinition("1130", "محفظة ون كاش", "asset", "1000", "محفظة إلكترونية", False, "e_wallet"),
    DefaultAccountDefinition("1140", "محفظة جيب", "asset", "1000", "محفظة إلكترونية", False, "e_wallet"),
    DefaultAccountDefinition("1200", "الذمم المدينة", "asset", "1000", "ذمم العملاء", True, "receivable"),
    DefaultAccountDefinition("2000", "الخصوم", "liability", None, "المجموعة الرئيسية للخصوم", True),
    DefaultAccountDefinition("2100", "الذمم الدائنة", "liability", "2000", "ذمم الموردين", True, "payable"),
    DefaultAccountDefinition("3000", "حقوق الملكية", "equity", None, "المجموعة الرئيسية لحقوق الملكية", True),
    DefaultAccountDefinition("3100", "رأس المال", "equity", "3000", "رأس مال المالك", True),
    DefaultAccountDefinition("3200", "الأرباح المحتجزة", "equity", "3000", "الأرباح المتراكمة", True),
    DefaultAccountDefinition("4000", "الإيرادات", "income", None, "المجموعة الرئيسية للإيرادات", True),
    DefaultAccountDefinition("4100", "إيرادات المبيعات", "income", "4000", "إيرادات المبيعات", True, "revenue"),
    DefaultAccountDefinition("5000", "المصروفات", "expense", None, "المجموعة الرئيسية للمصروفات", True),
    DefaultAccountDefinition("5100", "مصروف الإيجار", "expense", "5000", "إيجار المكتب والمخازن", False, "expense"),
    DefaultAccountDefinition("5200", "مصروف المرافق", "expense", "5000", "الكهرباء والماء والإنترنت", False, "expense"),
    DefaultAccountDefinition("5300", "مصروف الرواتب", "expense", "5000", "رواتب وأجور الموظفين", False, "expense"),
)


CHART_TEMPLATES: dict[str, tuple[DefaultAccountDefinition, ...]] = {
    "default": DEFAULT_ACCOUNTS,
    "yemen_cash_wallet": YEMEN_CASH_WALLET_ACCOUNTS,
}


def resolve_chart_template(template: str | None) -> tuple[DefaultAccountDefinition, ...]:
    """Return the accounts for a template name, falling back to the generic chart."""
    return CHART_TEMPLATES.get(template or "default", DEFAULT_ACCOUNTS)
