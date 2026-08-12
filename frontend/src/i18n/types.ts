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
    pagination: string;
    by: string;
    notAvailable: string;
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
    exportCsv: string;
    exporting: string;
    exportFailed: string;
    exportSucceeded: string;
    downloadReport: string;
    exportPdf: string;
    exportingPdf: string;
    pdfExportFailed: string;
    pdfExportSucceeded: string;
  };

  // ── Theme ──
  theme: {
    appearance: string;
    appearanceDescription: string;
    light: string;
    dark: string;
    system: string;
    switchToLight: string;
    switchToDark: string;
  };

  // ── Charts ──
  charts: {
    revenueVsExpenses: string;
    financialComposition: string;
    topAccountBalances: string;
    runningBalance: string;
    noChartData: string;
    revenue: string;
    expenses: string;
    netIncome: string;
    assets: string;
    liabilities: string;
    equity: string;
    currentYearEarnings: string;
    debit: string;
    credit: string;
    balance: string;
    date: string;
  };

  // ── Permissions ──
  permissions: {
    accessDenied: string;
    noPermissionForPage: string;
    readOnlyMode: string;
    backToDashboard: string;
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
    showPassword: string;
    hidePassword: string;
  };

  // ── Forced temporary password change ──
  changePassword: {
    title: string;
    description: string;
    currentPasswordLabel: string;
    currentPasswordPlaceholder: string;
    newPasswordLabel: string;
    newPasswordPlaceholder: string;
    confirmPasswordLabel: string;
    confirmPasswordPlaceholder: string;
    requirements: string;
    submit: string;
    submitting: string;
    signOut: string;
    mismatch: string;
    sameAsCurrent: string;
    tooWeak: string;
    currentIncorrect: string;
    genericError: string;
    networkError: string;
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
    groupOverview: string;
    groupBookkeeping: string;
    groupReports: string;
    groupAdministration: string;
    groupPlatform: string;
    platformDashboard: string;
    platformSubscriptions: string;
    platformOnboarding: string;
    collapseSidebar: string;
    expandSidebar: string;
    openMenu: string;
    closeMenu: string;
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
    origin: string;
    systemAccount: string;
    manualAccount: string;
    parent: string;
    created: string;
    skipped: string;
    seedFailed: string;
    noMatchTitle: string;
    noMatchDescription: string;
    // Create-account dialog.  The company owns its chart, so every field is
    // free text and the helper copy only ever offers examples.
    addAccount: string;
    addAccountTitle: string;
    addAccountDescription: string;
    codeHelp: string;
    codePlaceholder: string;
    namePlaceholder: string;
    typeHelp: string;
    subtype: string;
    subtypeHelp: string;
    subtypeNone: string;
    subtypeBank: string;
    subtypeCash: string;
    subtypeEWallet: string;
    subtypeReceivable: string;
    subtypePayable: string;
    subtypeRevenue: string;
    subtypeExpense: string;
    subtypeOther: string;
    parentAccount: string;
    parentNone: string;
    quickTemplates: string;
    quickTemplatesHelp: string;
    templateBank: string;
    templateCashBox: string;
    templateEWallet: string;
    createAccount: string;
    creating: string;
    accountCreated: string;
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
    noMatchTitle: string;
    noMatchDescription: string;
    noLines: string;
    showingEntries: string;
    sourceManual: string;
    sourceAssistant: string;
    sourceReversal: string;
    sourceOpeningBalance: string;
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
    openaiActive: string;
    openaiRulesFallback: string;
    geminiActive: string;
    geminiRulesFallback: string;
    assistantBackendFallbackWarning: string;
    providerLabel: string;
    fallbackLabel: string;
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
    lineDescriptionPlaceholder: string;
    chooseAccountForLine: string;
    newJournalEntry: string;
    newJournalEntryDesc: string;
    searchAccountsPlaceholder: string;
    noAccountsMatched: string;
    accountsAvailable: string;
    /** Reminder shown above the lines table. */
    lineRule: string;
    balanced: string;
    unbalanced: string;
    errMinLines: string;
    errAccountRequired: string;
    errBothSides: string;
    errNoSide: string;
    errDebitPositive: string;
    /** Followed by the formatted difference amount. */
    errUnbalanced: string;
  };

  // ── Review Journal Entry Modal ──
  reviewJournal: {
    title: string;
    confirmMessage: string;
    /** What the entry becomes once the action succeeds. */
    consequence: string;
    reviewing: string;
    reviewBtn: string;
  };

  // ── Post Journal Entry Modal ──
  postJournal: {
    title: string;
    confirmMessage: string;
    consequence: string;
    posting: string;
    postBtn: string;
  };

  // ── Void Journal Entry Modal ──
  voidJournal: {
    title: string;
    confirmMessage: string;
    consequence: string;
    voiding: string;
    voidBtn: string;
  };

  // ── Reverse Journal Entry Modal ──
  reverseJournal: {
    title: string;
    confirmMessage: string;
    consequence: string;
    entryNoLabel: string;
    entryNoPlaceholder: string;
    dateLabel: string;
    descriptionLabel: string;
    descriptionPlaceholder: string;
    reversing: string;
    reverseBtn: string;
  };

  // ── Reports ──
  reports: {
    /** Labels reused by every report toolbar and detail table. */
    shared: {
      filters: string;
      accountsShown: string;
      linesShown: string;
      noMatchTitle: string;
      noMatchDescription: string;
      noEntryMatchTitle: string;
      noEntryMatchDescription: string;
      noDataTitle: string;
      noDataDescription: string;
    };
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
      /** Debit total less credit total — only shown when the report is out of balance. */
      difference: string;
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
      equityAccountsTotal: string;
      retainedEarnings: string;
      currentYearEarnings: string;
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
    entity: string;
    entityType: string;
    entityId: string;
    noLogsTitle: string;
    noLogsDescription: string;
    /** Plural noun used by the pagination summary. */
    logEntries: string;
    showDetails: string;
    hideDetails: string;
    accessDeniedDescription: string;
    accessDeniedHint: string;
    // Details panel
    auditDetails: string;
    before: string;
    after: string;
    field: string;
    value: string;
    previousValue: string;
    changedFields: string;
    noDetails: string;
    changed: string;
    // Filters
    filterByAction: string;
    filterByEntity: string;
    clearFilters: string;
    // Action labels
    loginSuccess: string;
    loginFailure: string;
    createJournalEntry: string;
    reviewJournalEntry: string;
    postJournalEntry: string;
    voidJournalEntry: string;
    reverseJournalEntry: string;
    updateCompanyUser: string;
    removeCompanyAccess: string;
    restoreCompanyAccess: string;
    deactivateUserAccount: string;
    reactivateUserAccount: string;
    createInvitation: string;
    cancelInvitation: string;
    acceptInvitation: string;
    updateAccount: string;
    updateFiscalYear: string;
    updateFiscalPeriod: string;
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
    inviteUser: string;
    inviteEmail: string;
    inviteRole: string;
    sendInvite: string;
    copyInviteLink: string;
    inviteCreated: string;
    pendingInvitations: string;
    acceptInvite: string;
    invitationExpired: string;
    invalidInvitation: string;
    setPassword: string;
    confirmPassword: string;
    invitationAccepted: string;
    goToLogin: string;
    passwordMismatch: string;
    passwordTooShort: string;
    removeAccess: string;
    removeAccessConfirm: string;
    accessRemoved: string;
    deleteAccount: string;
    deleteAccountConfirm: string;
    accountDeleted: string;
    deactivateAccount: string;
    deactivatedUser: string;
    deletedUser: string;
    typeDeleteToConfirm: string;
    cannotRemoveLastAdmin: string;
    cannotDeleteLastAdmin: string;
    dangerZone: string;
    activeUsers: string;
    inactiveUsers: string;
    deactivatedUsers: string;
    allUsers: string;
    cancelInvite: string;
    deleteInvite: string;
    inviteCancelled: string;
    restoreAccess: string;
    accessRestored: string;
    reactivateAccount: string;
    accountReactivated: string;
    cannotRestoreDeactivatedAccount: string;
    showingActiveUsersOnly: string;
    filterUsers: string;
    confirmCancelInvite: string;
    confirmRestoreAccess: string;
    confirmReactivateAccount: string;
    emailRequired: string;
    emailPlaceholder: string;
    sendingInvite: string;
    inviteShareHint: string;
    inviteLink: string;
    copy: string;
    copied: string;
    done: string;
    editUserDesc: string;
    activeStatusHint: string;
    onlyAdminWarning: string;
    saveChanges: string;
    savingChanges: string;
    pendingStatus: string;
    userAdded: string;
    userUpdated: string;
    inviteLinkOnceOnly: string;
    mustTypeDelete: string;
    accessDeniedDescription: string;
    accessDeniedHint: string;
    usersEntity: string;
    memberFilters: string;
    memberGroups: string;
    invitedDescription: string;
    companyLabel: string;
    fullName: string;
    accountExists: string;
    logInToAccept: string;
    readyToAccept: string;
    joinedSuccessfully: string;
    accepting: string;
    acceptFailed: string;
    validatingInvite: string;
    /** Display names for the company roles, keyed by the backend enum value. */
    roles: {
      admin: string;
      accountant: string;
      reviewer: string;
      approver: string;
      auditor: string;
      viewer: string;
    };
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
    // Fiscal management section
    fiscalYearsAndPeriods: string;
    fiscalYearsDesc: string;
    fiscalYearName: string;
    createFiscalYear: string;
    createFiscalPeriod: string;
    createFiscalPeriodForToday: string;
    startDate: string;
    endDate: string;
    periodName: string;
    periodNo: string;
    noFiscalYears: string;
    noFiscalYearsHelp: string;
    noFiscalPeriods: string;
    fiscalSetupComplete: string;
    periodCreatedForToday: string;
  };
  // ── Gemini Assistant ──
  geminiAssistant: {
    askAI: string;
    assistant: string;
    typeYourQuestion: string;
    send: string;
    thinking: string;
    suggestedAction: string;
    confirmAction: string;
    cancelAction: string;
    createDraftJournalEntry: string;
    draftCreated: string;
    aiAccessDenied: string;
    aiCouldNotAnswer: string;
    aiNeedsMoreInfo: string;
    currentPageContext: string;
    poweredByAI: string;
    confirmCreateEntry: string;
    aiActionPreview: string;
    noCompanyForAI: string;
    clearChat: string;
    debit: string;
    credit: string;
    entryDate: string;
    confirmWarning: string;
    // Fiscal period error keys
    fiscalPeriodNotFound: string;
    fiscalPeriodClosed: string;
    fiscalYearNotFound: string;
    fiscalYearClosed: string;
    cannotCreateEntryForDate: string;
    chooseOpenFiscalDate: string;
    confirmFailed: string;
    tryDifferentDate: string;
    suggestedDate: string;
    // Date editing
    useSuggestedDate: string;
    editEntryDate: string;
    confirmDisabledFiscal: string;
    // Preview / draft clarity
    previewNotCreated: string;
    draftDoesNotAffectReports: string;
    postedEntriesOnly: string;
    // Today-only date enforcement
    dateMustBeToday: string;
    todayOnlyForGeminiEntries: string;
    todayNotInOpenFiscalPeriod: string;
    createFiscalPeriodForToday: string;
    entryDateTodayOnly: string;
  };

  // ── Platform Subscriptions (platform owner only) ──
  platformSubscriptions: {
    pageTitle: string;
    pageSubtitle: string;
    searchPlaceholder: string;
    statusFilterLabel: string;
    allStatuses: string;
    columnCompany: string;
    columnCurrency: string;
    columnStatus: string;
    columnEffectiveStatus: string;
    columnExpires: string;
    columnDaysRemaining: string;
    columnPlan: string;
    columnMembers: string;
    columnActions: string;
    noExpiry: string;
    noPlan: string;
    expiredAgo: string;
    daysLeft: string;
    emptyTitle: string;
    emptyDescription: string;
    loadFailed: string;
    accessDeniedTitle: string;
    accessDeniedDescription: string;
    actionActivate: string;
    actionSuspend: string;
    actionCancel: string;
    actionExtendMonth: string;
    actionExtendYear: string;
    actionEdit: string;
    activateTitle: string;
    activateDescription: string;
    suspendTitle: string;
    suspendDescription: string;
    cancelTitle: string;
    cancelDescription: string;
    reasonLabel: string;
    reasonPlaceholder: string;
    editTitle: string;
    editDescription: string;
    expiresAtLabel: string;
    expiresAtHelp: string;
    planCodeLabel: string;
    planCodePlaceholder: string;
    statusLabel: string;
    saveChanges: string;
    activatedToast: string;
    suspendedToast: string;
    cancelledToast: string;
    extendedToast: string;
    updatedToast: string;
    actionFailed: string;
  };

  platformDashboard: {
    pageTitle: string;
    pageSubtitle: string;
    totalClients: string;
    trialSubscriptions: string;
    activeSubscriptions: string;
    blockedSubscriptions: string;
    recentClients: string;
    statusDistribution: string;
    manageSubscriptions: string;
    noClients: string;
    noAdminEmail: string;
    unknownDate: string;
    loadFailed: string;
  };

  platformAccessNotice: {
    title: string;
    message: string;
  };

  // ── Subscription statuses ──
  subscriptionStatus: {
    trial: string;
    active: string;
    past_due: string;
    suspended: string;
    cancelled: string;
  };

  // ── Locked-out tenant screen ──
  subscriptionInactive: {
    title: string;
    message: string;
    currentStatus: string;
    expiredOn: string;
  };

  // ── Client onboarding wizard (platform owner only) ──
  clientOnboarding: {
    pageTitle: string;
    pageSubtitle: string;
    accessDeniedTitle: string;
    accessDeniedDescription: string;

    // Stepper
    stepCompany: string;
    stepAdmin: string;
    stepSubscription: string;
    stepAccounting: string;
    stepReview: string;
    stepProgress: string; // "Step {current} of {total}"

    // Step 1 — client company
    companyStepTitle: string;
    companyStepDescription: string;
    companyNameLabel: string;
    companyNamePlaceholder: string;
    baseCurrencyLabel: string;
    baseCurrencyHelp: string;

    // Step 2 — client admin
    adminStepTitle: string;
    adminStepDescription: string;
    adminEmailLabel: string;
    adminEmailPlaceholder: string;
    adminFullNameLabel: string;
    adminFullNamePlaceholder: string;
    passwordModeLabel: string;
    passwordModeGenerate: string;
    passwordModeManual: string;
    passwordModeReuse: string;
    generatePasswordHelp: string;
    temporaryPasswordLabel: string;
    temporaryPasswordPlaceholder: string;
    passwordPolicyHelp: string;
    changePasswordWarning: string;
    reuseExistingUserHelp: string;

    // Step 3 — subscription
    subscriptionStepTitle: string;
    subscriptionStepDescription: string;
    planCodeLabel: string;
    planCodePlaceholder: string;
    statusLabel: string;
    expiresAtLabel: string;
    expiresAtHelp: string;
    trialEndsAtLabel: string;
    trialEndsAtHelp: string;
    presetMonth: string;
    presetQuarter: string;
    presetYear: string;
    daysRemainingLabel: string;
    daysRemainingValue: string; // "{days} days remaining"
    expiryInPastWarning: string;

    // Step 4 — initial accounting setup
    accountingStepTitle: string;
    accountingStepDescription: string;
    // Chart setup choice. Regional templates are opt-in and never the default.
    chartSetupLabel: string;
    chartSetupHelp: string;
    chartSetupDefault: string;
    chartSetupDefaultHelp: string;
    chartSetupBlank: string;
    chartSetupBlankHelp: string;
    chartSetupYemen: string;
    chartSetupYemenHelp: string;
    createFiscalYearLabel: string;
    createFiscalYearHelp: string;
    openPeriodsLabel: string;
    openPeriodsHelp: string;
    openPeriodsRequiresFiscalYear: string;
    onboardingNoteLabel: string;
    onboardingNotePlaceholder: string;

    // Step 5 — review
    reviewStepTitle: string;
    reviewStepDescription: string;
    reviewCompanySection: string;
    reviewAdminSection: string;
    reviewSubscriptionSection: string;
    reviewAccountingSection: string;
    reviewPasswordGenerated: string;
    reviewPasswordManual: string;
    reviewPasswordReuse: string;
    reviewNoPlan: string;
    reviewNoExpiry: string;
    reviewNotProvided: string;
    createClient: string;
    creating: string;

    // Success screen
    successTitle: string;
    successDescription: string;
    summaryCompanyId: string;
    summaryAdminUserId: string;
    summarySeededAccounts: string;
    summaryFiscalYear: string;
    summaryFiscalPeriods: string;
    summaryExpiry: string;
    summaryEffectiveStatus: string;
    fiscalYearCreated: string;
    fiscalYearExisting: string;
    passwordShownOnceWarning: string;
    onboardAnother: string;
    goToSubscriptions: string;

    // Handover message (73-F)
    handoverTitle: string;
    handoverHelp: string;
    copyMessage: string;
    copiedToast: string;
    copyFailed: string;
    handoverGreeting: string;
    handoverIntro: string;
    handoverLoginUrl: string;
    handoverUrlNotConfigured: string;
    handoverCompany: string;
    handoverAdminEmail: string;
    handoverTemporaryPassword: string;
    handoverValidUntil: string;
    handoverNoExpiry: string;
    handoverInstructions: string;
    handoverInstructionsExistingPassword: string;

    // Validation and errors
    validationCompanyNameRequired: string;
    validationCurrencyRequired: string;
    validationEmailRequired: string;
    validationEmailInvalid: string;
    validationPasswordRequired: string;
    validationPasswordTooWeak: string;
    validationExpiryRequired: string;
    errorCompanyExists: string;
    errorAdminEmailExists: string;
    errorReusedPlatformAdmin: string;
    errorReusedInactive: string;
    errorInvalidWindow: string;
    errorAccessDenied: string;
    errorGeneric: string;
    createdToast: string;
  };
}
