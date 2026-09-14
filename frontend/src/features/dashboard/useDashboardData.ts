import { useState, useEffect, useCallback } from 'react';
import apiClient from '../../api/client';
import type { DashboardData } from '../../api/types';
import { dataEvents } from '../../lib/dataEvents';

/**
 * The five sources the dashboard draws on, in the order they are requested.
 * Exported so the page can name the ones that failed without duplicating the
 * list or depending on the request order by accident.
 */
export const DASHBOARD_SOURCES = [
  'trialBalance',
  'profitLoss',
  'balanceSheet',
  'journalEntries',
  'accounts',
] as const;

export type DashboardSource = (typeof DASHBOARD_SOURCES)[number];

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
  const [failedSources, setFailedSources] = useState<DashboardSource[]>([]);

  const fetchAll = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);
    setFailedSources([]);

    try {
      const settled = await Promise.allSettled([
        apiClient.get(`/reports/trial-balance?company_id=${companyId}`),
        apiClient.get(`/reports/profit-and-loss?company_id=${companyId}`),
        apiClient.get(`/reports/balance-sheet?company_id=${companyId}`),
        apiClient.get(`/journal-entries?company_id=${companyId}&skip=0&limit=5`),
        apiClient.get(`/accounts?company_id=${companyId}&skip=0&limit=5`),
      ]);
      const [tb, pl, bs, je, acc] = settled;

      setData({
        trialBalance: tb.status === 'fulfilled' ? tb.value.data : null,
        profitLoss: pl.status === 'fulfilled' ? pl.value.data : null,
        balanceSheet: bs.status === 'fulfilled' ? bs.value.data : null,
        journalEntries: je.status === 'fulfilled' ? je.value.data : null,
        accounts: acc.status === 'fulfilled' ? acc.value.data : null,
      });

      // Promise.allSettled never rejects, so the catch below could not report a
      // failed request; a rejected call simply became a null and an empty card.
      // Rejections are read off the settled results instead.
      //
      // A partial failure is reported through `failedSources`, NOT through
      // `error`: the page renders `error` and the dashboard as mutually
      // exclusive branches, so setting it here would take away the four cards
      // that did load. `error` means every source failed, and there is nothing
      // left to show.
      const failed = DASHBOARD_SOURCES.filter(
        (_source, index) => settled[index].status === 'rejected',
      );
      setFailedSources(failed);
      if (failed.length === DASHBOARD_SOURCES.length) {
        setError('Failed to load dashboard data. Please try again.');
      }
    } catch {
      // Reachable only if a request throws before its promise exists, or if
      // setData itself throws. Kept because those leave no settled results to
      // inspect.
      setFailedSources([...DASHBOARD_SOURCES]);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Auto-refetch when journal data changes elsewhere ──
  useEffect(() => {
    const unsub1 = dataEvents.on('journal:created', fetchAll);
    const unsub2 = dataEvents.on('journal:mutated', fetchAll);
    return () => {
      unsub1();
      unsub2();
    };
  }, [fetchAll]);

  return { data, isLoading, error, failedSources, refetch: fetchAll };
}
