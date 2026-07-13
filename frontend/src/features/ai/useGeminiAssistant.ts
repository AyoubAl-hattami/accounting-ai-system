import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import apiClient from '../../api/client';
import { dataEvents } from '../../lib/dataEvents';
import type { ClarificationOption, PendingTransaction } from './pendingContext';

export interface GeminiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp: Date;
}

export interface AssistantConversation {
  id: number;
  company_id: number;
  title: string;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
  last_message_at: string;
  last_message_preview: string | null;
}

export interface SuggestedJournalLine {
  account_id: number;
  account_name: string;
  account_code: string;
  debit: number;
  credit: number;
  description?: string | null;
}

export interface SuggestedJournalPayload {
  entry_date: string;
  description: string;
  lines: SuggestedJournalLine[];
  amount?: number | null;
  warnings: string[];
  fiscal_period_valid?: boolean;
  open_period_suggestion?: string | null;
}

export interface SuggestedAction {
  type: 'create_journal_entry_draft';
  requires_confirmation: true;
  payload: SuggestedJournalPayload;
}

export interface GeminiAssistantReply {
  reply: string;
  intent: string;
  confidence: 'high' | 'medium' | 'low';
  data_sources: string[];
  suggested_action?: SuggestedAction | null;
  pending_transaction?: PendingTransaction | null;
  clarification_options?: ClarificationOption[];
  pending_context_token?: string | null;
}

export interface ConfirmActionReply {
  success: boolean;
  message: string;
  error_code?: string | null;
  open_period_suggestion?: string | null;
  entity_id?: number | null;
  entity_type?: string | null;
  data?: Record<string, unknown> | null;
}

interface PersistedMessage {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system_event';
  content: string;
  language: 'en' | 'ar';
  message_type: string;
  metadata: {
    intent?: string;
    suggested_action?: SuggestedAction | null;
  } | null;
  created_at: string;
}

interface ConversationDetail extends AssistantConversation {
  messages: PersistedMessage[];
  messages_total: number;
}

interface ConversationList {
  items: AssistantConversation[];
  total: number;
}

interface MessageExchange {
  user_message: PersistedMessage;
  assistant_message: PersistedMessage;
  assistant_reply: GeminiAssistantReply;
  idempotent_replay: boolean;
}

interface FailedSend {
  text: string;
  clientMessageId: string;
}

function routeToPage(pathname: string): string {
  const map: Record<string, string> = {
    '/dashboard': 'dashboard',
    '/journal-entries': 'journal_entries',
    '/accounts': 'accounts',
    '/audit-logs': 'audit_logs',
    '/company-users': 'company_users',
    '/reports/trial-balance': 'trial_balance',
    '/reports/profit-and-loss': 'profit_loss',
    '/reports/balance-sheet': 'balance_sheet',
    '/reports/account-ledger': 'account_ledger',
    '/reports/general-ledger': 'general_ledger',
    '/settings': 'settings',
  };
  return map[pathname] ?? 'unknown';
}

function toUiMessage(message: PersistedMessage): GeminiMessage {
  return {
    id: String(message.id),
    role: message.role === 'user' ? 'user' : 'assistant',
    content: message.content,
    intent: message.metadata?.intent,
    timestamp: new Date(message.created_at),
  };
}

function clientMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `message-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export interface UseGeminiAssistantOptions {
  companyId: number | null;
  language?: 'en' | 'ar';
}

export function useGeminiAssistant({ companyId, language = 'en' }: UseGeminiAssistantOptions) {
  const location = useLocation();
  const currentPage = routeToPage(location.pathname);
  const [messages, setMessages] = useState<GeminiMessage[]>([]);
  const [conversations, setConversations] = useState<AssistantConversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestedAction, setSuggestedAction] = useState<SuggestedAction | null>(null);
  const [failedSend, setFailedSend] = useState<FailedSend | null>(null);
  const companyRequestRef = useRef(0);

  const applyConversationDetail = useCallback((detail: ConversationDetail) => {
    setCurrentConversationId(detail.id);
    setMessages(detail.messages.map(toUiMessage));
    const lastMessage = detail.messages[detail.messages.length - 1];
    setSuggestedAction(lastMessage?.metadata?.suggested_action ?? null);
    setFailedSend(null);
    setError(null);
  }, []);

  const loadConversation = useCallback(
    async (conversationId: number) => {
      if (!companyId) return;
      setIsRestoring(true);
      try {
        const { data } = await apiClient.get<ConversationDetail>(
          `/ai/conversations/${conversationId}`,
          { params: { company_id: companyId, messages_limit: 200 } },
        );
        applyConversationDetail(data);
      } finally {
        setIsRestoring(false);
      }
    },
    [applyConversationDetail, companyId],
  );

  const refreshConversations = useCallback(async () => {
    if (!companyId) return [];
    const { data } = await apiClient.get<ConversationList>('/ai/conversations', {
      params: { company_id: companyId, limit: 100 },
    });
    setConversations(data.items);
    return data.items;
  }, [companyId]);

  useEffect(() => {
    const requestId = ++companyRequestRef.current;
    setMessages([]);
    setConversations([]);
    setCurrentConversationId(null);
    setSuggestedAction(null);
    setFailedSend(null);
    setError(null);
    if (!companyId) return;

    setIsRestoring(true);
    void apiClient
      .get<ConversationList>('/ai/conversations', {
        params: { company_id: companyId, limit: 100 },
      })
      .then(async ({ data }) => {
        if (requestId !== companyRequestRef.current) return;
        setConversations(data.items);
        const latest = data.items.find((item) => item.status === 'active') ?? data.items[0];
        if (!latest) return;
        const detail = await apiClient.get<ConversationDetail>(
          `/ai/conversations/${latest.id}`,
          { params: { company_id: companyId, messages_limit: 200 } },
        );
        if (requestId === companyRequestRef.current) {
          applyConversationDetail(detail.data);
        }
      })
      .catch(() => {
        if (requestId === companyRequestRef.current) {
          setError(
            language === 'ar'
              ? 'تعذر استعادة سجل المحادثات.'
              : 'Conversation history could not be restored.',
          );
        }
      })
      .finally(() => {
        if (requestId === companyRequestRef.current) setIsRestoring(false);
      });
  }, [applyConversationDetail, companyId, language]);

  const createNewConversation = useCallback(async () => {
    if (!companyId) return null;
    const { data } = await apiClient.post<AssistantConversation>('/ai/conversations', {
      company_id: companyId,
      language,
    });
    setConversations((previous) => [data, ...previous]);
    setCurrentConversationId(data.id);
    setMessages([]);
    setSuggestedAction(null);
    setFailedSend(null);
    setError(null);
    return data;
  }, [companyId, language]);

  const sendMessage = useCallback(
    async (text: string, retryClientMessageId?: string) => {
      const trimmed = text.trim();
      if (!companyId || !trimmed || isLoading) return;

      setIsLoading(true);
      setError(null);
      setSuggestedAction(null);
      const outgoingId = retryClientMessageId ?? clientMessageId();
      const optimisticId = `pending-${outgoingId}`;
      setMessages((previous) => [
        ...previous.filter((message) => message.id !== optimisticId),
        {
          id: optimisticId,
          role: 'user',
          content: trimmed,
          timestamp: new Date(),
        },
      ]);

      try {
        let conversationId = currentConversationId;
        const currentConversation = conversations.find(
          (conversation) => conversation.id === conversationId,
        );
        if (!conversationId || currentConversation?.status === 'archived') {
          const conversation = await createNewConversation();
          conversationId = conversation?.id ?? null;
        }
        if (!conversationId) throw new Error('conversation_unavailable');

        const { data } = await apiClient.post<MessageExchange>(
          `/ai/conversations/${conversationId}/messages`,
          {
            company_id: companyId,
            message: trimmed,
            language,
            client_message_id: outgoingId,
            page_context: {
              route: location.pathname,
              page: currentPage,
              filters: {},
            },
          },
        );
        const persisted = [toUiMessage(data.user_message), toUiMessage(data.assistant_message)];
        setMessages((previous) => [
          ...previous.filter(
            (message) =>
              message.id !== optimisticId &&
              message.id !== String(data.user_message.id) &&
              message.id !== String(data.assistant_message.id),
          ),
          ...persisted,
        ]);
        setSuggestedAction(data.assistant_reply.suggested_action ?? null);
        setFailedSend(null);
        await refreshConversations();
      } catch (requestError: unknown) {
        const detail = (requestError as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail;
        setError(
          detail ||
            (language === 'ar'
              ? 'تعذر إرسال الرسالة. يمكنك المحاولة مرة أخرى بأمان.'
              : 'The message could not be sent. You can retry safely.'),
        );
        setFailedSend({ text: trimmed, clientMessageId: outgoingId });
      } finally {
        setIsLoading(false);
      }
    },
    [
      companyId,
      conversations,
      createNewConversation,
      currentConversationId,
      currentPage,
      isLoading,
      language,
      location.pathname,
      refreshConversations,
    ],
  );

  const retryLastMessage = useCallback(() => {
    if (failedSend) {
      void sendMessage(failedSend.text, failedSend.clientMessageId);
    }
  }, [failedSend, sendMessage]);

  const selectConversation = useCallback(
    async (conversationId: number) => {
      if (conversationId === currentConversationId) return;
      await loadConversation(conversationId);
    },
    [currentConversationId, loadConversation],
  );

  const renameConversation = useCallback(
    async (conversationId: number, title: string) => {
      if (!companyId || !title.trim()) return;
      const { data } = await apiClient.patch<AssistantConversation>(
        `/ai/conversations/${conversationId}`,
        { company_id: companyId, title: title.trim() },
      );
      setConversations((previous) =>
        previous.map((conversation) => (conversation.id === data.id ? data : conversation)),
      );
    },
    [companyId],
  );

  const archiveConversation = useCallback(
    async (conversationId: number) => {
      if (!companyId) return;
      await apiClient.patch(`/ai/conversations/${conversationId}`, {
        company_id: companyId,
        status: 'archived',
      });
      const items = await refreshConversations();
      if (currentConversationId === conversationId) {
        const next = items.find(
          (conversation) => conversation.id !== conversationId && conversation.status === 'active',
        );
        if (next) await loadConversation(next.id);
        else {
          setCurrentConversationId(null);
          setMessages([]);
          setSuggestedAction(null);
        }
      }
    },
    [companyId, currentConversationId, loadConversation, refreshConversations],
  );

  const deleteConversation = useCallback(
    async (conversationId: number) => {
      if (!companyId) return;
      await apiClient.delete(`/ai/conversations/${conversationId}`, {
        params: { company_id: companyId },
      });
      const items = await refreshConversations();
      if (currentConversationId === conversationId) {
        const next = items.find((conversation) => conversation.id !== conversationId);
        if (next) await loadConversation(next.id);
        else {
          setCurrentConversationId(null);
          setMessages([]);
          setSuggestedAction(null);
        }
      }
    },
    [companyId, currentConversationId, loadConversation, refreshConversations],
  );

  const confirmAction = useCallback(
    async (action: SuggestedAction): Promise<ConfirmActionReply | null> => {
      if (!companyId || isConfirming) return null;
      setIsConfirming(true);
      setError(null);
      try {
        const { data: result } = await apiClient.post<ConfirmActionReply>(
          '/ai/gemini-assistant/confirm-action',
          {
            company_id: companyId,
            conversation_id: currentConversationId,
            language,
            action_type: action.type,
            payload: {
              company_id: companyId,
              entry_date: action.payload.entry_date,
              description: action.payload.description,
              lines: action.payload.lines.map((line) => ({
                account_id: line.account_id,
                debit: line.debit,
                credit: line.credit,
                description: line.description ?? null,
              })),
            },
          },
        );
        if (!result.success) {
          setError(result.message);
          return result;
        }
        setSuggestedAction(null);
        if (currentConversationId) await loadConversation(currentConversationId);
        await refreshConversations();
        dataEvents.emit('journal:created');
        return result;
      } catch (requestError: unknown) {
        const detail = (requestError as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail;
        setError(
          detail ||
            (language === 'ar'
              ? 'فشل إنشاء القيد. يرجى المحاولة مرة أخرى.'
              : 'Failed to create the entry. Please try again.'),
        );
        return null;
      } finally {
        setIsConfirming(false);
      }
    },
    [
      companyId,
      currentConversationId,
      isConfirming,
      language,
      loadConversation,
      refreshConversations,
    ],
  );

  const cancelAction = useCallback(() => setSuggestedAction(null), []);

  return {
    messages,
    conversations,
    currentConversationId,
    isLoading,
    isRestoring,
    isConfirming,
    error,
    failedSend: Boolean(failedSend),
    suggestedAction,
    currentPage,
    sendMessage,
    retryLastMessage,
    confirmAction,
    cancelAction,
    createNewConversation,
    selectConversation,
    renameConversation,
    archiveConversation,
    deleteConversation,
  };
}