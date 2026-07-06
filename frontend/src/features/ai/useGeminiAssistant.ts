/**
 * useGeminiAssistant — state management hook for the Global Gemini Assistant panel.
 *
 * Uses the shared apiClient (axios) from src/api/client.ts.
 * apiClient.baseURL = http://127.0.0.1:8010 (no /api/v1 prefix).
 * Backend routes: POST /ai/gemini-assistant, POST /ai/gemini-assistant/confirm-action
 *
 * Never stores JWT, passwords, or secrets in state or history.
 */

import { useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import apiClient from '../../api/client';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface GeminiMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp: Date;
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
  fiscal_period_valid?: boolean;        // false = date has no open fiscal period
  open_period_suggestion?: string | null; // ISO date of a valid open period
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
}

export interface ConfirmActionReply {
  success: boolean;
  message: string;
  error_code?: string | null;             // fiscal_period_not_found, account_inactive, etc.
  open_period_suggestion?: string | null; // ISO date of first available open period
  entity_id?: number | null;
  entity_type?: string | null;
  data?: Record<string, unknown> | null;
}

// ── Route → page name mapping ─────────────────────────────────────────────────

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

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface useGeminiAssistantOptions {
  companyId: number | null;
  language?: 'en' | 'ar';
}

export function useGeminiAssistant({ companyId, language = 'en' }: useGeminiAssistantOptions) {
  const location = useLocation();
  const [messages, setMessages] = useState<GeminiMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestedAction, setSuggestedAction] = useState<SuggestedAction | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  const currentPage = routeToPage(location.pathname);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!companyId || !text.trim() || isLoading) return;

      const userMsg: GeminiMessage = {
        id: makeId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);
      setSuggestedAction(null);

      // Build last 6 messages for follow-up context (never includes secrets)
      const historyTurns = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content.slice(0, 500),
      }));

      try {
        // Use apiClient: baseURL is already http://127.0.0.1:8010
        // Backend route: POST /ai/gemini-assistant  (no /api/v1 prefix on this server)
        const { data: reply } = await apiClient.post<GeminiAssistantReply>('/ai/gemini-assistant', {
          company_id: companyId,
          message: text.trim(),
          language,
          page_context: {
            route: location.pathname,
            page: currentPage,
            filters: {},
          },
          history: historyTurns,
        });

        const assistantMsg: GeminiMessage = {
          id: makeId(),
          role: 'assistant',
          content: reply.reply,
          intent: reply.intent,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);

        if (reply.suggested_action) {
          setSuggestedAction(reply.suggested_action);
        }
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        const message =
          detail ||
          (status === 404
            ? language === 'ar'
              ? 'خدمة مساعد الذكاء الاصطناعي غير متاحة حاليًا. حاول مرة أخرى.'
              : 'Gemini Assistant service is unavailable. Please try again.'
            : status === 403
            ? language === 'ar'
              ? 'ليس لديك صلاحية استخدام المساعد الذكي.'
              : 'You do not have permission to use the Gemini Assistant.'
            : language === 'ar'
            ? 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.'
            : 'An unexpected error occurred. Please try again.');

        setError(message);

        const errMsg: GeminiMessage = {
          id: makeId(),
          role: 'assistant',
          content: `⚠️ ${message}`,
          intent: 'error',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [companyId, isLoading, language, location.pathname, currentPage, messages],
  );

  const confirmAction = useCallback(
    async (action: SuggestedAction, overrideDate?: string): Promise<ConfirmActionReply | null> => {
      if (!companyId || isConfirming) return null;

      setIsConfirming(true);
      setError(null);

      // Map error_code → friendly i18n message
      const getFriendlyMessage = (
        errorCode: string | null | undefined,
        openPeriodSuggestion: string | null | undefined,
      ): string => {
        const fiscalCodes: Record<string, string> = {
          fiscal_period_not_found: language === 'ar'
            ? 'لا توجد فترة مالية مفتوحة لهذا التاريخ. اختر تاريخًا داخل فترة مالية مفتوحة أو أنشئ فترة مالية جديدة.'
            : 'No open fiscal period was found for this entry date. Choose a date within an open fiscal period or create a new fiscal period.',
          fiscal_period_closed: language === 'ar'
            ? 'الفترة المالية لهذا التاريخ مغلقة. يرجى اختيار تاريخ داخل فترة مفتوحة.'
            : 'The fiscal period for this entry date is closed. Please choose a date within an open fiscal period.',
          fiscal_year_not_found: language === 'ar'
            ? 'لا توجد سنة مالية لهذا التاريخ. يرجى اختيار تاريخ داخل سنة مالية موجودة.'
            : 'No fiscal year found for this entry date. Please choose a date within an existing fiscal year.',
          fiscal_year_closed: language === 'ar'
            ? 'السنة المالية لهذا التاريخ مغلقة. يرجى اختيار تاريخ داخل سنة مالية مفتوحة.'
            : 'The fiscal year for this entry date is closed. Please choose a date within an open fiscal year.',
          account_inactive: language === 'ar'
            ? 'أحد الحسابات المستخدمة غير نشط. يرجى التحقق من الحسابات.'
            : 'One of the accounts used is inactive. Please check the accounts.',
          unbalanced_entry: language === 'ar'
            ? 'القيد غير متوازن. يجب أن يتساوى مجموع المدين والدائن.'
            : 'The journal entry is not balanced. Total debit must equal total credit.',
        };
        let msg = fiscalCodes[errorCode ?? ''] ?? (
          language === 'ar'
            ? 'فشل إنشاء القيد. تحقق من التاريخ وحاول مرة أخرى.'
            : 'Failed to create the journal entry. Please check the date and try again.'
        );
        if (openPeriodSuggestion) {
          msg += language === 'ar'
            ? ` (تاريخ مقترح: ${openPeriodSuggestion})`
            : ` (Suggested date: ${openPeriodSuggestion})`;
        }
        return msg;
      };

      try {
        // Backend route: POST /ai/gemini-assistant/confirm-action  (always HTTP 200)
        const { data: result } = await apiClient.post<ConfirmActionReply>(
          '/ai/gemini-assistant/confirm-action',
          {
            company_id: companyId,
            action_type: action.type,
            payload: {
              company_id: companyId,
              entry_date: overrideDate ?? action.payload.entry_date,
              description: action.payload.description,
              lines: action.payload.lines.map((l) => ({
                account_id: l.account_id,
                debit: l.debit,
                credit: l.credit,
                description: l.description ?? null,
              })),
            },
          },
        );

        // Structured failure (success=false with error_code) — keep preview open
        if (!result.success) {
          const friendlyMsg = getFriendlyMessage(result.error_code, result.open_period_suggestion);
          setError(friendlyMsg);

          const errMsg: GeminiMessage = {
            id: makeId(),
            role: 'assistant',
            content: `⚠️ ${friendlyMsg}`,
            intent: 'error',
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errMsg]);
          // Do NOT clear suggestedAction — keep the preview card visible for retry/cancel
          return result;
        }

        // Success — clear the preview card and show success message
        setSuggestedAction(null);

        const confirmMsg: GeminiMessage = {
          id: makeId(),
          role: 'assistant',
          content:
            language === 'ar'
              ? `✅ تم إنشاء القيد المسودة بنجاح! رقم القيد: **${result.data?.entry_no ?? '—'}**`
              : `✅ Draft journal entry created! Entry No: **${result.data?.entry_no ?? '—'}**`,
          intent: 'action_confirmed',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, confirmMsg]);

        return result;
      } catch (err: unknown) {
        // HTTP-level error (network, 403, etc.)
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        const status = (err as { response?: { status?: number } })?.response?.status;
        const message =
          detail ||
          (status === 403
            ? language === 'ar'
              ? 'ليس لديك صلاحية إنشاء القيود المحاسبية.'
              : 'You do not have permission to create journal entries.'
            : language === 'ar'
            ? 'فشل إنشاء القيد. يرجى المحاولة يدوياً.'
            : 'Failed to create entry. Please try manually.');

        setError(message);

        const errMsg: GeminiMessage = {
          id: makeId(),
          role: 'assistant',
          content: `❌ ${message}`,
          intent: 'error',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errMsg]);

        return null;
      } finally {
        setIsConfirming(false);
      }
    },
    [companyId, isConfirming, language],
  );


  const cancelAction = useCallback(() => {
    setSuggestedAction(null);
  }, []);

  const clearHistory = useCallback(() => {
    setMessages([]);
    setSuggestedAction(null);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    isConfirming,
    error,
    suggestedAction,
    currentPage,
    sendMessage,
    confirmAction,
    cancelAction,
    clearHistory,
  };
}
