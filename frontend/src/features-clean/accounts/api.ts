/**
 * Accounts API module.
 *
 * Imports transport from shared/api and types from entities/account.
 * Does not import from other features.
 */
import { apiClient } from '../../shared/api';
import type { PaginatedResponse } from '../../shared/api';
import type { Account, AccountSeedResult } from '../../entities/account';

export interface ListAccountsParams {
  companyId: number;
  skip?: number;
  limit?: number;
}

export async function listAccounts({
  companyId,
  skip = 0,
  limit = 500,
}: ListAccountsParams): Promise<PaginatedResponse<Account>> {
  const response = await apiClient.get<PaginatedResponse<Account>>(
    `/accounts?company_id=${companyId}&skip=${skip}&limit=${limit}`,
  );
  return response.data;
}

export async function seedDefaultAccounts(companyId: number): Promise<AccountSeedResult> {
  const response = await apiClient.post<AccountSeedResult>(
    `/accounts/seed-defaults?company_id=${companyId}`,
  );
  return response.data;
}

export async function createAccount(payload: {
  company_id: number;
  code: string;
  name: string;
  account_type: string;
  parent_id?: number | null;
  description?: string | null;
}): Promise<Account> {
  const response = await apiClient.post<Account>('/accounts', payload);
  return response.data;
}

export async function updateAccount(
  accountId: number,
  payload: Partial<{
    name: string;
    description: string | null;
    is_active: boolean;
    parent_id: number | null;
  }>,
): Promise<Account> {
  const response = await apiClient.patch<Account>(`/accounts/${accountId}`, payload);
  return response.data;
}
