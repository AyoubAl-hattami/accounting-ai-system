import { useState, useCallback } from 'react';
import apiClient from '../../api/client';
import type { Account, PaginatedResponse, AccountSeedResult } from '../../api/types';

interface UseAccountsOptions {
  companyId: number | null;
  skip?: number;
  limit?: number;
}

export function useAccounts({ companyId, skip = 0, limit = 500 }: UseAccountsOptions) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccounts = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<PaginatedResponse<Account>>(
        `/accounts?company_id=${companyId}&skip=${skip}&limit=${limit}`,
      );
      setAccounts(response.data.items);
      setTotal(response.data.total);
    } catch {
      setError('Failed to load accounts. Please try again.');
      setAccounts([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, skip, limit]);

  const seedDefaults = useCallback(async (): Promise<AccountSeedResult | null> => {
    if (!companyId) return null;

    try {
      const response = await apiClient.post<AccountSeedResult>(
        `/accounts/seed-defaults?company_id=${companyId}`,
      );
      return response.data;
    } catch {
      throw new Error('Failed to seed default accounts.');
    }
  }, [companyId]);

  return { accounts, total, isLoading, error, fetchAccounts, seedDefaults };
}
