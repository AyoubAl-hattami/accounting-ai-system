// ── Paginated response ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// ── Company ──
export interface Company {
  id: number;
  name: string;
  description: string | null;
  legal_name: string | null;
  registration_no: string | null;
  tax_no: string | null;
  base_currency: string;
  address: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Account ──
export interface Account {
  id: number;
  company_id: number;
  code: string;
  name: string;
  account_type: string;
  parent_id: number | null;
  description: string | null;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// ── Journal Entry ──
export type JournalEntryStatus = 'draft' | 'reviewed' | 'posted' | 'void' | 'reversed';

export interface JournalLine {
  id: number;
  journal_entry_id: number;
  company_id: number;
  account_id: number;
  line_no: number;
  debit: string;
  credit: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface JournalEntry {
  id: number;
  company_id: number;
  fiscal_year_id: number;
  fiscal_period_id: number | null;
  entry_no: string;
  entry_date: string;
  description: string | null;
  status: JournalEntryStatus;
  source_type: string | null;
  source_id: string | null;
  created_by_user_id: number | null;
  creator_name: string | null;
  reversal_of_id: number | null;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
  lines: JournalLine[];
}

// ── Report rows ──
export interface TrialBalanceRow {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  debit_total: number;
  credit_total: number;
  balance: number;
}

export interface TrialBalanceReport {
  company_id: number;
  rows: TrialBalanceRow[];
  total_debits: number;
  total_credits: number;
  is_balanced: boolean;
}

export interface ProfitLossReport {
  company_id: number;
  total_income: number;
  total_expenses: number;
  net_profit: number;
  income_accounts: TrialBalanceRow[];
  expense_accounts: TrialBalanceRow[];
}

export interface BalanceSheetReport {
  company_id: number;
  total_assets: number;
  total_liabilities: number;
  equity_accounts_total: number;
  prior_year_earnings: number;
  retained_earnings: number;
  current_year_earnings: number;
  total_equity: number;
  asset_accounts: TrialBalanceRow[];
  liability_accounts: TrialBalanceRow[];
  equity_accounts: TrialBalanceRow[];
}

// ── Dashboard aggregate ──
export interface DashboardData {
  trialBalance: TrialBalanceRead | null;
  profitLoss: ProfitAndLossRead | null;
  balanceSheet: BalanceSheetRead | null;
  journalEntries: PaginatedResponse<JournalEntry> | null;
  accounts: PaginatedResponse<Account> | null;
}

// ── Seed result ──
export interface AccountSeedResult {
  created_count: number;
  skipped_count: number;
}

// ── Trial Balance (detailed report) ──
export interface TrialBalanceLine {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  debit_total: string;
  credit_total: string;
  debit_balance: string;
  credit_balance: string;
}

export interface TrialBalanceRead {
  company_id: number;
  as_of_date: string | null;
  total_debit: string;
  total_credit: string;
  total_debit_balance: string;
  total_credit_balance: string;
  is_balanced: boolean;
  lines: TrialBalanceLine[];
}

// ── Profit & Loss (detailed report) ──
export interface ProfitAndLossLine {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  amount: string;
}

export interface ProfitAndLossRead {
  company_id: number;
  start_date: string | null;
  end_date: string | null;
  total_income: string;
  total_expenses: string;
  net_profit: string;
  income_lines: ProfitAndLossLine[];
  expense_lines: ProfitAndLossLine[];
}

// ── Balance Sheet (detailed report) ──
export interface BalanceSheetLine {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  amount: string;
}

export interface BalanceSheetRead {
  company_id: number;
  as_of_date: string | null;
  total_assets: string;
  total_liabilities: string;
  equity_accounts_total: string;
  prior_year_earnings: string;
  retained_earnings: string;
  current_year_earnings: string;
  total_equity: string;
  total_liabilities_and_equity: string;
  is_balanced: boolean;
  asset_lines: BalanceSheetLine[];
  liability_lines: BalanceSheetLine[];
  equity_lines: BalanceSheetLine[];
}

// ── Account Ledger (detailed report) ──
export interface AccountLedgerLine {
  journal_entry_id: number;
  entry_no: string;
  entry_date: string;
  line_no: number;
  description: string | null;
  debit: string;
  credit: string;
  running_balance: string;
}

export interface AccountLedgerRead {
  company_id: number;
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  start_date: string | null;
  end_date: string | null;
  opening_balance: string;
  closing_balance: string;
  lines: AccountLedgerLine[];
}

// ── General Ledger (all accounts) ──
export interface GeneralLedgerRead {
  company_id: number;
  start_date: string | null;
  end_date: string | null;
  accounts: AccountLedgerRead[];
}

// ── Journal Entry Payloads ──
export interface JournalEntryLineCreatePayload {
  account_id: number;
  debit: number;
  credit: number;
  description: string;
}

export interface JournalEntryCreatePayload {
  company_id: number;
  entry_no: string;
  entry_date: string;
  description: string;
  source_type: string;
  source_id: string;
  lines: JournalEntryLineCreatePayload[];
}

// ── Audit Log ──
export interface AuditLog {
  id: number;
  company_id: number | null;
  actor: string;
  actor_user_id: number | null;
  actor_email: string | null;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  description: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

// ── Company User ──
export type CompanyUserRole = 'admin' | 'accountant' | 'reviewer' | 'approver' | 'auditor' | 'viewer';

export interface CompanyUser {
  id: number;
  company_id: number;
  user_id: number;
  role: CompanyUserRole;
  is_active: boolean;
  user_email?: string;
  user_full_name?: string;
  user_is_active?: boolean;
  is_invitation?: boolean;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CompanyUserInvitationResponse {
  status: string;
  message: string;
  invite_url: string | null;
  token: string | null;
}

export interface CompanyUserInvitationValidateResponse {
  valid: boolean;
  email: string;
  role: CompanyUserRole;
  company_name: string;
  user_exists: boolean;
}

export interface CompanyUserInvitationRead {
  id: number;
  company_id: number;
  email: string;
  role: CompanyUserRole;
  invited_by_user_id: number;
  expires_at: string;
  accepted_at: string | null;
  accepted_by_user_id: number | null;
  created_at: string;
}

// ── Subscriptions ──

export type SubscriptionStatus =
  | 'trial'
  | 'active'
  | 'past_due'
  | 'suspended'
  | 'cancelled';

export interface Subscription {
  id: number | null;
  company_id: number;
  status: SubscriptionStatus;
  plan_code: string | null;
  expires_at: string | null;
  trial_ends_at: string | null;
  suspended_at: string | null;
  cancelled_at: string | null;
  suspension_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** Platform-owner view of one tenant and its subscription. */
export interface CompanySubscription {
  company_id: number;
  company_name: string;
  base_currency: string;
  company_is_active: boolean;
  subscription: Subscription;
  effective_status: SubscriptionStatus;
  days_remaining: number | null;
  member_count: number;
}

/** Company-facing projection: enough to explain a lockout, nothing more. */
export interface CompanySubscriptionStatus {
  company_id: number;
  effective_status: SubscriptionStatus;
  expires_at: string | null;
  days_remaining: number | null;
  is_active: boolean;
}

// ── Client onboarding (platform owner only) ──

/** Statuses a brand-new tenant may be created with. */
export type OnboardingSubscriptionStatus = Extract<SubscriptionStatus, 'trial' | 'active'>;

export interface ClientOnboardingRequest {
  company_name: string;
  base_currency: string;
  admin_email: string;
  admin_full_name: string | null;
  temporary_password?: string;
  generate_password: boolean;
  plan_code: string | null;
  subscription_status: OnboardingSubscriptionStatus;
  subscription_expires_at: string | null;
  trial_ends_at?: string | null;
  seed_default_accounts: boolean;
  create_fiscal_year: boolean;
  open_monthly_periods: boolean;
  reuse_existing_user?: boolean;
  onboarding_note?: string | null;
}

/**
 * `generated_password` is returned exactly once, by the request that created
 * the account. It is never stored and cannot be read back, so it must not be
 * persisted anywhere on the client either.
 */
export interface ClientOnboardingResult {
  company_id: number;
  company_name: string;
  base_currency: string;
  admin_user_id: number;
  admin_email: string;
  admin_was_existing: boolean;
  subscription_status: SubscriptionStatus;
  effective_status: SubscriptionStatus;
  plan_code: string | null;
  expires_at: string | null;
  trial_ends_at: string | null;
  days_remaining: number | null;
  seeded_accounts_count: number;
  fiscal_year_created: boolean;
  fiscal_periods_created: number;
  generated_password: string | null;
  /** True when the new admin is locked to the password change on first login. */
  must_change_password: boolean;
  /** APP_PUBLIC_URL, or the server's placeholder when it is unconfigured. */
  public_login_url: string;
  handover_message: string;
}

export interface OnboardingDefaults {
  default_currency: string;
  suggested_currencies: string[];
  default_plan_code: string;
  suggested_plan_codes: string[];
  default_subscription_status: OnboardingSubscriptionStatus;
  expiry_presets: string[];
  public_login_url: string;
  generated_password_length: number;
}
