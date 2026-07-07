import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../../api/client';
import type { ProfitAndLossRead } from '../../../api/types';
import { dataEvents } from '../../../lib/dataEvents';

interface UseProfitAndLossOptions {
  companyId: number | null;
  startDate: string | null;
  endDate: string | null;
}

export function useProfitAndLoss({ companyId, startDate, endDate }: UseProfitAndLossOptions) {
  const [data, setData] = useState<ProfitAndLossRead | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      let url = `/reports/profit-and-loss?company_id=${companyId}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      const response = await apiClient.get<ProfitAndLossRead>(url);
      setData(response.data);
    } catch {
      setError('Failed to load Profit & Loss report. Please try again.');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, startDate, endDate]);

  // Auto-refetch when posted journal data changes (post/review/void/reverse)
  useEffect(() => {
    const unsub = dataEvents.on('journal:mutated', fetchReport);
    return () => unsub();
  }, [fetchReport]);

  return { data, isLoading, error, fetchReport };
}
