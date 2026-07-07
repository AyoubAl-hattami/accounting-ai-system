import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { BalanceSheetRead } from '../../../api/types';
import { dataEvents } from '../../../lib/dataEvents';

interface UseBalanceSheetOptions {
  companyId: number | null;
  asOfDate: string | null;
}

export function useBalanceSheet({ companyId, asOfDate }: UseBalanceSheetOptions) {
  const [data, setData] = useState<BalanceSheetRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/balance-sheet?company_id=${companyId}`;
      if (asOfDate) url += `&as_of_date=${asOfDate}`;
      const response = await apiClient.get<BalanceSheetRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load Balance Sheet report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, asOfDate]);

  // Auto-refetch when posted journal data changes (post/review/void/reverse)
  useEffect(() => {
    const unsub = dataEvents.on('journal:mutated', fetchReport);
    return () => unsub();
  }, [fetchReport]);

  return { data, isLoading, error, fetchReport };
}
