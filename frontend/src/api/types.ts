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
  net_income: number;
  income_accounts: TrialBalanceRow[];
  expense_accounts: TrialBalanceRow[];
}

export interface BalanceSheetReport {
  company_id: number;
  total_assets: number;
  total_liabilities: number;
  total_equity: number;
  retained_earnings: number;
  asset_accounts: TrialBalanceRow[];
  liability_accounts: TrialBalanceRow[];
  equity_accounts: TrialBalanceRow[];
}

// ── Dashboard aggregate ──
export interface DashboardData {
  trialBalance: TrialBalanceReport | null;
  profitLoss: ProfitLossReport | null;
  balanceSheet: BalanceSheetReport | null;
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
