import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import apiClient from '../../api/client';
import { dataEvents } from '../../lib/dataEvents';
import type { ClarificationOption, PendingTransaction } from './pendingContext';

const HISTORY_PAGE_SIZE = 20;
type ConversationStatus = 'active' | 'archived';

export interface GeminiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  metadata?: AssistantMessageMetadata | null;
  timestamp: Date;
}

export interface AssistantMessageMetadata {
  intent?: string;
  suggested_action?: SuggestedAction | null;
  grounding?: unknown;
}

export interface AssistantConversation {
  id: number;
  company_id: number;
  title: string;
  title_source: 'fallback' | 'greeting' | 'auto' | 'manual';
  status: ConversationStatus;
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
  metadata: AssistantMessageMetadata | null;
  created_at: string;
}

interface ConversationDetail extends AssistantConversation {
  messages: PersistedMessage[];
  messages_total: number;
}

interface ConversationList {
  items: AssistantConversation[];
  total: number;
  skip: number;
  limit: number;
}

interface MessageExchange {
  conversation: AssistantConversation;
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
    metadata: message.metadata,
    timestamp: new Date(message.created_at),
  };
}

function clientMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `message-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function selectedConversationKey(companyId: number): string {
  return `gemini_selected_conversation_${companyId}`;
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
  const [currentConversation, setCurrentConversation] = useState<AssistantConversation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historySearch, setHistorySearch] = useState('');
  const [historyStatus, setHistoryStatus] = useState<ConversationStatus>('active');
  const [historyTotal, setHistoryTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [suggestedAction, setSuggestedAction] = useState<SuggestedAction | null>(null);
  const [failedSend, setFailedSend] = useState<FailedSend | null>(null);
  const companyRequestRef = useRef(0);
  const conversationRequestRef = useRef(0);
  const historyRequestRef = useRef(0);
  const conversationsRef = useRef<AssistantConversation[]>([]);

  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  const clearConversationState = useCallback(() => {
    conversationRequestRef.current += 1;
    setCurrentConversation(null);
    setMessages([]);
    setSuggestedAction(null);
    setFailedSend(null);
  }, []);

  const applyConversationDetail = useCallback((detail: ConversationDetail) => {
    setCurrentConversation(detail);
    setMessages(detail.messages.map(toUiMessage));
    const lastMessage = detail.messages[detail.messages.length - 1];
    setSuggestedAction(lastMessage?.metadata?.suggested_action ?? null);
    setFailedSend(null);
    setError(null);
    localStorage.setItem(selectedConversationKey(detail.company_id), String(detail.id));
  }, []);

  const loadConversation = useCallback(
    async (conversationId: number): Promise<boolean> => {
      if (!companyId) return false;
      const requestId = ++conversationRequestRef.current;
      setIsRestoring(true);
      setMessages([]);
      setSuggestedAction(null);
      try {
        const { data } = await apiClient.get<ConversationDetail>(
          `/ai/conversations/${conversationId}`,
          { params: { company_id: companyId, messages_limit: 200 } },
        );
        if (requestId !== conversationRequestRef.current) return false;
        applyConversationDetail(data);
        return true;
      } catch (requestError: unknown) {
        if (requestId !== conversationRequestRef.current) return false;
        const status = (requestError as { response?: { status?: number } }).response?.status;
        if (status === 403 || status === 404) {
          clearConversationState();
          localStorage.removeItem(selectedConversationKey(companyId));
        }
        setError(
          language === 'ar'
            ? 'تعذر تحميل المحادثة المطلوبة.'
            : 'The selected conversation could not be loaded.',
        );
        return false;
      } finally {
        if (requestId === conversationRequestRef.current) setIsRestoring(false);
      }
    },
    [applyConversationDetail, clearConversationState, companyId, language],
  );

  const fetchHistory = useCallback(
    async (append = false): Promise<AssistantConversation[]> => {
      if (!companyId) return [];
      const requestId = ++historyRequestRef.current;
      setIsHistoryLoading(true);
      setHistoryError(null);
      const page = append ? Math.floor(conversationsRef.current.length / HISTORY_PAGE_SIZE) + 1 : 1;
      try {
        const { data } = await apiClient.get<ConversationList>('/ai/conversations', {
          params: {
            company_id: companyId,
            status: historyStatus,
            search: historySearch.trim() || undefined,
            page,
            page_size: HISTORY_PAGE_SIZE,
          },
        });
        if (requestId !== historyRequestRef.current) return [];
        setHistoryTotal(data.total);
        setConversations((previous) => {
          if (!append) return data.items;
          const known = new Set(previous.map((conversation) => conversation.id));
          return [...previous, ...data.items.filter((conversation) => !known.has(conversation.id))];
        });
        setCurrentConversation((current) => {
          if (!current) return current;
          return data.items.find((item) => item.id === current.id) ?? current;
        });
        return data.items;
      } catch {
        if (requestId === historyRequestRef.current) {
          setHistoryError(
            language === 'ar'
              ? 'تعذر تحميل سجل المحادثات.'
              : 'Conversation history could not be loaded.',
          );
        }
        return [];
      } finally {
        if (requestId === historyRequestRef.current) setIsHistoryLoading(false);
      }
    }, [companyId, historySearch, historyStatus, language]);

  useEffect(() => {
    const requestId = ++companyRequestRef.current;
    historyRequestRef.current += 1;
    conversationRequestRef.current += 1;
    setMessages([]);
    setConversations([]);
    setCurrentConversation(null);
    setSuggestedAction(null);
    setFailedSend(null);
    setError(null);
    setHistoryError(null);
    setHistorySearch('');
    setHistoryStatus('active');
    setHistoryTotal(0);
    if (!companyId) return;

    setIsRestoring(true);
    void apiClient
      .get<ConversationList>('/ai/conversations', {
        params: { company_id: companyId, status: 'active', page: 1, page_size: HISTORY_PAGE_SIZE },
      })
      .then(async ({ data }) => {
        if (requestId !== companyRequestRef.current) return;
        setConversations(data.items);
        setHistoryTotal(data.total);
        const storedId = Number(localStorage.getItem(selectedConversationKey(companyId)));
        const preferredId = Number.isInteger(storedId) && storedId > 0 ? storedId : data.items[0]?.id;
        if (!preferredId) return;
        const detail = await apiClient.get<ConversationDetail>(
          `/ai/conversations/${preferredId}`,
          { params: { company_id: companyId, messages_limit: 200 } },
        ).catch(async (requestError: unknown) => {
          const status = (requestError as { response?: { status?: number } }).response?.status;
          if ((status === 403 || status === 404) && data.items[0]?.id && data.items[0].id !== preferredId) {
            localStorage.removeItem(selectedConversationKey(companyId));
            return apiClient.get<ConversationDetail>(`/ai/conversations/${data.items[0].id}`, {
              params: { company_id: companyId, messages_limit: 200 },
            });
          }
          throw requestError;
        });
        if (requestId === companyRequestRef.current) applyConversationDetail(detail.data);
      })
      .catch(() => {
        if (requestId === companyRequestRef.current) {
          clearConversationState();
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
  }, [applyConversationDetail, clearConversationState, companyId, language]);

  useEffect(() => {
    if (!companyId) return;
    const timeout = window.setTimeout(() => void fetchHistory(false), 250);
    return () => window.clearTimeout(timeout);
  }, [companyId, fetchHistory, historySearch, historyStatus]);

  const createNewConversation = useCallback(async () => {
    if (!companyId) return null;
    try {
      const { data } = await apiClient.post<AssistantConversation>('/ai/conversations', {
        company_id: companyId,
        language,
      });
      historyRequestRef.current += 1;
      setHistorySearch('');
      setHistoryStatus('active');
      setConversations((previous) => [data, ...previous.filter((item) => item.id !== data.id)]);
      setHistoryTotal((total) => total + 1);
      setCurrentConversation(data);
      setMessages([]);
      setSuggestedAction(null);
      setFailedSend(null);
      setError(null);
      localStorage.setItem(selectedConversationKey(companyId), String(data.id));
      return data;
    } catch {
      setError(language === 'ar' ? 'تعذر إنشاء محادثة جديدة.' : 'A new conversation could not be created.');
      return null;
    }
  }, [companyId, language]);

  const sendMessage = useCallback(
    async (text: string, retryClientMessageId?: string) => {
      const trimmed = text.trim();
      if (!companyId || !trimmed || isLoading) return;
      if (currentConversation?.status === 'archived') {
        setError(
          language === 'ar'
            ? 'لا يمكن الإرسال إلى محادثة مؤرشفة. ألغِ الأرشفة أولاً.'
            : 'Cannot send to an archived conversation. Unarchive it first.',
        );
        return;
      }

      setIsLoading(true);
      setError(null);
      setSuggestedAction(null);
      const outgoingId = retryClientMessageId ?? clientMessageId();
      const optimisticId = `pending-${outgoingId}`;
      setMessages((previous) => [
        ...previous.filter((message) => message.id !== optimisticId),
        { id: optimisticId, role: 'user', content: trimmed, timestamp: new Date() },
      ]);

      try {
        let conversationId = currentConversation?.id ?? null;
        if (!conversationId) {
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
            page_context: { route: location.pathname, page: currentPage, filters: {} },
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
        setCurrentConversation(data.conversation);
        setConversations((previous) => {
          if (historyStatus !== 'active') return previous;
          const query = historySearch.trim().toLocaleLowerCase();
          const matches =
            !query ||
            data.conversation.title.toLocaleLowerCase().includes(query) ||
            (data.conversation.last_message_preview || '').toLocaleLowerCase().includes(query);
          if (!matches) return previous.filter((item) => item.id !== data.conversation.id);
          return [
            data.conversation,
            ...previous.filter((conversation) => conversation.id !== data.conversation.id),
          ];
        });
        setSuggestedAction(data.assistant_reply.suggested_action ?? null);
        setFailedSend(null);
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
    }, [
      companyId,
      createNewConversation,
      currentConversation,
      currentPage,
      historySearch,
      historyStatus,
      isLoading,
      language,
      location.pathname,
    ],
  );

  const retryLastMessage = useCallback(() => {
    if (failedSend) void sendMessage(failedSend.text, failedSend.clientMessageId);
  }, [failedSend, sendMessage]);

  const selectConversation = useCallback(
    async (conversationId: number) => {
      if (conversationId === currentConversation?.id) return;
      const summary = conversations.find((conversation) => conversation.id === conversationId);
      if (summary) setCurrentConversation(summary);
      await loadConversation(conversationId);
    },
    [conversations, currentConversation?.id, loadConversation],
  );

  const renameConversation = useCallback(
    async (conversationId: number, title: string): Promise<boolean> => {
      if (!companyId || !title.trim()) return false;
      try {
        const { data } = await apiClient.patch<AssistantConversation>(
          `/ai/conversations/${conversationId}`,
          { company_id: companyId, title: title.trim() },
        );
        setConversations((previous) => {
          const query = historySearch.trim().toLocaleLowerCase();
          const matches =
            !query ||
            data.title.toLocaleLowerCase().includes(query) ||
            (data.last_message_preview || '').toLocaleLowerCase().includes(query);
          if (!matches) {
            const wasListed = previous.some((conversation) => conversation.id === data.id);
            if (wasListed) setHistoryTotal((total) => Math.max(0, total - 1));
            return previous.filter((conversation) => conversation.id !== data.id);
          }
          return previous.map((conversation) => (conversation.id === data.id ? data : conversation));
        });
        setCurrentConversation((current) => (current?.id === data.id ? data : current));
        return true;
      } catch (requestError: unknown) {
        const detail = (requestError as { response?: { data?: { detail?: string } } })
          .response?.data?.detail;
        setHistoryError(typeof detail === 'string' ? detail : language === 'ar' ? 'تعذر تغيير الاسم.' : 'The conversation could not be renamed.');
        return false;
      }
    }, [companyId, historySearch, language],
  );

  const setConversationStatus = useCallback(
    async (conversationId: number, status: ConversationStatus): Promise<boolean> => {
      if (!companyId) return false;
      try {
        const { data } = await apiClient.patch<AssistantConversation>(
          `/ai/conversations/${conversationId}`,
          { company_id: companyId, status },
        );
        setCurrentConversation((current) => (current?.id === data.id ? data : current));
        setConversations((previous) => {
          if (historyStatus !== status) return previous.filter((item) => item.id !== data.id);
          return [data, ...previous.filter((item) => item.id !== data.id)];
        });
        setHistoryTotal((total) =>
          historyStatus === status ? total + 1 : Math.max(0, total - 1),
        );
        return true;
      } catch {
        setHistoryError(language === 'ar' ? 'تعذر تحديث حالة المحادثة.' : 'The conversation status could not be updated.');
        return false;
      }
    }, [companyId, historyStatus, language],
  );

  const deleteConversation = useCallback(
    async (conversationId: number): Promise<boolean> => {
      if (!companyId) return false;
      const previous = conversations;
      const previousTotal = historyTotal;
      const wasListed = previous.some((conversation) => conversation.id === conversationId);
      setConversations((items) => items.filter((conversation) => conversation.id !== conversationId));
      if (wasListed) setHistoryTotal((total) => Math.max(0, total - 1));
      try {
        await apiClient.delete(`/ai/conversations/${conversationId}`, {
          params: { company_id: companyId },
        });
        if (currentConversation?.id === conversationId) {
          clearConversationState();
          localStorage.removeItem(selectedConversationKey(companyId));
          const { data } = await apiClient.get<ConversationList>('/ai/conversations', {
            params: { company_id: companyId, status: 'active', page: 1, page_size: HISTORY_PAGE_SIZE },
          });
          const next = data.items[0];
          if (next) await loadConversation(next.id);
        }
        return true;
      } catch {
        setConversations(previous);
        setHistoryTotal(previousTotal);
        setHistoryError(language === 'ar' ? 'تعذر حذف المحادثة.' : 'The conversation could not be deleted.');
        return false;
      }
    }, [clearConversationState, companyId, conversations, currentConversation?.id, historyTotal, language, loadConversation],
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
            conversation_id: currentConversation?.id ?? null,
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
        if (currentConversation) await loadConversation(currentConversation.id);
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
    }, [companyId, currentConversation, isConfirming, language, loadConversation],
  );

  const cancelAction = useCallback(() => setSuggestedAction(null), []);

  return {
    messages,
    conversations,
    currentConversation,
    currentConversationId: currentConversation?.id ?? null,
    isLoading,
    isRestoring,
    isConfirming,
    isHistoryLoading,
    historyError,
    historySearch,
    historyStatus,
    historyTotal,
    hasMoreConversations: conversations.length < historyTotal,
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
    setConversationStatus,
    deleteConversation,
    setHistorySearch,
    setHistoryStatus,
    loadMoreConversations: () => fetchHistory(true),
    retryHistory: () => fetchHistory(false),
  };
}