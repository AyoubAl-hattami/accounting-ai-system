import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useGeminiAssistant } from '../../features/ai/useGeminiAssistant';

vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import apiClient from '../../api/client';
const mockGet = vi.mocked(apiClient.get);

const wrapper = ({ children }: { children: ReactNode }) => (
  <MemoryRouter initialEntries={['/dashboard']}>{children}</MemoryRouter>
);

/** Every GET /ai/conversations (the list, not a detail) issued so far. */
function listCalls() {
  return mockGet.mock.calls.filter(([url]) => url === '/ai/conversations');
}

function emptyList() {
  mockGet.mockImplementation((url: string) => {
    if (url === '/ai/conversations') {
      return Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 20 } });
    }
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
}

describe('assistant conversation history is not fetched twice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('issues one list request per company switch', async () => {
    emptyList();
    const { result } = renderHook(() => useGeminiAssistant({ companyId: 11, language: 'en' }), { wrapper });
    await waitFor(() => expect(result.current.isRestoring).toBe(false));

    // The second effect debounces by 250 ms; give it room to fire.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });

    const calls = listCalls();
    console.log(`  GET /ai/conversations after one mount: ${calls.length}`);
    calls.forEach((call, i) => {
      console.log(`    [${i}] ${JSON.stringify((call[1] as { params: unknown }).params)}`);
    });
    expect(calls.length).toBe(1);
  });

  // The debounced effect exists for search and status changes. The guard above
  // must not cost it that job.
  it('still fetches when the search term changes', async () => {
    emptyList();
    const { result } = renderHook(
      () => useGeminiAssistant({ companyId: 13, language: 'en' }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isRestoring).toBe(false));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });
    const afterMount = listCalls().length;

    act(() => result.current.setHistorySearch('invoice'));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });

    console.log(`  after mount: ${afterMount}, after a search: ${listCalls().length}`);
    expect(listCalls().length).toBe(afterMount + 1);
    expect((listCalls().at(-1)?.[1] as { params: { search?: string } }).params.search).toBe('invoice');
  });

  it('still fetches when the restore request failed', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/ai/conversations') {
        // First call (restore) fails; later calls succeed.
        return listCalls().length <= 1
          ? Promise.reject(new Error('boom'))
          : Promise.resolve({ data: { items: [], total: 0, page: 1, page_size: 20 } });
      }
      return Promise.reject(new Error(`unexpected GET ${url}`));
    });
    const { result } = renderHook(() => useGeminiAssistant({ companyId: 12, language: 'en' }), { wrapper });
    await waitFor(() => expect(result.current.isRestoring).toBe(false));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400));
    });
    console.log(`  GET /ai/conversations when restore failed: ${listCalls().length}`);
    expect(listCalls().length).toBeGreaterThanOrEqual(2);
  });
});
