import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import type { DashboardData } from '../api/types';

export function useDashboardData(companyId: number | null) {
  const [data, setData] = useState<DashboardData>({
    trialBalance: null,
    profitLoss: null,
    balanceSheet: null,
    journalEntries: null,
    accounts: null,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const [tb, pl, bs, je, acc] = await Promise.allSettled([
        apiClient.get(`/reports/trial-balance?company_id=${companyId}`),
        apiClient.get(`/reports/profit-and-loss?company_id=${companyId}`),
        apiClient.get(`/reports/balance-sheet?company_id=${companyId}`),
        apiClient.get(`/journal-entries?company_id=${companyId}&skip=0&limit=5`),
        apiClient.get(`/accounts?company_id=${companyId}&skip=0&limit=5`),
      ]);

      setData({
        trialBalance: tb.status === 'fulfilled' ? tb.value.data : null,
        profitLoss: pl.status === 'fulfilled' ? pl.value.data : null,
        balanceSheet: bs.status === 'fulfilled' ? bs.value.data : null,
        journalEntries: je.status === 'fulfilled' ? je.value.data : null,
        accounts: acc.status === 'fulfilled' ? acc.value.data : null,
      });
    } catch {
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { data, isLoading, error, refetch: fetchAll };
}
