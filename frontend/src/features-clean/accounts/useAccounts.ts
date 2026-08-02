/**
 * useAccounts hook — clean version.
 *
 * Uses entity types from entities/account and API from this feature's api.ts.
 * Does not import from other features.
 */
import { useState, useCallback } from 'react';
import type { Account, AccountSeedResult } from '../../entities/account';
import { listAccounts, seedDefaultAccounts } from './api';

interface UseAccountsOptions {
  companyId: number | null;
  skip?: number;
  limit?: number;
}

interface UseAccountsReturn {
  accounts: Account[];
  total: number;
  isLoading: boolean;
  error: string | null;
  fetchAccounts: () => Promise<void>;
  seedDefaults: () => Promise<AccountSeedResult | null>;
}

export function useAccounts({
  companyId,
  skip = 0,
  limit = 500,
}: UseAccountsOptions): UseAccountsReturn {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccounts = useCallback(async () => {
    if (!companyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await listAccounts({ companyId, skip, limit });
      setAccounts(data.items);
      setTotal(data.total);
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
      return await seedDefaultAccounts(companyId);
    } catch {
      throw new Error('Failed to seed default accounts.');
    }
  }, [companyId]);

  return { accounts, total, isLoading, error, fetchAccounts, seedDefaults };
}
