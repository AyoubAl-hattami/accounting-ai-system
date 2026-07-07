import { useState, useCallback } from 'react';
import apiClient from '../../api/client';

export interface FiscalYear {
  id: number;
  company_id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: 'open' | 'closed' | 'locked';
  created_at: string;
  updated_at: string;
}

export interface FiscalPeriod {
  id: number;
  company_id: number;
  fiscal_year_id: number;
  period_no: number;
  name: string;
  start_date: string;
  end_date: string;
  status: 'open' | 'closed' | 'locked';
  created_at: string;
  updated_at: string;
}

export interface QuickSetupResult {
  today: string;
  fiscal_year_created: boolean;
  fiscal_year_opened: boolean;
  fiscal_period_created: boolean;
  fiscal_period_opened: boolean;
  fiscal_year: {
    id: number;
    name: string;
    start_date: string;
    end_date: string;
    status: string;
  };
  fiscal_period: {
    id: number;
    name: string;
    start_date: string;
    end_date: string;
    status: string;
    period_no: number;
  };
}

export function useFiscalSettings() {
  const [fiscalYears, setFiscalYears] = useState<FiscalYear[]>([]);
  const [fiscalPeriods, setFiscalPeriods] = useState<Record<number, FiscalPeriod[]>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isQuickSetupLoading, setIsQuickSetupLoading] = useState(false);
  const [quickSetupResult, setQuickSetupResult] = useState<QuickSetupResult | null>(null);

  // Expanded fiscal year IDs
  const [expandedYears, setExpandedYears] = useState<Set<number>>(new Set());

  const toggleYear = useCallback((yearId: number) => {
    setExpandedYears((prev) => {
      const next = new Set(prev);
      if (next.has(yearId)) {
        next.delete(yearId);
      } else {
        next.add(yearId);
      }
      return next;
    });
  }, []);

  const fetchFiscalYears = useCallback(async (companyId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await apiClient.get<{ items: FiscalYear[]; total: number }>(
        '/fiscal-years',
        { params: { company_id: companyId, limit: 500 } },
      );
      setFiscalYears(resp.data.items);
    } catch {
      setError('Failed to load fiscal years');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchFiscalPeriods = useCallback(async (companyId: number, fiscalYearId: number) => {
    try {
      const resp = await apiClient.get<{ items: FiscalPeriod[]; total: number }>(
        '/fiscal-periods',
        { params: { company_id: companyId, fiscal_year_id: fiscalYearId, limit: 500 } },
      );
      setFiscalPeriods((prev) => ({
        ...prev,
        [fiscalYearId]: resp.data.items,
      }));
    } catch {
      // Silently fail — the UI will just show empty
    }
  }, []);

  const createFiscalYear = useCallback(async (payload: {
    company_id: number;
    name: string;
    start_date: string;
    end_date: string;
    status: string;
  }): Promise<FiscalYear | null> => {
    try {
      const resp = await apiClient.post<FiscalYear>('/fiscal-years', payload);
      setFiscalYears((prev) => [...prev, resp.data]);
      return resp.data;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      throw new Error(axiosErr.response?.data?.detail || 'Failed to create fiscal year');
    }
  }, []);

  const createFiscalPeriod = useCallback(async (payload: {
    company_id: number;
    fiscal_year_id: number;
    period_no: number;
    name: string;
    start_date: string;
    end_date: string;
    status: string;
  }): Promise<FiscalPeriod | null> => {
    try {
      const resp = await apiClient.post<FiscalPeriod>('/fiscal-periods', payload);
      setFiscalPeriods((prev) => ({
        ...prev,
        [payload.fiscal_year_id]: [
          ...(prev[payload.fiscal_year_id] || []),
          resp.data,
        ],
      }));
      return resp.data;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      throw new Error(axiosErr.response?.data?.detail || 'Failed to create fiscal period');
    }
  }, []);

  const quickSetupToday = useCallback(async (companyId: number): Promise<QuickSetupResult | null> => {
    setIsQuickSetupLoading(true);
    setQuickSetupResult(null);
    try {
      const resp = await apiClient.post<QuickSetupResult>(
        '/fiscal/quick-setup-today',
        null,
        { params: { company_id: companyId } },
      );
      setQuickSetupResult(resp.data);
      // Refresh the list
      await fetchFiscalYears(companyId);
      return resp.data;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      throw new Error(axiosErr.response?.data?.detail || 'Failed to setup fiscal period');
    } finally {
      setIsQuickSetupLoading(false);
    }
  }, [fetchFiscalYears]);

  return {
    fiscalYears,
    fiscalPeriods,
    isLoading,
    error,
    isQuickSetupLoading,
    quickSetupResult,
    expandedYears,
    toggleYear,
    fetchFiscalYears,
    fetchFiscalPeriods,
    createFiscalYear,
    createFiscalPeriod,
    quickSetupToday,
    setQuickSetupResult,
  };
}
