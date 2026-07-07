import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { AccountLedgerRead } from '../../../api/types';
import { dataEvents } from '../../../lib/dataEvents';

interface UseAccountLedgerOptions {
  companyId: number | null;
  accountId: number | null;
  startDate: string | null;
  endDate: string | null;
}

export function useAccountLedger({ companyId, accountId, startDate, endDate }: UseAccountLedgerOptions) {
  const [data, setData] = useState<AccountLedgerRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId || !accountId) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/account-ledger?company_id=${companyId}&account_id=${accountId}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      const response = await apiClient.get<AccountLedgerRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load Account Ledger report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, accountId, startDate, endDate]);

  // Auto-refetch when posted journal data changes (post/review/void/reverse)
  useEffect(() => {
    const unsub = dataEvents.on('journal:mutated', fetchReport);
    return () => unsub();
  }, [fetchReport]);

  return { data, isLoading, error, fetchReport };
}
