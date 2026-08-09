import { useState, useCallback } from 'react';
import apiClient from '../../api/client';
import type {
  Account,
  AccountSubtype,
  PaginatedResponse,
  AccountSeedResult,
} from '../../api/types';

export interface CreateAccountInput {
  code: string;
  name: string;
  account_type: string;
  account_subtype: AccountSubtype | null;
  parent_id: number | null;
  description: string | null;
}

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

  const createAccount = useCallback(
    async (input: CreateAccountInput): Promise<Account> => {
      if (!companyId) throw new Error('No company selected.');

      try {
        const response = await apiClient.post<Account>('/accounts', {
          company_id: companyId,
          ...input,
        });
        return response.data;
      } catch (requestError) {
        // The backend explains code conflicts and bad parents precisely; a
        // generic message would hide the one thing the user needs to fix.
        const detail = (requestError as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail;
        throw new Error(typeof detail === 'string' ? detail : 'Failed to create account.');
      }
    },
    [companyId],
  );

  return { accounts, total, isLoading, error, fetchAccounts, seedDefaults, createAccount };
}
