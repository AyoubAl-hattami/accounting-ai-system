import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useGeminiAssistant } from '../../features/ai/useGeminiAssistant';

vi.mock('../../api/client', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import apiClient from '../../api/client';

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

const conversation = (id: number, companyId: number) => ({
  id,
  company_id: companyId,
  title: `Thread ${id}`,
  title_source: 'auto' as const,
  status: 'active' as const,
  created_at: '2026-08-01T10:00:00Z',
  updated_at: '2026-08-01T10:00:00Z',
  last_message_at: '2026-08-01T10:00:00Z',
});

const message = (id: number, role: 'user' | 'assistant', content: string) => ({
  id,
  role,
  content,
  created_at: '2026-08-01T10:00:00Z',
  metadata: null,
});

const detail = (id: number, companyId: number, contents: string[]) => ({
  ...conversation(id, companyId),
  messages_total: contents.length,
  messages: contents.map((content, index) =>
    message(id * 100 + index, index % 2 === 0 ? 'user' : 'assistant', content),
  ),
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <MemoryRouter initialEntries={['/dashboard']}>{children}</MemoryRouter>
);

/** Answers the two calls the hook makes on mount: list, then the newest thread. */
function serveCompany(companyId: number, threadDetail: ReturnType<typeof detail> | null) {
  mockGet.mockImplementation((url: string) => {
    if (url === '/ai/conversations') {
      return Promise.resolve({
        data: {
          items: threadDetail ? [conversation(threadDetail.id, companyId)] : [],
          total: threadDetail ? 1 : 0,
        },
      } as never);
    }
    if (threadDetail && url === `/ai/conversations/${threadDetail.id}`) {
      return Promise.resolve({ data: threadDetail } as never);
    }
    return Promise.reject({ response: { status: 404 } });
  });
}

describe('assistant conversation memory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  // Reopening the assistant must show the thread, not an empty box.
  it('restores the persisted thread when the panel mounts', async () => {
    serveCompany(1, detail(9, 1, ['I paid the office rent', 'How much was it?']));

    const { result } = renderHook(() => useGeminiAssistant({ companyId: 1 }), { wrapper });

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.messages.map((m) => m.content)).toEqual([
      'I paid the office rent',
      'How much was it?',
    ]);
    expect(result.current.currentConversation?.id).toBe(9);
  });

  // Memory lives on the server: the client posts one message and gets the
  // stored pair back, rather than replaying a locally held transcript.
  it('sends only the new message and keeps what the server stored', async () => {
    serveCompany(1, detail(9, 1, ['I paid the office rent', 'How much was it?']));
    mockPost.mockResolvedValueOnce({
      data: {
        conversation: conversation(9, 1),
        user_message: message(300, 'user', 'it was 300 from the bank'),
        assistant_message: message(301, 'assistant', 'Draft ready.'),
        assistant_reply: { intent: 'create_journal_draft', suggested_action: null },
      },
    } as never);

    const { result } = renderHook(() => useGeminiAssistant({ companyId: 1 }), { wrapper });
    await waitFor(() => expect(result.current.messages).toHaveLength(2));

    await act(async () => {
      await result.current.sendMessage('it was 300 from the bank');
    });

    const [url, payload] = mockPost.mock.calls[0] as [string, Record<string, unknown>];
    expect(url).toBe('/ai/conversations/9/messages');
    expect(payload.company_id).toBe(1);
    expect(payload.message).toBe('it was 300 from the bank');
    // No client-side transcript is uploaded; the server owns the memory.
    expect(payload.history).toBeUndefined();
    expect(payload.client_message_id).toEqual(expect.any(String));

    await waitFor(() => expect(result.current.messages).toHaveLength(4));
    expect(result.current.messages[result.current.messages.length - 1]?.content).toBe('Draft ready.');
  });

  // A thread belongs to one company. Switching tenants must not carry it over.
  it('drops one company’s thread when the user switches company', async () => {
    serveCompany(1, detail(9, 1, ['I paid the office rent']));

    const { result, rerender } = renderHook(
      ({ companyId }: { companyId: number }) => useGeminiAssistant({ companyId }),
      { wrapper, initialProps: { companyId: 1 } },
    );
    await waitFor(() => expect(result.current.messages).toHaveLength(1));

    serveCompany(2, null);
    rerender({ companyId: 2 });

    await waitFor(() => expect(result.current.messages).toEqual([]));
    expect(result.current.currentConversation).toBeNull();
    const companyIds = mockGet.mock.calls
      .map(([, config]) => (config as { params?: { company_id?: number } })?.params?.company_id)
      .filter((id): id is number => id !== undefined);
    expect(companyIds).toContain(1);
    expect(companyIds).toContain(2);
  });

  // Every read is scoped server-side; the client must always say which company.
  it('asks for a specific thread only within the selected company', async () => {
    serveCompany(1, detail(9, 1, ['first thread']));

    const { result } = renderHook(() => useGeminiAssistant({ companyId: 1 }), { wrapper });
    await waitFor(() => expect(result.current.messages).toHaveLength(1));

    mockGet.mockResolvedValueOnce({ data: detail(12, 1, ['second thread']) } as never);
    await act(async () => {
      await result.current.selectConversation(12);
    });

    await waitFor(() =>
      expect(result.current.messages.map((m) => m.content)).toEqual(['second thread']),
    );
    const selectCall = mockGet.mock.calls.find(([url]) => url === '/ai/conversations/12');
    expect(selectCall).toBeDefined();
    expect((selectCall?.[1] as { params?: { company_id?: number } })?.params?.company_id).toBe(1);
  });

  // If the server refuses a remembered thread, the client must forget it too.
  it('forgets a thread the server will no longer hand over', async () => {
    localStorage.setItem('gemini_selected_conversation_1', '77');
    serveCompany(1, detail(9, 1, ['still visible']));

    const { result } = renderHook(() => useGeminiAssistant({ companyId: 1 }), { wrapper });
    await waitFor(() => expect(result.current.messages).toHaveLength(1));

    mockGet.mockRejectedValueOnce({ response: { status: 404 } });
    await act(async () => {
      await result.current.selectConversation(77);
    });

    await waitFor(() => expect(result.current.messages).toEqual([]));
    expect(localStorage.getItem('gemini_selected_conversation_1')).toBeNull();
    expect(result.current.error).toBeTruthy();
  });
});
