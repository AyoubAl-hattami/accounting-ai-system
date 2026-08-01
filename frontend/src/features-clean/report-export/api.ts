/**
 * Reports API module (clean pilot).
 *
 * Covers trial balance, profit & loss, balance sheet, account ledger,
 * general ledger, and CSV/PDF export downloads.
 * Does not import from other features.
 */
import { apiClient } from '../../shared/api';
import type {
  TrialBalanceRead,
  ProfitAndLossRead,
  BalanceSheetRead,
  AccountLedgerRead,
  GeneralLedgerRead,
} from '../../api/types';

// ── Report fetches ───────────────────────────────────────────────────────────

export async function fetchTrialBalance(
  companyId: number,
  asOfDate?: string | null,
): Promise<TrialBalanceRead> {
  let url = `/reports/trial-balance?company_id=${companyId}`;
  if (asOfDate) url += `&as_of_date=${asOfDate}`;
  const response = await apiClient.get<TrialBalanceRead>(url);
  return response.data;
}

export async function fetchProfitAndLoss(
  companyId: number,
  startDate?: string | null,
  endDate?: string | null,
): Promise<ProfitAndLossRead> {
  let url = `/reports/profit-and-loss?company_id=${companyId}`;
  if (startDate) url += `&start_date=${startDate}`;
  if (endDate) url += `&end_date=${endDate}`;
  const response = await apiClient.get<ProfitAndLossRead>(url);
  return response.data;
}

export async function fetchBalanceSheet(
  companyId: number,
  asOfDate?: string | null,
): Promise<BalanceSheetRead> {
  let url = `/reports/balance-sheet?company_id=${companyId}`;
  if (asOfDate) url += `&as_of_date=${asOfDate}`;
  const response = await apiClient.get<BalanceSheetRead>(url);
  return response.data;
}

export async function fetchAccountLedger(
  companyId: number,
  accountId: number,
  startDate?: string | null,
  endDate?: string | null,
): Promise<AccountLedgerRead> {
  let url = `/reports/account-ledger?company_id=${companyId}&account_id=${accountId}`;
  if (startDate) url += `&start_date=${startDate}`;
  if (endDate) url += `&end_date=${endDate}`;
  const response = await apiClient.get<AccountLedgerRead>(url);
  return response.data;
}

export async function fetchGeneralLedger(
  companyId: number,
  startDate?: string | null,
  endDate?: string | null,
): Promise<GeneralLedgerRead> {
  let url = `/reports/general-ledger?company_id=${companyId}`;
  if (startDate) url += `&start_date=${startDate}`;
  if (endDate) url += `&end_date=${endDate}`;
  const response = await apiClient.get<GeneralLedgerRead>(url);
  return response.data;
}

// ── CSV / PDF exports ────────────────────────────────────────────────────────

type ReportName =
  | 'trial-balance'
  | 'profit-and-loss'
  | 'balance-sheet'
  | 'account-ledger'
  | 'general-ledger';

type ExportFormat = 'csv' | 'pdf';

export async function downloadReport(
  reportName: ReportName,
  format: ExportFormat,
  params: Record<string, string | number | null | undefined>,
): Promise<void> {
  const filteredParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v != null),
  ) as Record<string, string | number>;

  const query = new URLSearchParams(
    Object.fromEntries(Object.entries(filteredParams).map(([k, v]) => [k, String(v)])),
  ).toString();

  const response = await apiClient.get(`/reports/${reportName}/${format}?${query}`, {
    responseType: 'blob',
  });

  const extension = format === 'csv' ? 'csv' : 'pdf';
  const filename = `${reportName}.${extension}`;
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
