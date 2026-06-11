import type { Account, JournalAssistantSuggestion, JournalAssistantInput } from './types';

/**
 * Extracts a numeric transaction amount from the text description.
 * It ignores dates and year-like numbers when alternative amounts are present.
 */
export function extractAmount(text: string): number | undefined {
  // Strip dates (YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY) to avoid extracting years/months/days as amounts
  let cleanText = text.replace(/\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/g, '');
  cleanText = cleanText.replace(/\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b/g, '');

  // Match numbers optionally with currency symbols or commas/decimals
  const regex = /(?:[$£€¥]\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s*(?:USD|EUR|GBP|SAR|AED|ريال|دولار|جنيه))?/gi;
  
  let match;
  const candidates: { value: number; index: number; text: string }[] = [];
  
  while ((match = regex.exec(cleanText)) !== null) {
    const rawNum = match[1];
    // Remove formatting commas
    const parsed = parseFloat(rawNum.replace(/,/g, ''));
    if (!isNaN(parsed) && parsed > 0) {
      candidates.push({ value: parsed, index: match.index, text: match[0] });
    }
  }
  
  if (candidates.length === 0) return undefined;
  
  // Prefer candidates that are not year-like numbers (between 2000 and 2100)
  // unless they have clear currency identifiers or there are no other options.
  const nonYearCandidates = candidates.filter(
    c => c.value < 2000 || c.value > 2100 || c.text.match(/[$£€¥|USD|EUR|GBP|SAR|AED|ريال|دولار|جنيه]/i)
  );
  
  if (nonYearCandidates.length > 0) {
    return nonYearCandidates[0].value;
  }
  
  return candidates[0].value;
}

/**
 * Finds a bank or cash asset account from the chart of accounts.
 */
export function findBankCashAccount(accounts: Account[]): Account | undefined {
  const assets = accounts.filter(a => a.is_active && a.account_type === 'asset');
  if (assets.length === 0) return undefined;

  // Keyword list prioritizing cash and bank
  const keywords = ['bank', 'cash', 'petty', 'main bank', 'بنك', 'البنك', 'نقد', 'نقدية', 'صندوق', 'الصندوق'];
  for (const kw of keywords) {
    const matched = assets.find(a => a.name.toLowerCase().includes(kw) || a.code.toLowerCase().includes(kw));
    if (matched) return matched;
  }

  // Fallback to first asset account
  return assets[0];
}

/**
 * Helper to match an account of a given type based on prioritized keywords and fallbacks.
 */
function findAccountByTypeAndKeywords(
  accounts: Account[],
  type: string,
  keywords: string[],
  fallbackKeywords: string[]
): Account | undefined {
  const filtered = accounts.filter(a => a.is_active && a.account_type === type);
  if (filtered.length === 0) return undefined;

  // Priority 1: Match specific search keywords
  for (const kw of keywords) {
    const matched = filtered.find(a => a.name.toLowerCase().includes(kw) || a.code.toLowerCase().includes(kw));
    if (matched) return matched;
  }

  // Priority 2: Match fallback keywords
  for (const kw of fallbackKeywords) {
    const matched = filtered.find(a => a.name.toLowerCase().includes(kw) || a.code.toLowerCase().includes(kw));
    if (matched) return matched;
  }

  // Fallback to the first active account of this type
  return filtered[0];
}

/**
 * Main deterministic rules engine to suggest debit/credit journal entries.
 */
export function suggestJournalEntry({ description, accounts, language }: JournalAssistantInput): JournalAssistantSuggestion {
  const text = description.toLowerCase().trim();
  const amount = extractAmount(description);
  
  let detectedIntent = 'unknown';
  let debitAccount: Account | undefined;
  let creditAccount: Account | undefined;
  let explanation = '';
  const warnings: string[] = [];

  // 1. Rent / Lease
  if (
    text.match(/\b(rent|lease)\b/i) || 
    text.includes('إيجار') || text.includes('ايجار') || text.includes('أجار') || text.includes('اجار')
  ) {
    detectedIntent = 'rent_lease';
    debitAccount = findAccountByTypeAndKeywords(
      accounts,
      'expense',
      ['rent', 'lease', '5100', 'إيجار', 'ايجار', 'أجار', 'اجار'],
      ['expense', 'expenses', 'مصروف', 'مصاريف']
    );
    creditAccount = findBankCashAccount(accounts);
    explanation = language === 'ar'
      ? 'الإيجار هو مصروف، لذلك يزيد بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن.'
      : 'Rent is an expense, so it increases by debit. Bank/Cash decreases by credit.';
  }
  // 2. Salary / Wages / Payroll
  else if (
    text.match(/\b(salary|salaries|wage|wages|payroll|paycheck)\b/i) || 
    text.includes('رواتب') || text.includes('راتب') || text.includes('أجور') || text.includes('اجور') || text.includes('مرتب') || text.includes('مرتبات')
  ) {
    detectedIntent = 'salary_payroll';
    debitAccount = findAccountByTypeAndKeywords(
      accounts,
      'expense',
      ['salary', 'wage', 'payroll', 'رواتب', 'راتب', 'أجور', 'اجور', 'مرتب', 'مرتبات'],
      ['expense', 'expenses', '5000', 'مصروف', 'مصاريف']
    );
    creditAccount = findBankCashAccount(accounts);
    explanation = language === 'ar'
      ? 'الرواتب والأجور هي مصاريف، لذلك تزيد بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن.'
      : 'Salaries and wages are expenses, so they increase by debit. Bank/Cash decreases by credit.';
  }
  // 3. Sales / Revenue / Income
  else if (
    text.match(/\b(sales|sale|revenue|income|earning|earnings|sold)\b/i) ||
    text.includes('مبيعات') || text.includes('بيع') || text.includes('إيراد') || text.includes('ايراد') || text.includes('إيرادات') || text.includes('ايرادات') || text.includes('دخل')
  ) {
    detectedIntent = 'sales_revenue';
    debitAccount = findBankCashAccount(accounts);
    creditAccount = findAccountByTypeAndKeywords(
      accounts,
      'income',
      ['sales', 'sale', 'revenue', 'income', 'مبيعات', 'بيع', 'إيراد', 'ايراد', 'إيرادات', 'دخل'],
      ['income', 'revenue', 'إيراد', 'ايراد']
    );
    explanation = language === 'ar'
      ? 'تم استلام إيراد مبيعات، مما يزيد البنك/النقدية (أصل) بالجانب المدين. المبيعات/الإيرادات تزيد بالجانب الدائن.'
      : 'Received sales income, which increases Bank/Cash (asset) by debit. Sales/Revenue increases by credit.';
  }
  // 4. Owner Investment / Capital Contribution
  else if (
    text.match(/\b(invest|invested|investment|capital|contribution)\b/i) ||
    text.includes('رأس المال') || text.includes('راس المال') || text.includes('استثمار') || text.includes('مساهمة')
  ) {
    detectedIntent = 'owner_investment';
    debitAccount = findBankCashAccount(accounts);
    creditAccount = findAccountByTypeAndKeywords(
      accounts,
      'equity',
      ['capital', 'owner', 'invest', 'equity', 'رأس المال', 'راس المال', 'استثمار', 'حقوق الملكية'],
      ['equity', 'capital', 'رأس المال', 'حقوق الملكية']
    );
    explanation = language === 'ar'
      ? 'استثمر المالك رأس مال، مما يزيد البنك/النقدية (أصل) بالجانب المدين. رأس المال/حقوق الملكية تزيد بالجانب الدائن.'
      : 'Owner invested capital, which increases Bank/Cash (asset) by debit. Owner Capital/Equity increases by credit.';
  }
  // 5. Loan Payment & Received
  else if (
    text.match(/\b(loan|borrow|debt|installment)\b/i) ||
    text.includes('قرض') || text.includes('سداد قروض') || text.includes('تسديد قروض') || text.includes('سلفة')
  ) {
    const isPayment = text.match(/\b(pay|paid|payment|repay|repayment|installment|repaying)\b/i) ||
                      text.includes('سداد') || text.includes('تسديد') || text.includes('دفع') || text.includes('دفعة');
    
    if (isPayment) {
      detectedIntent = 'loan_payment';
      debitAccount = findAccountByTypeAndKeywords(
        accounts,
        'liability',
        ['loan', 'borrow', 'liability', 'قرض', 'التزام', 'التزامات'],
        ['liability', 'payable', 'التزام', 'دائنين']
      );
      creditAccount = findBankCashAccount(accounts);
      explanation = language === 'ar'
        ? 'تم سداد دفعة القرض، مما يخفض التزام القرض بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن.'
        : 'Paid loan installment, which decreases loan liability by debit. Bank/Cash decreases by credit.';
    } else {
      detectedIntent = 'loan_received';
      debitAccount = findBankCashAccount(accounts);
      creditAccount = findAccountByTypeAndKeywords(
        accounts,
        'liability',
        ['loan', 'borrow', 'liability', 'قرض', 'التزام', 'التزامات'],
        ['liability', 'payable', 'التزام', 'دائنين']
      );
      explanation = language === 'ar'
        ? 'تم استلام قرض، مما يزيد البنك/النقدية (أصل) بالجانب المدين. التزام القرض يزيد بالجانب الدائن.'
        : 'Received loan, which increases Bank/Cash (asset) by debit. Loan liability increases by credit.';
    }
  }
  // 6. Purchase / Bought / Equipment / Assets
  else if (
    text.match(/\b(purchase|purchased|bought|equipment|machinery|asset|furniture|office|supplies)\b/i) ||
    text.includes('شراء') || text.includes('معدات') || text.includes('أثاث') || text.includes('اثاث') || text.includes('أصول') || text.includes('اصول') || text.includes('مستلزمات')
  ) {
    detectedIntent = 'purchase_equipment';
    
    // First priority: look for a specific Equipment/Machinery/Asset asset account
    let targetDebit = findAccountByTypeAndKeywords(
      accounts,
      'asset',
      ['equipment', 'machinery', 'furniture', 'device', 'office', 'معدات', 'أثاث', 'أجهزة', 'مكتب'],
      ['assets', 'الأصول', 'الاصول']
    );
    
    // If it resolves to the generic top-level parent asset (code 1000), search for expense-based purchases (e.g. software)
    if (!targetDebit || targetDebit.code === '1000') {
      const expenseDebit = findAccountByTypeAndKeywords(
        accounts,
        'expense',
        ['software', 'supplies', 'purchase', 'office', 'برمجيات', 'مستلزمات', 'مصروف'],
        ['expense', 'expenses', 'مصروف', 'مصاريف']
      );
      if (expenseDebit) {
        targetDebit = expenseDebit;
      }
    }
    
    debitAccount = targetDebit;
    creditAccount = findBankCashAccount(accounts);
    explanation = language === 'ar'
      ? 'شراء أصل/معدات أو مصروف، مما يزيده بالجانب المدين. البنك/النقدية ينقص بالجانب الدائن.'
      : 'Purchased asset/equipment or expense, which increases by debit. Bank/Cash decreases by credit.';
  }
  // 7. Unknown Intent
  else {
    detectedIntent = 'unknown';
    explanation = language === 'ar'
      ? 'تعذر تحديد نوع المعاملة من الوصف المقدم. حاول استخدام كلمات مفتاحية مثل "دفع"، "استلام"، "شراء" أو "إيجار".'
      : 'Could not identify the transaction type from the description. Try using keywords like "paid", "received", "bought", or "rent".';
  }

  // Account matching validation warnings
  if (!debitAccount && detectedIntent !== 'unknown') {
    warnings.push(
      language === 'ar'
        ? 'لم نتمكن من تحديد حساب مدين مناسب بثقة في دليل الحسابات.'
        : 'Could not confidently match a suitable debit account in your chart of accounts.'
    );
  }
  
  if (!creditAccount && detectedIntent !== 'unknown') {
    warnings.push(
      language === 'ar'
        ? 'لم نتمكن من تحديد حساب دائن مناسب بثقة في دليل الحسابات.'
        : 'Could not confidently match a suitable credit account in your chart of accounts.'
    );
  }

  // Amount extraction validation warnings
  if (amount === undefined) {
    warnings.push(
      language === 'ar'
        ? 'لم يتم العثور على مبلغ العملية في الوصف. يرجى إدخال المبلغ يدوياً.'
        : 'No transaction amount detected. Please enter the amount manually.'
    );
  }

  // Determine suggestion confidence level
  let confidence: 'high' | 'medium' | 'low' = 'low';
  if (detectedIntent !== 'unknown' && debitAccount && creditAccount) {
    confidence = amount !== undefined ? 'high' : 'medium';
  }

  return {
    debitAccountId: debitAccount?.id,
    creditAccountId: creditAccount?.id,
    amount,
    confidence,
    explanation,
    warnings,
    detectedIntent
  };
}
