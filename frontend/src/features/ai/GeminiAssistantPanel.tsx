/**
 * GeminiAssistantPanel — the glass side panel chat UI for the Global Gemini Assistant.
 *
 * Features:
 * - Message thread (user + assistant bubbles) with markdown-ish bold rendering
 * - Suggested action card with Confirm / Cancel
 * - Input box + Send button
 * - Thinking indicator
 * - RTL/LTR support via dir from useI18n
 * - AnimatePresence slide-in animation
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  Send,
  X,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  Bot,
  User,
  Plus,
  History,
  Pencil,
  Archive,
  ArchiveRestore,
  Search,
  ChevronLeft,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import GroundingCards from './GroundingCards';
import type {
  AssistantConversation,
  GeminiMessage,
  ConfirmActionReply,
  SuggestedAction,
} from './useGeminiAssistant';

interface GeminiAssistantPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: GeminiMessage[];
  conversations: AssistantConversation[];
  currentConversation: AssistantConversation | null;
  currentConversationId: number | null;
  isLoading: boolean;
  isRestoring: boolean;
  isConfirming: boolean;
  isHistoryLoading: boolean;
  historyError: string | null;
  historySearch: string;
  historyStatus: 'active' | 'archived';
  historyTotal: number;
  hasMoreConversations: boolean;
  error: string | null;
  failedSend: boolean;
  suggestedAction: SuggestedAction | null;
  currentPage: string;
  onSendMessage: (text: string) => void;
  onRetryMessage: () => void;
  onConfirmAction: (action: SuggestedAction) => Promise<ConfirmActionReply | null>;
  onCancelAction: () => void;
  onNewConversation: () => Promise<AssistantConversation | null>;
  onSelectConversation: (conversationId: number) => Promise<void>;
  onRenameConversation: (conversationId: number, title: string) => Promise<boolean>;
  onSetConversationStatus: (
    conversationId: number,
    status: 'active' | 'archived',
  ) => Promise<boolean>;
  onDeleteConversation: (conversationId: number) => Promise<boolean>;
  onHistorySearchChange: (search: string) => void;
  onHistoryStatusChange: (status: 'active' | 'archived') => void;
  onLoadMoreConversations: () => Promise<AssistantConversation[]>;
  onRetryHistory: () => Promise<AssistantConversation[]>;
  companyName?: string | null;
}
/** Render text with **bold** markers */
function RichText({ text }: { text: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-foreground">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function MessageBubble({ message, dir, language }: { message: GeminiMessage; dir: 'ltr' | 'rtl'; language: 'en' | 'ar' }) {
  const isUser = message.role === 'user';
  const isError = message.intent === 'error';
  const isConfirmed = message.intent === 'action_confirmed';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-2.5 ${isUser ? (dir === 'rtl' ? 'flex-row-reverse' : 'flex-row-reverse') : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`
          w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5
          ${isUser
            ? 'bg-primary-soft-hover border border-primary-border'
            : isError
            ? 'bg-danger-soft border border-danger-border'
            : isConfirmed
            ? 'bg-success-soft border border-success-border'
            : 'bg-violet-soft border border-violet-border'
          }
        `}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 text-primary" />
        ) : isError ? (
          <AlertTriangle className="w-3.5 h-3.5 text-danger" />
        ) : isConfirmed ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-success" />
        ) : (
          <Bot className="w-3.5 h-3.5 text-violet" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`
          max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed
          ${isUser
            ? 'bg-primary-soft border border-primary-border text-foreground'
            : isError
            ? 'bg-danger-soft border border-danger-border text-danger'
            : isConfirmed
            ? 'bg-success-soft border border-success-border text-success'
            : 'bg-surface-muted border border-border text-muted-foreground'
          }
        `}
        dir="auto"
      >
        {message.content.split('\n').map((line, i) => (
          <p key={i} className={i > 0 ? 'mt-1' : ''}>
            <RichText text={line} />
          </p>
        ))}
        <GroundingCards message={message} language={language} dir={dir} />
        <p className="text-[10px] text-subtle-foreground mt-1.5">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </motion.div>
  );
}

function SuggestedActionCard({
  action,
  isConfirming,
  confirmError,
  onConfirm,
  onCancel,
  dir,
}: {
  action: SuggestedAction;
  isConfirming: boolean;
  confirmError?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
  dir: 'ltr' | 'rtl';
}) {
  const { t } = useI18n();
  const tc = t.geminiAssistant;

  // Date is read-only — always backend-derived today
  const entryDate = String(action.payload.entry_date);
  const fiscalBlocked = action.payload.fiscal_period_valid === false;
  const isConfirmDisabled = isConfirming || fiscalBlocked;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.97 }}
      className="mx-3 mb-3 overflow-hidden rounded-lg border border-violet-border bg-surface"
    >
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-violet-border bg-violet-soft px-3 py-2.5">
        <Sparkles aria-hidden className="h-3.5 w-3.5 text-violet" />
        <span className="overline text-violet">{tc.previewNotCreated}</span>
      </div>

      {/* Fiscal period warning banner (today-specific) */}
      {fiscalBlocked && (
        <div className="space-y-1.5 border-b border-warning-border bg-warning-soft px-3 py-2.5 text-warning">
          <div className="flex items-start gap-2 text-xs">
            <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            <p className="font-semibold leading-snug">{tc.todayNotInOpenFiscalPeriod}</p>
          </div>
          <p className="ps-5 text-[11px] leading-snug">{tc.createFiscalPeriodForToday}</p>
        </div>
      )}

      {/* Confirm error banner (shown after a failed confirm attempt) */}
      {confirmError && !fiscalBlocked && (
        <div
          role="alert"
          className="flex items-start gap-2 border-b border-danger-border bg-danger-soft px-3 py-2 text-xs text-danger"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <p>{confirmError}</p>
        </div>
      )}

      {/* Entry details */}
      <div className="px-3 py-2.5 space-y-2" dir={dir}>

        {/* Read-only entry date (backend-derived today) */}
        <div className="flex items-center justify-between gap-2 text-xs">
          <span className="flex shrink-0 items-center gap-1 text-subtle-foreground">
            <CalendarDays aria-hidden className="h-3 w-3" />
            {tc.entryDateTodayOnly}
          </span>
          <span className="numeric rounded-md border border-border bg-surface-muted px-2 py-1 text-xs text-muted-foreground">
            {entryDate}
          </span>
        </div>

        <div className="truncate text-xs italic text-muted-foreground">
          {action.payload.description}
        </div>

        {/* Journal lines */}
        <div className="space-y-1 border-t border-border-subtle pt-1">
          {action.payload.lines.map((line, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-xs">
              <span className="min-w-0 flex-1 truncate text-muted-foreground">
                {line.account_name}
                <span className="ms-1 text-subtle-foreground">({line.account_code})</span>
              </span>
              {line.debit > 0 && (
                <span className="numeric whitespace-nowrap text-debit">
                  {tc.debit} {Number(line.debit).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              )}
              {line.credit > 0 && (
                <span className="numeric whitespace-nowrap text-credit">
                  {tc.credit} {Number(line.credit).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Warnings */}
        {action.payload.warnings.length > 0 && (
          <div className="flex items-start gap-1.5 pt-1 text-xs text-warning">
            <AlertTriangle aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            <span>{action.payload.warnings.join(' | ')}</span>
          </div>
        )}

        {/* Confirmation notice */}
        {!fiscalBlocked && (
          <>
            <p className="pt-1 text-[11px] text-subtle-foreground">{tc.confirmWarning}</p>
            <p className="pt-0.5 text-[10px] italic text-subtle-foreground">{tc.draftDoesNotAffectReports}</p>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 px-3 pb-3">
        <button
          type="button"
          onClick={() => onConfirm()}
          disabled={isConfirmDisabled}
          title={fiscalBlocked ? tc.todayNotInOpenFiscalPeriod : undefined}
          className={`btn btn-tone btn-sm flex-1 ${fiscalBlocked ? 'tone-neutral' : 'tone-success'}`}
          id="gemini-assistant-confirm-btn"
        >
          {isConfirming ? (
            <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
          )}
          {tc.confirmAction}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isConfirming}
          className="btn btn-tone tone-danger btn-sm flex-1"
          id="gemini-assistant-cancel-btn"
        >
          <XCircle aria-hidden className="h-3.5 w-3.5" />
          {tc.cancelAction}
        </button>
      </div>
    </motion.div>
  );
}

export default function GeminiAssistantPanel({
  isOpen,
  onClose,
  messages,
  conversations,
  currentConversation,
  currentConversationId,
  isLoading,
  isRestoring,
  isConfirming,
  isHistoryLoading,
  historyError,
  historySearch,
  historyStatus,
  historyTotal,
  hasMoreConversations,
  error,
  failedSend,
  suggestedAction,
  onSendMessage,
  onRetryMessage,
  onConfirmAction,
  onCancelAction,
  onNewConversation,
  onSelectConversation,
  onRenameConversation,
  onSetConversationStatus,
  onDeleteConversation,
  onHistorySearchChange,
  onHistoryStatusChange,
  onLoadMoreConversations,
  onRetryHistory,
  companyName,
}: GeminiAssistantPanelProps) {
  const { t, dir, language } = useI18n();
  const tc = t.geminiAssistant;
  const [inputText, setInputText] = useState('');
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isRtl = dir === 'rtl';
  const isArchived = currentConversation?.status === 'archived';

  const labels = language === 'ar'
    ? {
        history: 'سجل المحادثات',
        newConversation: 'محادثة جديدة',
        search: 'بحث في المحادثات',
        active: 'نشطة',
        archived: 'مؤرشفة',
        rename: 'إعادة تسمية',
        archive: 'أرشفة',
        unarchive: 'إلغاء الأرشفة',
        delete: 'حذف',
        restore: 'جارٍ استعادة المحادثة...',
        retry: 'إعادة المحاولة',
        loadMore: 'تحميل المزيد',
        noConversations: 'لا توجد محادثات مطابقة',
        renamePrompt: 'اسم المحادثة الجديد',
        deleteConfirm: (title: string) => `هل تريد حذف المحادثة «${title}» نهائيًا؟`,
        archiveConfirm: (title: string) => `هل تريد أرشفة المحادثة «${title}»؟`,
        deleted: 'تم حذف المحادثة',
        readOnly: 'هذه المحادثة مؤرشفة وللقراءة فقط.',
        cannotSend: 'لا يمكن الإرسال إلى محادثة مؤرشفة.',
        close: 'إغلاق',
        back: 'العودة إلى الرسائل',
        current: 'المحادثة الحالية',
        conversationsCount: `${historyTotal} محادثة`,
      }
    : {
        history: 'Conversation history',
        newConversation: 'New conversation',
        search: 'Search conversations',
        active: 'Active',
        archived: 'Archived',
        rename: 'Rename',
        archive: 'Archive',
        unarchive: 'Unarchive',
        delete: 'Delete',
        restore: 'Restoring conversation...',
        retry: 'Retry',
        loadMore: 'Load more',
        noConversations: 'No conversations found',
        renamePrompt: 'New conversation name',
        deleteConfirm: (title: string) => `Delete “${title}” permanently?`,
        archiveConfirm: (title: string) => `Archive “${title}”?`,
        deleted: 'Conversation deleted',
        readOnly: 'This conversation is archived and read-only.',
        cannotSend: 'Cannot send to an archived conversation.',
        close: 'Close',
        back: 'Back to messages',
        current: 'Current conversation',
        conversationsCount: `${historyTotal} conversations`,
      };

  useEffect(() => {
    if (isOpen && !showHistory) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen, showHistory]);

  useEffect(() => {
    if (isOpen && !showHistory && !isArchived) {
      const timeout = window.setTimeout(() => inputRef.current?.focus(), 100);
      return () => window.clearTimeout(timeout);
    }
  }, [isArchived, isOpen, showHistory]);

  useEffect(() => {
    setInputText('');
    setConfirmError(null);
  }, [currentConversationId]);

  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (showHistory) setShowHistory(false);
      else onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose, showHistory]);

  const handleSend = () => {
    if (isArchived) {
      setNotice(labels.cannotSend);
      return;
    }
    if (inputText.trim() && !isLoading && !isRestoring) {
      onSendMessage(inputText.trim());
      setInputText('');
      setConfirmError(null);
      setNotice(null);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const formatActivity = (value: string) =>
    new Intl.DateTimeFormat(language === 'ar' ? 'ar' : 'en', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));

  const selectConversation = async (conversationId: number) => {
    setInputText('');
    setNotice(null);
    await onSelectConversation(conversationId);
    setShowHistory(false);
  };

  const createConversation = async () => {
    setInputText('');
    setNotice(null);
    const created = await onNewConversation();
    if (created) setShowHistory(false);
  };

  const renameConversation = async (conversation: AssistantConversation) => {
    const title = window.prompt(labels.renamePrompt, conversation.title);
    if (!title?.trim()) return;
    await onRenameConversation(conversation.id, title.trim());
  };

  const deleteConversation = async (conversation: AssistantConversation) => {
    if (!window.confirm(labels.deleteConfirm(conversation.title))) return;
    if (await onDeleteConversation(conversation.id)) setNotice(labels.deleted);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[59] bg-backdrop backdrop-blur-sm lg:hidden"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`fixed inset-x-2 bottom-2 z-[60] flex h-[calc(100dvh-1rem)] max-h-[720px] flex-col overflow-hidden rounded-lg border border-border-strong bg-surface shadow-xl backdrop-blur-2xl transition-[width] sm:inset-x-auto sm:bottom-20 sm:h-[min(640px,calc(100vh-120px))] ${isRtl ? 'sm:left-4' : 'sm:right-4'} ${showHistory ? 'sm:w-[min(760px,calc(100vw-2rem))]' : 'sm:w-[420px]'}`}
            id="gemini-assistant-panel"
            dir={dir}
            role="dialog"
            aria-label={tc.assistant}
          >
            <div className="flex min-h-[58px] flex-shrink-0 items-center justify-between gap-2 border-b border-border bg-surface-muted px-3 py-2.5">
              <div className="flex min-w-0 items-center gap-2.5">
                {showHistory && (
                  <button
                    type="button"
                    onClick={() => setShowHistory(false)}
                    className="btn-icon h-8 w-8 sm:hidden"
                    title={labels.back}
                    aria-label={labels.back}
                  >
                    {isRtl ? (
                      <ChevronRight aria-hidden className="h-4 w-4" />
                    ) : (
                      <ChevronLeft aria-hidden className="h-4 w-4" />
                    )}
                  </button>
                )}
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary-solid shadow-sm">
                  <Sparkles aria-hidden className="h-4 w-4 text-primary-foreground" />
                </div>
                <div className="min-w-0">
                  <p
                    className="max-w-[190px] truncate text-sm font-semibold text-foreground sm:max-w-[300px]"
                    title={currentConversation?.title || tc.assistant}
                  >
                    {currentConversation?.title || tc.assistant}
                  </p>
                  <div className="flex min-w-0 items-center gap-1.5 text-[10px] text-subtle-foreground">
                    {isArchived && <span className="badge tone-warning">{labels.archived}</span>}
                    {companyName && <span className="truncate" title={companyName}>{companyName}</span>}
                  </div>
                </div>
              </div>

              <div className="flex flex-shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  onClick={() => void createConversation()}
                  className="btn-icon h-8 w-8"
                  title={labels.newConversation}
                  aria-label={labels.newConversation}
                >
                  <Plus aria-hidden className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setShowHistory((value) => !value)}
                  className={`btn-icon h-8 w-8 ${showHistory ? 'bg-surface-overlay text-primary' : ''}`}
                  title={labels.history}
                  aria-label={labels.history}
                  aria-expanded={showHistory}
                >
                  <History aria-hidden className="h-4 w-4" />
                </button>
                {currentConversation && (
                  <button
                    type="button"
                    onClick={() => void renameConversation(currentConversation)}
                    className="btn-icon hidden h-8 w-8 sm:inline-flex"
                    title={labels.rename}
                    aria-label={labels.rename}
                  >
                    <Pencil aria-hidden className="h-4 w-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-icon h-8 w-8"
                  id="gemini-assistant-close"
                  title={labels.close}
                  aria-label={labels.close}
                >
                  <X aria-hidden className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="flex min-h-0 flex-1">
              <section className={`${showHistory ? 'flex' : 'hidden'} w-full min-w-0 flex-col bg-surface-sunken sm:w-[300px] sm:flex-shrink-0 sm:border-s sm:border-border`} aria-label={labels.history}>
                <div className="space-y-2 border-b border-border p-3">
                  <button type="button" onClick={() => void createConversation()} className="btn btn-tone tone-primary btn-sm btn-block">
                    <Plus aria-hidden className="h-3.5 w-3.5" />
                    {labels.newConversation}
                  </button>
                  <div className="relative">
                    <Search aria-hidden className="pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle-foreground start-3" />
                    <input
                      type="search"
                      value={historySearch}
                      onChange={(event) => onHistorySearchChange(event.target.value)}
                      placeholder={labels.search}
                      aria-label={labels.search}
                      maxLength={100}
                      className="input py-1.5 text-xs ps-9 pe-3"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-1 rounded-lg bg-surface-muted p-1" role="tablist" aria-label={labels.history}>
                    {(['active', 'archived'] as const).map((status) => (
                      <button
                        key={status}
                        type="button"
                        role="tab"
                        aria-selected={historyStatus === status}
                        onClick={() => onHistoryStatusChange(status)}
                        className={`rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${historyStatus === status ? 'bg-surface text-primary shadow-sm' : 'text-subtle-foreground hover:text-foreground'}`}
                      >
                        {status === 'active' ? labels.active : labels.archived}
                      </button>
                    ))}
                  </div>
                  <p className="px-1 text-[10px] text-subtle-foreground">{labels.conversationsCount}</p>
                </div>

                <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
                  {isHistoryLoading && conversations.length === 0 && [0, 1, 2].map((item) => (
                    <div key={item} className="animate-pulse rounded-lg border border-border-subtle p-3">
                      <div className="h-3 w-2/3 rounded bg-surface-overlay" />
                      <div className="mt-2 h-2 w-full rounded bg-surface-overlay" />
                    </div>
                  ))}

                  {historyError && (
                    <div role="alert" className="rounded-lg border border-danger-border bg-danger-soft p-3 text-center text-xs text-danger">
                      <p>{historyError}</p>
                      <button type="button" onClick={() => void onRetryHistory()} className="btn btn-tone tone-danger btn-sm mt-2">
                        {labels.retry}
                      </button>
                    </div>
                  )}

                  {!isHistoryLoading && !historyError && conversations.length === 0 && (
                    <div className="flex h-36 flex-col items-center justify-center gap-2 text-center text-xs text-subtle-foreground">
                      <History aria-hidden className="h-6 w-6 text-subtle-foreground" />
                      {labels.noConversations}
                    </div>
                  )}

                  {conversations.map((conversation) => (
                    <article
                      key={conversation.id}
                      className={`group rounded-lg border p-2 ${conversation.id === currentConversationId ? 'border-primary-border bg-primary-soft' : 'border-transparent hover:border-border hover:bg-surface-muted'}`}
                      aria-current={conversation.id === currentConversationId ? 'true' : undefined}
                    >
                      <button type="button" onClick={() => void selectConversation(conversation.id)} className="w-full min-w-0 rounded text-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring-soft" title={conversation.title}>
                        <div className="flex items-center gap-2">
                          <span className="min-w-0 flex-1 truncate text-xs font-medium text-foreground">{conversation.title}</span>
                          {conversation.id === currentConversationId && <span aria-hidden className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-solid" title={labels.current} />}
                        </div>
                        <p className="mt-1 truncate text-[10px] text-subtle-foreground" title={conversation.last_message_preview || ''}>{conversation.last_message_preview || '—'}</p>
                        <p className="mt-1 text-[9px] text-subtle-foreground">{formatActivity(conversation.last_message_at)}</p>
                      </button>
                      <div className="mt-1 flex items-center justify-end gap-0.5 border-t border-border-subtle pt-1">
                        <button type="button" onClick={() => void renameConversation(conversation)} className="btn-icon h-7 w-7" title={labels.rename} aria-label={`${labels.rename}: ${conversation.title}`}><Pencil aria-hidden className="h-3 w-3" /></button>
                        <button
                          type="button"
                          onClick={() => {
                            if (conversation.status === 'active' && !window.confirm(labels.archiveConfirm(conversation.title))) return;
                            void onSetConversationStatus(conversation.id, conversation.status === 'active' ? 'archived' : 'active');
                          }}
                          className="btn-icon h-7 w-7 hover:text-warning"
                          title={conversation.status === 'active' ? labels.archive : labels.unarchive}
                          aria-label={`${conversation.status === 'active' ? labels.archive : labels.unarchive}: ${conversation.title}`}
                        >
                          {conversation.status === 'active' ? <Archive aria-hidden className="h-3 w-3" /> : <ArchiveRestore aria-hidden className="h-3 w-3" />}
                        </button>
                        <button type="button" onClick={() => void deleteConversation(conversation)} className="btn-icon h-7 w-7 hover:bg-danger-soft hover:text-danger" title={labels.delete} aria-label={`${labels.delete}: ${conversation.title}`}><Trash2 aria-hidden className="h-3 w-3" /></button>
                      </div>
                    </article>
                  ))}

                  {hasMoreConversations && (
                    <button type="button" onClick={() => void onLoadMoreConversations()} disabled={isHistoryLoading} className="btn btn-ghost btn-sm btn-block text-primary">
                      {isHistoryLoading && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />}
                      {labels.loadMore}
                    </button>
                  )}
                </div>
              </section>

              <section className={`${showHistory ? 'hidden sm:flex' : 'flex'} min-w-0 flex-1 flex-col`} aria-label={currentConversation?.title || tc.assistant}>
                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
                  {isRestoring && (
                    <div className="flex h-full items-center justify-center gap-2 text-xs text-muted-foreground">
                      <Loader2 aria-hidden className="h-4 w-4 animate-spin text-violet" />
                      {labels.restore}
                    </div>
                  )}

                  {!isRestoring && messages.length === 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex h-full flex-col items-center justify-center gap-3 py-6 text-center">
                      <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-violet-border bg-violet-soft"><Sparkles aria-hidden className="h-7 w-7 text-violet" /></div>
                      <div><p className="text-sm font-semibold text-foreground">{tc.assistant}</p><p className="mt-1 max-w-[240px] text-xs leading-relaxed text-subtle-foreground">{tc.typeYourQuestion}</p></div>
                    </motion.div>
                  )}

                  {!isRestoring && messages.map((message) => <MessageBubble key={message.id} message={message} dir={dir} language={language} />)}

                  {isLoading && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-violet-border bg-violet-soft"><Bot aria-hidden className="h-3.5 w-3.5 text-violet" /></div>
                      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-muted px-3.5 py-2.5"><Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin text-violet" /><span className="text-xs text-muted-foreground">{tc.thinking}</span></div>
                    </motion.div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                <AnimatePresence>
                  {suggestedAction && !isArchived && (
                    <SuggestedActionCard
                      action={suggestedAction}
                      isConfirming={isConfirming}
                      confirmError={confirmError}
                      onConfirm={async () => {
                        setConfirmError(null);
                        const result = await onConfirmAction(suggestedAction);
                        if (result && !result.success) {
                          const fiscalCodes: Record<string, string> = {
                            fiscal_period_not_found: tc.todayNotInOpenFiscalPeriod,
                            fiscal_period_closed: tc.todayNotInOpenFiscalPeriod,
                            fiscal_year_not_found: tc.fiscalYearNotFound,
                            fiscal_year_closed: tc.fiscalYearClosed,
                            gemini_date_must_be_today: tc.dateMustBeToday,
                            today_not_in_open_fiscal_period: tc.todayNotInOpenFiscalPeriod,
                          };
                          let message = (result.error_code && fiscalCodes[result.error_code]) || tc.confirmFailed;
                          if (result.open_period_suggestion) message += ` (${tc.suggestedDate}: ${result.open_period_suggestion})`;
                          setConfirmError(message);
                        }
                      }}
                      onCancel={() => { setConfirmError(null); onCancelAction(); }}
                      dir={dir}
                    />
                  )}
                </AnimatePresence>

                {(error || notice) && (
                  <div
                    role={error ? 'alert' : 'status'}
                    className={`callout mx-3 mt-2 items-center justify-between text-xs ${error ? 'tone-danger' : 'tone-success'}`}
                  >
                    <span className="min-w-0 flex-1">{error || notice}</span>
                    {failedSend && (
                      <button type="button" onClick={onRetryMessage} disabled={isLoading} className="btn btn-tone tone-danger btn-sm flex-shrink-0">
                        {labels.retry}
                      </button>
                    )}
                  </div>
                )}

                {isArchived && (
                  <div className="callout tone-warning mx-3 mt-2 items-center justify-between text-xs">
                    <span className="min-w-0 flex-1">{labels.readOnly}</span>
                    <button
                      type="button"
                      onClick={() => currentConversation && void onSetConversationStatus(currentConversation.id, 'active')}
                      className="btn btn-tone tone-warning btn-sm flex-shrink-0"
                    >
                      {labels.unarchive}
                    </button>
                  </div>
                )}

                <div className="flex-shrink-0 border-t border-border px-3 pb-3 pt-2">
                  <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-muted px-3 py-2 transition-colors focus-within:border-primary-solid focus-within:ring-2 focus-within:ring-ring-soft">
                    <input
                      ref={inputRef}
                      type="text"
                      value={inputText}
                      onChange={(event) => setInputText(event.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={isArchived ? labels.cannotSend : tc.typeYourQuestion}
                      disabled={isLoading || isRestoring || isArchived}
                      dir="auto"
                      className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-subtle-foreground disabled:opacity-50"
                      id="gemini-assistant-input"
                      maxLength={2000}
                    />
                    <button type="button" onClick={handleSend} disabled={isLoading || isRestoring || isArchived || !inputText.trim()} className="btn btn-primary h-7 w-7 flex-shrink-0 p-0" id="gemini-assistant-send" aria-label={tc.send} title={tc.send}>
                      {isLoading ? <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" /> : <Send aria-hidden className="h-3.5 w-3.5 rtl:rotate-180" />}
                    </button>
                  </div>
                </div>
              </section>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}