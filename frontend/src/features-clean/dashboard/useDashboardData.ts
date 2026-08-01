/**
 * useDashboardData hook — clean version.
 *
 * Fetches all dashboard report slices in parallel.
 * Does not import from other features.
 */
import { useState, useEffect, useCallback } from 'react';
import type { DashboardSnapshot } from './api';
import { fetchDashboardSnapshot } from './api';

const EMPTY_SNAPSHOT: DashboardSnapshot = {
  trialBalance: null,
  profitLoss: null,
  balanceSheet: null,
  recentJournalEntries: null,
  recentAccounts: null,
};

export function useDashboardData(companyId: number | null) {
  const [data, setData] = useState<DashboardSnapshot>(EMPTY_SNAPSHOT);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const snapshot = await fetchDashboardSnapshot(companyId);
      setData(snapshot);
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
