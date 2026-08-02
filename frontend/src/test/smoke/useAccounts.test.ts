import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAccounts } from '../../entities/account';

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import apiClient from '../../api/client';

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

const mockAccounts = [
  { id: 1, code: '1000', name: 'Cash', account_type: 'asset', is_active: true, is_system: false, parent_id: null, description: null },
  { id: 2, code: '2000', name: 'Accounts Payable', account_type: 'liability', is_active: true, is_system: false, parent_id: null, description: null },
];

describe('useAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts with empty state', () => {
    const { result } = renderHook(() => useAccounts({ companyId: 1 }));
    expect(result.current.accounts).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('fetches accounts successfully', async () => {
    mockGet.mockResolvedValueOnce({ data: { items: mockAccounts, total: 2 } } as never);

    const { result } = renderHook(() => useAccounts({ companyId: 1 }));

    await act(async () => {
      await result.current.fetchAccounts();
    });

    expect(result.current.accounts).toEqual(mockAccounts);
    expect(result.current.total).toBe(2);
    expect(result.current.error).toBeNull();
  });

  it('sets error on fetch failure', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useAccounts({ companyId: 1 }));

    await act(async () => {
      await result.current.fetchAccounts();
    });

    expect(result.current.accounts).toEqual([]);
    expect(result.current.error).toBe('Failed to load accounts. Please try again.');
  });

  it('does not fetch when companyId is null', async () => {
    const { result } = renderHook(() => useAccounts({ companyId: null }));

    await act(async () => {
      await result.current.fetchAccounts();
    });

    expect(mockGet).not.toHaveBeenCalled();
  });

  it('calls seed-defaults endpoint', async () => {
    mockPost.mockResolvedValueOnce({ data: { created_count: 5, skipped_count: 2 } } as never);

    const { result } = renderHook(() => useAccounts({ companyId: 1 }));

    let seedResult: Awaited<ReturnType<typeof result.current.seedDefaults>>;
    await act(async () => {
      seedResult = await result.current.seedDefaults();
    });

    expect(mockPost).toHaveBeenCalledWith('/accounts/seed-defaults?company_id=1');
    expect(seedResult!).toEqual({ created_count: 5, skipped_count: 2 });
  });
});
