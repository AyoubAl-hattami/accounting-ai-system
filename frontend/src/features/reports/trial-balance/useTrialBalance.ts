import { useState, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { TrialBalanceRead } from '../../../api/types';

interface UseTrialBalanceOptions {
  companyId: number | null;
  asOfDate: string | null;
}

export function useTrialBalance({ companyId, asOfDate }: UseTrialBalanceOptions) {
  const [data, setData] = useState<TrialBalanceRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/trial-balance?company_id=${companyId}`;
      if (asOfDate) {
        url += `&as_of_date=${asOfDate}`;
      }
      const response = await apiClient.get<TrialBalanceRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load trial balance report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, asOfDate]);

  return { data, isLoading, error, fetchReport };
}
