"""
Deterministic rules engine for journal entry suggestions.

This is a Python port of the frontend journalAssistantRules.ts,
providing identical intent detection, account matching, and amount
extraction logic on the backend.

No external AI services, no API keys, no database access.
"""

import re

from app.modules.accounting.schemas.ai_suggestion_schemas import AccountInfo


def extract_amount(text: str) -> float | None:
    """
    Extract a numeric transaction amount from the text description.
    Strips date patterns to avoid interpreting years as amounts.
    """
    # Strip dates (YYYY-MM-DD, YYYY/MM/DD)
    clean_text = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", "", text)
    # Strip dates (DD-MM-YYYY, DD/MM/YYYY)
    clean_text = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b", "", clean_text)

    # Match numbers optionally with currency symbols or commas/decimals
    regex = re.compile(
        r"(?:[$£€¥]\s*)?(\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?)"
        r"(?:\s*(?:USD|EUR|GBP|SAR|AED|ريال|دولار|جنيه))?",
        re.IGNORECASE,
    )

    candidates: list[dict] = []

    for match in regex.finditer(clean_text):
        raw_num = match.group(1)
        parsed = float(raw_num.replace(",", ""))
        if parsed > 0:
            candidates.append({
                "value": parsed,
                "index": match.start(),
                "text": match.group(0),
            })

    if not candidates:
        return None

    # Prefer candidates that are not year-like numbers (2000–2100)
    # unless they have clear currency identifiers
    currency_pattern = re.compile(
        r"[$£€¥]|USD|EUR|GBP|SAR|AED|ريال|دولار|جنيه",
        re.IGNORECASE,
    )

    non_year_candidates = [
        c for c in candidates
        if c["value"] < 2000
        or c["value"] > 2100
        or currency_pattern.search(c["text"])
    ]

    if non_year_candidates:
        return non_year_candidates[0]["value"]

    return candidates[0]["value"]


def find_bank_cash_account(
    accounts: list[AccountInfo],
) -> AccountInfo | None:
    """Find a bank or cash asset account from the chart of accounts."""
    assets = [a for a in accounts if a.is_active and a.account_type == "asset"]
    if not assets:
        return None

    keywords = [
        "bank", "cash", "petty", "main bank",
        "بنك", "البنك", "نقد", "نقدية", "صندوق", "الصندوق",
    ]

    for kw in keywords:
        for a in assets:
            if kw in a.name.lower() or kw in a.code.lower():
                return a

    # Fallback to first asset account
    return assets[0]


def find_account_by_type_and_keywords(
    accounts: list[AccountInfo],
    account_type: str,
    keywords: list[str],
    fallback_keywords: list[str],
) -> AccountInfo | None:
    """Match an account of a given type based on prioritized keywords."""
    filtered = [
        a for a in accounts
        if a.is_active and a.account_type == account_type
    ]
    if not filtered:
        return None

    # Priority 1: specific keywords
    for kw in keywords:
        for a in filtered:
            if kw in a.name.lower() or kw in a.code.lower():
                return a

    # Priority 2: fallback keywords
    for kw in fallback_keywords:
        for a in filtered:
            if kw in a.name.lower() or kw in a.code.lower():
                return a

    # Fallback to first active account of this type
    return filtered[0]


def suggest_journal_entry(
    description: str,
    accounts: list[AccountInfo],
    language: str = "en",
) -> dict:
    """
    Main deterministic rules engine to suggest debit/credit journal entries.
    Returns a dict matching JournalSuggestionResponse fields.
    """
    text = description.lower().strip()
    amount = extract_amount(description)

    detected_intent = "unknown"
    debit_account: AccountInfo | None = None
    credit_account: AccountInfo | None = None
    explanation = ""
    warnings: list[str] = []

    # 1. Rent / Lease
    if (
        re.search(r"\b(rent|lease)\b", text, re.IGNORECASE)
        or any(kw in text for kw in ["إيجار", "ايجار", "أجار", "اجار"])
    ):
        detected_intent = "rent_lease"
        debit_account = find_account_by_type_and_keywords(
            accounts,
            "expense",
            ["rent", "lease", "5100", "إيجار", "ايجار", "أجار", "اجار"],
            ["expense", "expenses", "مصروف", "مصاريف"],
        )
        credit_account = find_bank_cash_account(accounts)
        explanation = (
            "الإيجار هو مصروف، لذلك يزيد بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن."
            if language == "ar"
            else "Rent is an expense, so it increases by debit. Bank/Cash decreases by credit."
        )

    # 2. Salary / Wages / Payroll
    elif (
        re.search(
            r"\b(salary|salaries|wage|wages|payroll|paycheck)\b",
            text,
            re.IGNORECASE,
        )
        or any(
            kw in text
            for kw in ["رواتب", "راتب", "أجور", "اجور", "مرتب", "مرتبات"]
        )
    ):
        detected_intent = "salary_payroll"
        debit_account = find_account_by_type_and_keywords(
            accounts,
            "expense",
            [
                "salary", "wage", "payroll",
                "رواتب", "راتب", "أجور", "اجور", "مرتب", "مرتبات",
            ],
            ["expense", "expenses", "5000", "مصروف", "مصاريف"],
        )
        credit_account = find_bank_cash_account(accounts)
        explanation = (
            "الرواتب والأجور هي مصاريف، لذلك تزيد بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن."
            if language == "ar"
            else "Salaries and wages are expenses, so they increase by debit. Bank/Cash decreases by credit."
        )

    # 3. Sales / Revenue / Income
    elif (
        re.search(
            r"\b(sales|sale|revenue|income|earning|earnings|sold)\b",
            text,
            re.IGNORECASE,
        )
        or any(
            kw in text
            for kw in [
                "مبيعات", "بيع", "إيراد", "ايراد",
                "إيرادات", "ايرادات", "دخل",
            ]
        )
    ):
        detected_intent = "sales_revenue"
        debit_account = find_bank_cash_account(accounts)
        credit_account = find_account_by_type_and_keywords(
            accounts,
            "income",
            [
                "sales", "sale", "revenue", "income",
                "مبيعات", "بيع", "إيراد", "ايراد", "إيرادات", "دخل",
            ],
            ["income", "revenue", "إيراد", "ايراد"],
        )
        explanation = (
            "تم استلام إيراد مبيعات، مما يزيد البنك/النقدية (أصل) بالجانب المدين. "
            "المبيعات/الإيرادات تزيد بالجانب الدائن."
            if language == "ar"
            else "Received sales income, which increases Bank/Cash (asset) by debit. "
            "Sales/Revenue increases by credit."
        )

    # 4. Owner Investment / Capital Contribution
    elif (
        re.search(
            r"\b(invest|invested|investment|capital|contribution)\b",
            text,
            re.IGNORECASE,
        )
        or any(
            kw in text
            for kw in ["رأس المال", "راس المال", "استثمار", "مساهمة"]
        )
    ):
        detected_intent = "owner_investment"
        debit_account = find_bank_cash_account(accounts)
        credit_account = find_account_by_type_and_keywords(
            accounts,
            "equity",
            [
                "capital", "owner", "invest", "equity",
                "رأس المال", "راس المال", "استثمار", "حقوق الملكية",
            ],
            ["equity", "capital", "رأس المال", "حقوق الملكية"],
        )
        explanation = (
            "استثمر المالك رأس مال، مما يزيد البنك/النقدية (أصل) بالجانب المدين. "
            "رأس المال/حقوق الملكية تزيد بالجانب الدائن."
            if language == "ar"
            else "Owner invested capital, which increases Bank/Cash (asset) by debit. "
            "Owner Capital/Equity increases by credit."
        )

    # 5. Loan Payment & Received
    elif (
        re.search(
            r"\b(loan|borrow|debt|installment)\b",
            text,
            re.IGNORECASE,
        )
        or any(
            kw in text
            for kw in ["قرض", "سداد قروض", "تسديد قروض", "سلفة"]
        )
    ):
        is_payment = bool(
            re.search(
                r"\b(pay|paid|payment|repay|repayment|installment|repaying)\b",
                text,
                re.IGNORECASE,
            )
            or any(
                kw in text
                for kw in ["سداد", "تسديد", "دفع", "دفعة"]
            )
        )

        if is_payment:
            detected_intent = "loan_payment"
            debit_account = find_account_by_type_and_keywords(
                accounts,
                "liability",
                ["loan", "borrow", "liability", "قرض", "التزام", "التزامات"],
                ["liability", "payable", "التزام", "دائنين"],
            )
            credit_account = find_bank_cash_account(accounts)
            explanation = (
                "تم سداد دفعة القرض، مما يخفض التزام القرض بالجانب المدين. "
                "البنك/النقدية ينقص بالجانب الدائن."
                if language == "ar"
                else "Paid loan installment, which decreases loan liability by debit. "
                "Bank/Cash decreases by credit."
            )
        else:
            detected_intent = "loan_received"
            debit_account = find_bank_cash_account(accounts)
            credit_account = find_account_by_type_and_keywords(
                accounts,
                "liability",
                ["loan", "borrow", "liability", "قرض", "التزام", "التزامات"],
                ["liability", "payable", "التزام", "دائنين"],
            )
            explanation = (
                "تم استلام قرض، مما يزيد البنك/النقدية (أصل) بالجانب المدين. "
                "التزام القرض يزيد بالجانب الدائن."
                if language == "ar"
                else "Received loan, which increases Bank/Cash (asset) by debit. "
                "Loan liability increases by credit."
            )

    # 6. Purchase / Bought / Equipment / Assets
    elif (
        re.search(
            r"\b(purchase|purchased|bought|equipment|machinery|"
            r"asset|furniture|office|supplies)\b",
            text,
            re.IGNORECASE,
        )
        or any(
            kw in text
            for kw in [
                "شراء", "معدات", "أثاث", "اثاث",
                "أصول", "اصول", "مستلزمات",
            ]
        )
    ):
        detected_intent = "purchase_equipment"

        target_debit = find_account_by_type_and_keywords(
            accounts,
            "asset",
            [
                "equipment", "machinery", "furniture", "device", "office",
                "معدات", "أثاث", "أجهزة", "مكتب",
            ],
            ["assets", "الأصول", "الاصول"],
        )

        # If it resolves to the generic top-level parent asset (code 1000),
        # search for expense-based purchases
        if not target_debit or target_debit.code == "1000":
            expense_debit = find_account_by_type_and_keywords(
                accounts,
                "expense",
                [
                    "software", "supplies", "purchase", "office",
                    "برمجيات", "مستلزمات", "مصروف",
                ],
                ["expense", "expenses", "مصروف", "مصاريف"],
            )
            if expense_debit:
                target_debit = expense_debit

        debit_account = target_debit
        credit_account = find_bank_cash_account(accounts)
        explanation = (
            "شراء أصل/معدات أو مصروف، مما يزيده بالجانب المدين. "
            "البنك/النقدية ينقص بالجانب الدائن."
            if language == "ar"
            else "Purchased asset/equipment or expense, which increases by debit. "
            "Bank/Cash decreases by credit."
        )

    # 7. Unknown Intent
    else:
        detected_intent = "unknown"
        explanation = (
            "تعذر تحديد نوع المعاملة من الوصف المقدم. "
            "حاول استخدام كلمات مفتاحية مثل \"دفع\"، \"استلام\"، \"شراء\" أو \"إيجار\"."
            if language == "ar"
            else "Could not identify the transaction type from the description. "
            "Try using keywords like \"paid\", \"received\", \"bought\", or \"rent\"."
        )

    # Account matching validation warnings
    if not debit_account and detected_intent != "unknown":
        warnings.append(
            "لم نتمكن من تحديد حساب مدين مناسب بثقة في دليل الحسابات."
            if language == "ar"
            else "Could not confidently match a suitable debit account "
            "in your chart of accounts."
        )

    if not credit_account and detected_intent != "unknown":
        warnings.append(
            "لم نتمكن من تحديد حساب دائن مناسب بثقة في دليل الحسابات."
            if language == "ar"
            else "Could not confidently match a suitable credit account "
            "in your chart of accounts."
        )

    # Amount extraction validation warnings
    if amount is None:
        warnings.append(
            "لم يتم العثور على مبلغ العملية في الوصف. يرجى إدخال المبلغ يدوياً."
            if language == "ar"
            else "No transaction amount detected. Please enter the amount manually."
        )

    # Determine suggestion confidence level
    confidence = "low"
    if detected_intent != "unknown" and debit_account and credit_account:
        confidence = "high" if amount is not None else "medium"

    return {
        "debit_account_id": debit_account.id if debit_account else None,
        "credit_account_id": credit_account.id if credit_account else None,
        "amount": amount,
        "confidence": confidence,
        "explanation": explanation,
        "warnings": warnings,
        "detected_intent": detected_intent,
        "source": "backend_rules",
    }
