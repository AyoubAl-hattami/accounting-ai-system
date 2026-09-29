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
export type AccountSubtype =
  | 'bank'
  | 'cash'
  | 'e_wallet'
  | 'receivable'
  | 'payable'
  | 'revenue'
  | 'expense'
  | 'other';

export interface Account {
  id: number;
  company_id: number;
  code: string;
  name: string;
  account_type: string;
  account_subtype: AccountSubtype | null;
  /** The unit this account is kept in; fixed once the account exists. */
  currency: string;
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
  /** The one currency every figure in this report is in. */
  currency: string | null;
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
  /** The one currency every figure in this report is in. */
  currency: string | null;
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
  /** The one currency every figure in this report is in. */
  currency: string | null;
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
  /** The one currency every figure in this report is in. */
  currency: string | null;
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
  /** Lines in the whole window; `lines` may be one page of them. */
  total_lines: number;
  line_skip: number | null;
  line_limit: number | null;
}

// ── General Ledger (all accounts) ──
export interface GeneralLedgerRead {
  /** The one currency every figure in this report is in. */
  currency: string | null;
  company_id: number;
  start_date: string | null;
  end_date: string | null;
  accounts: AccountLedgerRead[];
  /** Accounts in the company; `accounts` may be one page of them. */
  total_accounts: number;
  account_skip: number | null;
  account_limit: number | null;
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
  created_at: string | null;
  primary_admin_email: string | null;
}

export interface PlatformDashboard {
  total_clients: number;
  trial_subscriptions: number;
  active_subscriptions: number;
  past_due_subscriptions: number;
  suspended_subscriptions: number;
  cancelled_subscriptions: number;
  recent_clients: CompanySubscription[];
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

export type ChartTemplate = 'default' | 'yemen_cash_wallet';

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
  chart_template: ChartTemplate;
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

// ── Partner (Customer / Vendor) ──
export interface Partner {
  id: number;
  company_id: number;
  name: string;
  code: string;
  is_customer: boolean;
  is_vendor: boolean;
  currency: string;
  email: string | null;
  phone: string | null;
  tax_id: string | null;
  address: string | null;
  receivable_account_id: number | null;
  payable_account_id: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PartnerCreatePayload {
  company_id: number;
  name: string;
  code: string;
  is_customer: boolean;
  is_vendor: boolean;
  currency?: string | null;
  email?: string | null;
  phone?: string | null;
  tax_id?: string | null;
  address?: string | null;
  receivable_account_id?: number | null;
  payable_account_id?: number | null;
  is_active?: boolean;
}

// ── Invoice / Bill ──
export type InvoiceType = 'out_invoice' | 'in_invoice';
export type InvoiceStatus = 'draft' | 'posted' | 'paid' | 'void' | 'cancelled';

export interface InvoiceLine {
  id?: number;
  invoice_id?: number;
  line_no: number;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  subtotal: string | number;
  account_id: number;
}

export interface Invoice {
  id: number;
  company_id: number;
  partner_id: number;
  partner_name?: string | null;
  invoice_type: InvoiceType;
  invoice_no: string;
  reference: string | null;
  issue_date: string;
  due_date: string;
  currency: string;
  status: InvoiceStatus;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  paid_amount?: string;
  credited_amount?: string;
  residual_amount?: string;
  payment_status?: 'unpaid' | 'partially_paid' | 'paid';
  journal_entry_id: number | null;
  notes: string | null;
  created_at?: string;
  updated_at?: string;
  lines: InvoiceLine[];
}

export interface InvoiceLineCreatePayload {
  description: string;
  quantity: number | string;
  unit_price: number | string;
  account_id: number;
}

export interface InvoiceCreatePayload {
  company_id: number;
  partner_id: number;
  invoice_type: InvoiceType;
  invoice_no: string;
  issue_date: string;
  due_date: string;
  currency?: string | null;
  reference?: string | null;
  tax_amount?: number | string;
  notes?: string | null;
  lines: InvoiceLineCreatePayload[];
}

// ── Payments & Receipts ──
export type PaymentType = 'customer_receipt' | 'vendor_payment';
export type PaymentStatus = 'draft' | 'posted' | 'void';

export interface PaymentAllocation {
  id: number;
  company_id: number;
  payment_id: number;
  invoice_id: number;
  amount: string;
  created_at?: string;
  invoice_no?: string | null;
}

export interface PaymentAllocationPayload {
  invoice_id: number;
  amount: number;
}

export interface Payment {
  id: number;
  company_id: number;
  partner_id: number;
  payment_type: PaymentType;
  currency_code: string;
  amount: string;
  payment_date: string;
  bank_or_cash_account_id: number;
  receivable_or_payable_account_id: number;
  status: PaymentStatus;
  reference?: string | null;
  memo?: string | null;
  journal_entry_id?: number | null;
  created_by_user_id?: number | null;
  created_at?: string;
  updated_at?: string;
  partner_name?: string | null;
  bank_account_name?: string | null;
  receivable_or_payable_account_name?: string | null;
  allocations: PaymentAllocation[];
  allocated_amount: string;
  unallocated_amount: string;
}

export interface PaymentCreatePayload {
  company_id: number;
  partner_id: number;
  payment_type: PaymentType;
  currency_code: string;
  amount: number;
  payment_date: string;
  bank_or_cash_account_id: number;
  receivable_or_payable_account_id: number;
  allocations?: PaymentAllocationPayload[];
  reference?: string | null;
  memo?: string | null;
}

export interface PaymentPageResponse {
  items: Payment[];
  total: number;
  skip: number;
  limit: number;
}

// ── Aging & Statement Reports ──
export interface AgingItem {
  partner_id: number;
  partner_code: string;
  partner_name: string;
  invoice_id: number;
  invoice_no: string;
  invoice_date: string;
  due_date: string;
  original_amount: string | number;
  paid_amount: string | number;
  credited_amount?: string | number;
  outstanding_amount: string | number;
  days_overdue: number;
  bucket: string;
  currency: string;
}

export interface AgingTotals {
  total_current: string | number;
  total_1_30: string | number;
  total_31_60: string | number;
  total_61_90: string | number;
  total_91_120: string | number;
  total_120_plus: string | number;
  total_outstanding: string | number;
}

export interface AgingReportResponse {
  company_id: number;
  report_type: 'ar' | 'ap';
  as_of_date: string;
  currency: string;
  items: AgingItem[];
  totals: AgingTotals;
}

export interface StatementTransactionItem {
  date: string;
  type: 'invoice' | 'payment' | 'credit_note' | 'refund';
  document_no: string;
  reference?: string | null;
  description?: string | null;
  debit: string | number;
  credit: string | number;
  running_balance: string | number;
}

export interface PartnerStatementResponse {
  company_id: number;
  partner_id: number;
  partner_name: string;
  partner_code: string;
  partner_type: 'customer' | 'vendor' | 'both';
  currency: string;
  date_from: string;
  date_to: string;
  opening_balance: string | number;
  transactions: StatementTransactionItem[];
  closing_balance: string | number;
  total_debit: string | number;
  total_credit: string | number;
}

// ── Credit & Debit Notes ──
export type CreditNoteType = 'customer_credit_note' | 'vendor_debit_note';
export type CreditNoteStatus = 'draft' | 'posted' | 'void';

export interface CreditNoteLine {
  id: number;
  credit_note_id: number;
  line_no: number;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  subtotal: string | number;
  account_id: number;
}

export interface CreditNoteLinePayload {
  description: string;
  quantity: number;
  unit_price: number;
  account_id: number;
}

export interface CreditNoteAllocation {
  id: number;
  company_id: number;
  credit_note_id: number;
  invoice_id: number;
  amount: string;
  created_at?: string;
  invoice_no?: string | null;
}

export interface CreditNoteAllocationPayload {
  invoice_id: number;
  amount: number;
}

export interface CreditNote {
  id: number;
  company_id: number;
  partner_id: number;
  note_type: CreditNoteType;
  credit_note_no: string;
  issue_date: string;
  currency: string;
  status: CreditNoteStatus;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  allocated_amount: string;
  unallocated_amount: string;
  reference?: string | null;
  partner_name?: string | null;
  journal_entry_id?: number | null;
  reason?: string | null;
  created_by_user_id?: number | null;
  created_at?: string;
  updated_at?: string;
  lines: CreditNoteLine[];
  allocations: CreditNoteAllocation[];
}

export interface CreditNoteCreatePayload {
  company_id: number;
  partner_id: number;
  note_type: CreditNoteType;
  credit_note_no: string;
  issue_date: string;
  currency: string;
  lines: CreditNoteLinePayload[];
  reference?: string | null;
  tax_amount?: number;
  reason?: string | null;
  allocations?: CreditNoteAllocationPayload[];
}

export interface CreditNotePageResponse {
  items: CreditNote[];
  total: number;
  skip: number;
  limit: number;
}

// ── Refunds ──
export type RefundType = 'customer_refund' | 'vendor_refund';
export type RefundStatus = 'draft' | 'posted' | 'void';

export interface Refund {
  id: number;
  company_id: number;
  partner_id: number;
  refund_type: RefundType;
  currency_code: string;
  amount: string;
  refund_date: string;
  bank_or_cash_account_id: number;
  receivable_or_payable_account_id: number;
  status: RefundStatus;
  credit_note_id?: number | null;
  reference?: string | null;
  memo?: string | null;
  journal_entry_id?: number | null;
  created_by_user_id?: number | null;
  created_at?: string;
  updated_at?: string;
  partner_name?: string | null;
  bank_account_name?: string | null;
  receivable_or_payable_account_name?: string | null;
}

export interface RefundCreatePayload {
  company_id: number;
  partner_id: number;
  refund_type: RefundType;
  currency_code: string;
  amount: number;
  refund_date: string;
  bank_or_cash_account_id: number;
  receivable_or_payable_account_id: number;
  credit_note_id?: number | null;
  reference?: string | null;
  memo?: string | null;
}

export interface RefundPageResponse {
  items: Refund[];
  total: number;
  skip: number;
  limit: number;
}

