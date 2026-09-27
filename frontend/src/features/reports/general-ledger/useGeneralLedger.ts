import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { GeneralLedgerRead } from '../../../api/types';
import { dataEvents } from '../../../lib/dataEvents';

interface UseGeneralLedgerOptions {
  companyId: number | null;
  /** Null means the company's own currency. */
  currency?: string | null;
  startDate: string | null;
  endDate: string | null;
  accountSkip?: number;
}

/** Matches the endpoint's own default, so the control and the server agree. */
export const LEDGER_ACCOUNT_PAGE_SIZE = 50;

export function useGeneralLedger({
  companyId,
  currency,
  startDate,
  endDate,
  accountSkip = 0,
}: UseGeneralLedgerOptions) {
  const [data, setData] = useState<GeneralLedgerRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/general-ledger?company_id=${companyId}`;
      if (currency) url += `&currency=${encodeURIComponent(currency)}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      // Paged by account, never by line: a page that split an account would
      // show a running balance with no beginning.
      url += `&account_skip=${accountSkip}&account_limit=${LEDGER_ACCOUNT_PAGE_SIZE}`;
      const response = await apiClient.get<GeneralLedgerRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load General Ledger report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, currency, startDate, endDate, accountSkip]);

  // Auto-refetch when posted journal data changes (post/review/void/reverse)
  useEffect(() => {
    const unsub = dataEvents.on('journal:mutated', fetchReport);
    return () => unsub();
  }, [fetchReport]);

  return { data, isLoading, error, fetchReport };
}
