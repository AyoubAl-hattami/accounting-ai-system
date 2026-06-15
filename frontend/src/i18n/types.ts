export type Language = 'en' | 'ar';

export interface Translations {
  // ── Common ──
  common: {
    loading: string;
    error: string;
    retry: string;
    save: string;
    cancel: string;
    edit: string;
    delete: string;
    add: string;
    search: string;
    filter: string;
    noResults: string;
    close: string;
    confirm: string;
    back: string;
    next: string;
    previous: string;
    showing: string; // "Showing"
    of: string;      // "of"
    connectionError: string;
    tryAgain: string;
    somethingWentWrong: string;
    active: string;
    inactive: string;
    yes: string;
    no: string;
    status: string;
    date: string;
    description: string;
    actions: string;
    total: string;
    noCompanySelected: string;
    selectCompanyPrompt: string;
    noCompaniesYet: string;
    noCompaniesDescription: string;
    selectCompany: string;
    noCompanySelectedText: string;
    administrator: string;
    user: string;
    startDate: string;
    endDate: string;
    clear: string;
    expandAll: string;
    collapseAll: string;
    refresh: string;
    amount: string;
    code: string;
    account: string;
    type: string;
    entryNumber: string;
    openingBalance: string;
    closingBalance: string;
    opening: string;
    closing: string;
    totals: string;
    entries: string;
    source: string;
    line: string;
    allTime: string;
    from: string;
    through: string;
    noDescription: string;
    clearFilters: string;
    noActivity: string;
    withActivity: string;
    debitTotal: string;
    creditTotal: string;
    debitBalance: string;
    creditBalance: string;
    errorLabel: string;
    submissionError: string;
    validationWarnings: string;
    sourceType: string;
    sourceId: string;
    selectAccount: string;
    selectAccountPrompt: string;
    asOfDate: string;
    noAccountsMatch: string;
    clearSearch: string;
    addLine: string;
    remove: string;
    journalLines: string;
    originalEntrySummary: string;
    searchByAccountPlaceholder: string;
    searchByEntryPlaceholder: string;
  };

  // ── Login ──
  login: {
    title: string;
    subtitle: string;
    welcomeBack: string;
    signInPrompt: string;
    emailLabel: string;
    emailPlaceholder: string;
    passwordLabel: string;
    passwordPlaceholder: string;
    signIn: string;
    signingIn: string;
    networkError: string;
    invalidCredentials: string;
    footer: string;
  };

  // ── Sidebar / Navigation ──
  nav: {
    appName: string;
    appTagline: string;
    dashboard: string;
    journalEntries: string;
    accounts: string;
    auditLogs: string;
    companyUsers: string;
    trialBalance: string;
    profitAndLoss: string;
    balanceSheet: string;
    accountLedger: string;
    generalLedger: string;
    settings: string;
    signOut: string;
  };

  // ── Dashboard ──
  dashboard: {
    pageTitle: string;
    pageSubtitle: string;
    financialOverview: string;
    realtimePosition: string;
    balanced: string;
    unbalanced: string;
    profit: string;
    loss: string;
    netIncome: string;
    totalAssets: string;
    totalLiabilities: string;
    totalEquity: string;
    trialBalance: string;
    journalEntries: string;
    accounts: string;
    plBreakdown: string;
    totalIncome: string;
    totalExpenses: string;
    netResult: string;
    recentJournalEntries: string;
    noJournalEntriesYet: string;
    ok: string;
    warning: string;
  };

  // ── Accounts ──
  accountsPage: {
    pageTitle: string;
    pageSubtitle: string;
    searchPlaceholder: string;
    allTypes: string;
    seedDefaults: string;
    seeding: string;
    seedSuccess: string;
    code: string;
    name: string;
    type: string;
    parentCode: string;
    noAccountsTitle: string;
    noAccountsDescription: string;
    showingAccounts: string;
  };

  // ── Journal Entries ──
  journals: {
    pageTitle: string;
    pageSubtitle: string;
    searchPlaceholder: string;
    allStatuses: string;
    newEntry: string;
    entryNo: string;
    entryDate: string;
    debit: string;
    credit: string;
    lines: string;
    balanced: string;
    noEntriesTitle: string;
    noEntriesDescription: string;
    showingEntries: string;
    review: string;
    post: string;
    void: string;
    reverse: string;
    draft: string;
    reviewed: string;
    posted: string;
    voided: string;
    reversed: string;
    expand: string;
    collapse: string;
    account: string;
    memo: string;
    source: string;
    successCreatedDraft: string;
    successReviewed: string;
    successPosted: string;
    successVoided: string;
    successReversalDraft: string;
    assistantTitle: string;
    assistantSubtitle: string;
    assistantPlaceholder: string;
    assistantSuggest: string;
    assistantApply: string;
    assistantClear: string;
    assistantConfidence: string;
    assistantHigh: string;
    assistantMedium: string;
    assistantLow: string;
    assistantDebit: string;
    assistantCredit: string;
    assistantAmount: string;
    assistantExplanation: string;
    assistantWarnings: string;
    assistantNoSuggestion: string;
    assistantReviewDisclaimer: string;
    assistantApplied: string;
    assistantReplaceExistingLines: string;
    assistantReplaceConfirm: string;
    assistantSourceBackend: string;
    assistantSourceLocal: string;
    assistantFallbackWarning: string;
    assistantLoading: string;
    aiMode: string;
    backendRules: string;
    rulesFallback: string;
    aiStatusUnavailable: string;
    llmNotConfigured: string;
    providerStatus: string;
  };

  // ── Create Journal Entry Modal ──
  createJournal: {
    title: string;
    entryNoLabel: string;
    entryNoPlaceholder: string;
    dateLabel: string;
    descriptionLabel: string;
    descriptionPlaceholder: string;
    linesTitle: string;
    addLine: string;
    selectAccount: string;
    debit: string;
    credit: string;
    removeLine: string;
    totalDebit: string;
    totalCredit: string;
    difference: string;
    submit: string;
    submitting: string;
    validationError: string;
    successMessage: string;
    lineDescription: string;
    chooseAccountForLine: string;
    newJournalEntry: string;
    newJournalEntryDesc: string;
  };

  // ── Review Journal Entry Modal ──
  reviewJournal: {
    title: string;
    confirmMessage: string;
    reviewing: string;
    reviewBtn: string;
  };

  // ── Post Journal Entry Modal ──
  postJournal: {
    title: string;
    confirmMessage: string;
    posting: string;
    postBtn: string;
  };

  // ── Void Journal Entry Modal ──
  voidJournal: {
    title: string;
    confirmMessage: string;
    voiding: string;
    voidBtn: string;
  };

  // ── Reverse Journal Entry Modal ──
  reverseJournal: {
    title: string;
    entryNoLabel: string;
    dateLabel: string;
    descriptionLabel: string;
    reversing: string;
    reverseBtn: string;
  };

  // ── Reports ──
  reports: {
    trialBalance: {
      pageTitle: string;
      pageSubtitle: string;
      accountCode: string;
      accountName: string;
      debit: string;
      credit: string;
      totalDebits: string;
      totalCredits: string;
      balanced: string;
      unbalanced: string;
      debitBalance: string;
      creditBalance: string;
      totals: string;
    };
    profitAndLoss: {
      pageTitle: string;
      pageSubtitle: string;
      income: string;
      expenses: string;
      totalIncome: string;
      totalExpenses: string;
      netIncome: string;
      netResult: string;
      incomeMinusExpenses: string;
    };
    balanceSheet: {
      pageTitle: string;
      pageSubtitle: string;
      assets: string;
      liabilities: string;
      equity: string;
      totalAssets: string;
      totalLiabilities: string;
      totalEquity: string;
      netAssets: string;
      liabilitiesAndEquity: string;
      earnings: string;
    };
    accountLedger: {
      pageTitle: string;
      pageSubtitle: string;
      selectAccount: string;
      date: string;
      entryNo: string;
      description: string;
      debit: string;
      credit: string;
      balance: string;
      openingBalance: string;
      closingBalance: string;
      totalDebits: string;
      totalCredits: string;
      entries: string;
      line: string;
    };
    generalLedger: {
      pageTitle: string;
      pageSubtitle: string;
      accounts: string;
      totalLines: string;
      showing: string;
      searchPlaceholder: string;
      noDataTitle: string;
      noDataDescription: string;
      noMatchFilters: string;
      opening: string;
      closing: string;
      lines: string;
      date: string;
      entryNo: string;
      ln: string;
      description: string;
      debit: string;
      credit: string;
      balance: string;
      allTypes: string;
    };
  };

  // ── Audit Logs ──
  auditLogs: {
    pageTitle: string;
    pageSubtitle: string;
    searchPlaceholder: string;
    allEntityTypes: string;
    timestamp: string;
    actor: string;
    action: string;
    entityType: string;
    entityId: string;
    noLogsTitle: string;
    noLogsDescription: string;
  };

  // ── Company Users ──
  companyUsersPage: {
    pageTitle: string;
    pageSubtitle: string;
    searchPlaceholder: string;
    addUser: string;
    allRoles: string;
    allStatuses: string;
    userId: string;
    role: string;
    activeStatus: string;
    createdAt: string;
    updatedAt: string;
    noUsersTitle: string;
    noUsersDescription: string;
    editUser: string;
  };

  // ── Settings ──
  settingsPage: {
    pageTitle: string;
    pageSubtitle: string;
    companyProfile: string;
    companyProfileDesc: string;
    editSettings: string;
    saveChanges: string;
    saving: string;
    companyName: string;
    legalName: string;
    legalNamePlaceholder: string;
    registrationNo: string;
    registrationNoPlaceholder: string;
    taxId: string;
    taxIdPlaceholder: string;
    baseCurrency: string;
    baseCurrencyHelp: string;
    baseCurrencyPlaceholder: string;
    businessAddress: string;
    businessAddressPlaceholder: string;
    updateSuccess: string;
    errorUpdating: string;
    accessDenied: string;
    accessDeniedMessage: string;
    accessDeniedHelp: string;
    companyNameRequired: string;
    currencyInvalid: string;
    // Language section
    languageAppearance: string;
    languageAppearanceDesc: string;
    language: string;
    languageHelp: string;
    english: string;
    arabic: string;
  };
}
