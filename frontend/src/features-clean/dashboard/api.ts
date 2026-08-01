/**
 * Dashboard API module (clean pilot).
 *
 * All report/dashboard data fetches in one place.
 * Does not import from other features.
 */
import { apiClient } from '../../shared/api';
import type { PaginatedResponse } from '../../shared/api';
import type {
  TrialBalanceRead,
  ProfitAndLossRead,
  BalanceSheetRead,
} from '../../api/types';
import type { JournalEntry } from '../../entities/journal';
import type { Account } from '../../entities/account';

export interface DashboardSnapshot {
  trialBalance: TrialBalanceRead | null;
  profitLoss: ProfitAndLossRead | null;
  balanceSheet: BalanceSheetRead | null;
  recentJournalEntries: PaginatedResponse<JournalEntry> | null;
  recentAccounts: PaginatedResponse<Account> | null;
}

export async function fetchDashboardSnapshot(
  companyId: number,
): Promise<DashboardSnapshot> {
  const [tb, pl, bs, je, acc] = await Promise.allSettled([
    apiClient.get<TrialBalanceRead>(`/reports/trial-balance?company_id=${companyId}`),
    apiClient.get<ProfitAndLossRead>(`/reports/profit-and-loss?company_id=${companyId}`),
    apiClient.get<BalanceSheetRead>(`/reports/balance-sheet?company_id=${companyId}`),
    apiClient.get<PaginatedResponse<JournalEntry>>(
      `/journal-entries?company_id=${companyId}&skip=0&limit=5`,
    ),
    apiClient.get<PaginatedResponse<Account>>(
      `/accounts?company_id=${companyId}&skip=0&limit=5`,
    ),
  ]);

  return {
    trialBalance:         tb.status  === 'fulfilled' ? tb.value.data  : null,
    profitLoss:           pl.status  === 'fulfilled' ? pl.value.data  : null,
    balanceSheet:         bs.status  === 'fulfilled' ? bs.value.data  : null,
    recentJournalEntries: je.status  === 'fulfilled' ? je.value.data  : null,
    recentAccounts:       acc.status === 'fulfilled' ? acc.value.data : null,
  };
}
