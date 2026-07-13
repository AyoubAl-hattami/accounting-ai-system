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
          <strong key={i} className="font-semibold text-white">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

function MessageBubble({ message, dir }: { message: GeminiMessage; dir: 'ltr' | 'rtl' }) {
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
            ? 'bg-brand-500/20 border border-brand-500/30'
            : isError
            ? 'bg-red-500/20 border border-red-500/30'
            : isConfirmed
            ? 'bg-emerald-500/20 border border-emerald-500/30'
            : 'bg-violet-500/20 border border-violet-500/30'
          }
        `}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 text-brand-400" />
        ) : isError ? (
          <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
        ) : isConfirmed ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <Bot className="w-3.5 h-3.5 text-violet-400" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={`
          max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed
          ${isUser
            ? 'bg-brand-500/15 border border-brand-500/20 text-gray-200'
            : isError
            ? 'bg-red-500/10 border border-red-500/20 text-red-300'
            : isConfirmed
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
            : 'bg-white/[0.04] border border-white/[0.08] text-gray-300'
          }
        `}
        dir="auto"
      >
        {message.content.split('\n').map((line, i) => (
          <p key={i} className={i > 0 ? 'mt-1' : ''}>
            <RichText text={line} />
          </p>
        ))}
        <p className="text-[10px] text-gray-600 mt-1.5">
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
      className="mx-3 mb-3 rounded-2xl bg-gradient-to-br from-violet-500/10 to-brand-500/10 border border-violet-500/20 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <Sparkles className="w-3.5 h-3.5 text-violet-400" />
        <span className="text-xs font-semibold text-violet-300 uppercase tracking-wider">
          {tc.previewNotCreated}
        </span>
      </div>

      {/* Fiscal period warning banner (today-specific) */}
      {fiscalBlocked && (
        <div className="px-3 py-2.5 bg-amber-500/10 border-b border-amber-500/20 space-y-2">
          <div className="flex items-start gap-2 text-xs text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <p className="font-semibold leading-snug">{tc.todayNotInOpenFiscalPeriod}</p>
          </div>
          <p className="text-[11px] text-amber-500/80 leading-snug pl-5">
            {tc.createFiscalPeriodForToday}
          </p>
        </div>
      )}

      {/* Confirm error banner (shown after a failed confirm attempt) */}
      {confirmError && !fiscalBlocked && (
        <div className="flex items-start gap-2 px-3 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-300">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <p>{confirmError}</p>
        </div>
      )}

      {/* Entry details */}
      <div className="px-3 py-2.5 space-y-2" dir={dir}>

        {/* Read-only entry date (backend-derived today) */}
        <div className="flex justify-between items-center gap-2 text-xs">
          <span className="text-gray-500 flex items-center gap-1 shrink-0">
            <CalendarDays className="w-3 h-3" />
            {tc.entryDateTodayOnly}
          </span>
          <span className="font-mono text-xs text-gray-300 bg-white/[0.04] border border-white/[0.08] rounded-lg px-2 py-1">
            {entryDate}
          </span>
        </div>

        <div className="text-xs text-gray-400 italic truncate">
          {action.payload.description}
        </div>

        {/* Journal lines */}
        <div className="space-y-1 pt-1 border-t border-white/[0.05]">
          {action.payload.lines.map((line, i) => (
            <div key={i} className="flex justify-between items-center text-xs gap-2">
              <span className="text-gray-400 truncate flex-1 min-w-0">
                {line.account_name}
                <span className="text-gray-600 ml-1">({line.account_code})</span>
              </span>
              {line.debit > 0 && (
                <span className="text-emerald-400 font-mono whitespace-nowrap">
                  {tc.debit} {Number(line.debit).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              )}
              {line.credit > 0 && (
                <span className="text-amber-400 font-mono whitespace-nowrap">
                  {tc.credit} {Number(line.credit).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Warnings */}
        {action.payload.warnings.length > 0 && (
          <div className="flex items-start gap-1.5 text-xs text-amber-400 pt-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            <span>{action.payload.warnings.join(' | ')}</span>
          </div>
        )}

        {/* Confirmation notice */}
        {!fiscalBlocked && (
          <>
            <p className="text-[11px] text-gray-500 pt-1">{tc.confirmWarning}</p>
            <p className="text-[10px] text-gray-600 pt-0.5 italic">{tc.draftDoesNotAffectReports}</p>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 px-3 pb-3">
        <button
          onClick={() => onConfirm()}
          disabled={isConfirmDisabled}
          title={fiscalBlocked ? tc.todayNotInOpenFiscalPeriod : undefined}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-all
            ${
              fiscalBlocked
                ? 'bg-gray-500/10 border border-gray-500/20 text-gray-600 cursor-not-allowed'
                : 'bg-emerald-500/15 border border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/25 disabled:opacity-50 disabled:cursor-not-allowed'
            }`}
          id="gemini-assistant-confirm-btn"
        >
          {isConfirming ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5" />
          )}
          {tc.confirmAction}
        </button>
        <button
          onClick={onCancel}
          disabled={isConfirming}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold hover:bg-red-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          id="gemini-assistant-cancel-btn"
        >
          <XCircle className="w-3.5 h-3.5" />
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
            className="fixed inset-0 z-[59] bg-black/30 backdrop-blur-sm lg:hidden"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`fixed inset-x-2 bottom-2 z-[60] flex h-[calc(100dvh-1rem)] max-h-[720px] flex-col overflow-hidden rounded-2xl border border-white/[0.1] bg-surface-800/95 shadow-2xl shadow-black/50 backdrop-blur-2xl transition-[width] sm:inset-x-auto sm:bottom-20 sm:h-[min(640px,calc(100vh-120px))] ${isRtl ? 'sm:left-4' : 'sm:right-4'} ${showHistory ? 'sm:w-[min(760px,calc(100vw-2rem))]' : 'sm:w-[420px]'}`}
            id="gemini-assistant-panel"
            dir={dir}
            role="dialog"
            aria-label={tc.assistant}
          >
            <div className="flex min-h-[58px] flex-shrink-0 items-center justify-between gap-2 border-b border-white/[0.07] bg-white/[0.02] px-3 py-2.5">
              <div className="flex min-w-0 items-center gap-2.5">
                {showHistory && (
                  <button
                    onClick={() => setShowHistory(false)}
                    className="rounded-lg p-1.5 text-gray-400 hover:bg-white/[0.05] hover:text-white sm:hidden"
                    title={labels.back}
                    aria-label={labels.back}
                  >
                    {isRtl ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                  </button>
                )}
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-brand-600 shadow-lg shadow-violet-500/20">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div className="min-w-0">
                  <p
                    className="max-w-[190px] truncate text-sm font-semibold text-white sm:max-w-[300px]"
                    title={currentConversation?.title || tc.assistant}
                  >
                    {currentConversation?.title || tc.assistant}
                  </p>
                  <div className="flex min-w-0 items-center gap-1.5 text-[10px] text-gray-500">
                    {isArchived && <span className="rounded bg-amber-500/10 px-1 text-amber-300">{labels.archived}</span>}
                    {companyName && <span className="truncate" title={companyName}>{companyName}</span>}
                  </div>
                </div>
              </div>

              <div className="flex flex-shrink-0 items-center gap-0.5">
                <button onClick={() => void createConversation()} className="rounded-lg p-2 text-gray-400 hover:bg-white/[0.05] hover:text-brand-300" title={labels.newConversation} aria-label={labels.newConversation}>
                  <Plus className="h-4 w-4" />
                </button>
                <button onClick={() => setShowHistory((value) => !value)} className={`rounded-lg p-2 hover:bg-white/[0.05] ${showHistory ? 'bg-white/[0.05] text-brand-300' : 'text-gray-400 hover:text-white'}`} title={labels.history} aria-label={labels.history}>
                  <History className="h-4 w-4" />
                </button>
                {currentConversation && (
                  <button onClick={() => void renameConversation(currentConversation)} className="hidden rounded-lg p-2 text-gray-400 hover:bg-white/[0.05] hover:text-white sm:block" title={labels.rename} aria-label={labels.rename}>
                    <Pencil className="h-4 w-4" />
                  </button>
                )}
                <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-white/[0.05] hover:text-white" id="gemini-assistant-close" title={labels.close} aria-label={labels.close}>
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="flex min-h-0 flex-1">
              <section className={`${showHistory ? 'flex' : 'hidden'} w-full min-w-0 flex-col border-white/[0.07] bg-black/15 sm:w-[300px] sm:flex-shrink-0 ${isRtl ? 'sm:border-l' : 'sm:border-r'}`} aria-label={labels.history}>
                <div className="space-y-2 border-b border-white/[0.07] p-3">
                  <button onClick={() => void createConversation()} className="flex w-full items-center justify-center gap-2 rounded-xl border border-brand-500/20 bg-brand-500/10 px-3 py-2 text-xs font-semibold text-brand-300 hover:bg-brand-500/15">
                    <Plus className="h-3.5 w-3.5" />
                    {labels.newConversation}
                  </button>
                  <div className="relative">
                    <Search className={`pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-600 ${isRtl ? 'right-3' : 'left-3'}`} />
                    <input
                      value={historySearch}
                      onChange={(event) => onHistorySearchChange(event.target.value)}
                      placeholder={labels.search}
                      aria-label={labels.search}
                      maxLength={100}
                      className={`w-full rounded-xl border border-white/[0.08] bg-white/[0.04] py-2 text-xs text-gray-200 outline-none placeholder:text-gray-600 focus:border-brand-500/40 ${isRtl ? 'pr-9 pl-3' : 'pl-9 pr-3'}`}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-1 rounded-xl bg-white/[0.03] p-1" role="tablist">
                    {(['active', 'archived'] as const).map((status) => (
                      <button
                        key={status}
                        role="tab"
                        aria-selected={historyStatus === status}
                        onClick={() => onHistoryStatusChange(status)}
                        className={`rounded-lg px-2 py-1.5 text-xs font-medium ${historyStatus === status ? 'bg-brand-500/15 text-brand-300' : 'text-gray-500 hover:text-gray-300'}`}
                      >
                        {status === 'active' ? labels.active : labels.archived}
                      </button>
                    ))}
                  </div>
                  <p className="px-1 text-[10px] text-gray-600">{labels.conversationsCount}</p>
                </div>

                <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
                  {isHistoryLoading && conversations.length === 0 && [0, 1, 2].map((item) => (
                    <div key={item} className="animate-pulse rounded-xl border border-white/[0.05] p-3">
                      <div className="h-3 w-2/3 rounded bg-white/[0.08]" />
                      <div className="mt-2 h-2 w-full rounded bg-white/[0.05]" />
                    </div>
                  ))}

                  {historyError && (
                    <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-center text-xs text-red-300">
                      <p>{historyError}</p>
                      <button onClick={() => void onRetryHistory()} className="mt-2 rounded-lg border border-red-400/20 px-2 py-1 font-semibold hover:bg-red-500/10">{labels.retry}</button>
                    </div>
                  )}

                  {!isHistoryLoading && !historyError && conversations.length === 0 && (
                    <div className="flex h-36 flex-col items-center justify-center gap-2 text-center text-xs text-gray-500">
                      <History className="h-6 w-6 text-gray-700" />
                      {labels.noConversations}
                    </div>
                  )}

                  {conversations.map((conversation) => (
                    <article
                      key={conversation.id}
                      className={`group rounded-xl border p-2 ${conversation.id === currentConversationId ? 'border-brand-500/40 bg-brand-500/10' : 'border-transparent hover:border-white/[0.06] hover:bg-white/[0.03]'}`}
                      aria-current={conversation.id === currentConversationId ? 'true' : undefined}
                    >
                      <button onClick={() => void selectConversation(conversation.id)} className="w-full min-w-0 text-start" title={conversation.title}>
                        <div className="flex items-center gap-2">
                          <span className="min-w-0 flex-1 truncate text-xs font-medium text-gray-200">{conversation.title}</span>
                          {conversation.id === currentConversationId && <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-brand-400" title={labels.current} />}
                        </div>
                        <p className="mt-1 truncate text-[10px] text-gray-500" title={conversation.last_message_preview || ''}>{conversation.last_message_preview || '—'}</p>
                        <p className="mt-1 text-[9px] text-gray-600">{formatActivity(conversation.last_message_at)}</p>
                      </button>
                      <div className="mt-1 flex items-center justify-end gap-0.5 border-t border-white/[0.04] pt-1">
                        <button onClick={() => void renameConversation(conversation)} className="rounded p-1.5 text-gray-600 hover:bg-white/[0.05] hover:text-gray-300" title={labels.rename} aria-label={`${labels.rename}: ${conversation.title}`}><Pencil className="h-3 w-3" /></button>
                        <button
                          onClick={() => {
                            if (conversation.status === 'active' && !window.confirm(labels.archiveConfirm(conversation.title))) return;
                            void onSetConversationStatus(conversation.id, conversation.status === 'active' ? 'archived' : 'active');
                          }}
                          className="rounded p-1.5 text-gray-600 hover:bg-white/[0.05] hover:text-amber-300"
                          title={conversation.status === 'active' ? labels.archive : labels.unarchive}
                          aria-label={`${conversation.status === 'active' ? labels.archive : labels.unarchive}: ${conversation.title}`}
                        >
                          {conversation.status === 'active' ? <Archive className="h-3 w-3" /> : <ArchiveRestore className="h-3 w-3" />}
                        </button>
                        <button onClick={() => void deleteConversation(conversation)} className="rounded p-1.5 text-gray-600 hover:bg-red-500/10 hover:text-red-300" title={labels.delete} aria-label={`${labels.delete}: ${conversation.title}`}><Trash2 className="h-3 w-3" /></button>
                      </div>
                    </article>
                  ))}

                  {hasMoreConversations && (
                    <button onClick={() => void onLoadMoreConversations()} disabled={isHistoryLoading} className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs text-brand-300 hover:bg-brand-500/10 disabled:opacity-50">
                      {isHistoryLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                      {labels.loadMore}
                    </button>
                  )}
                </div>
              </section>

              <section className={`${showHistory ? 'hidden sm:flex' : 'flex'} min-w-0 flex-1 flex-col`} aria-label={currentConversation?.title || tc.assistant}>
                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/10">
                  {isRestoring && (
                    <div className="flex h-full items-center justify-center gap-2 text-xs text-gray-400">
                      <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
                      {labels.restore}
                    </div>
                  )}

                  {!isRestoring && messages.length === 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex h-full flex-col items-center justify-center gap-3 py-6 text-center">
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/20 to-brand-500/20"><Sparkles className="h-7 w-7 text-violet-400" /></div>
                      <div><p className="text-sm font-semibold text-gray-300">{tc.assistant}</p><p className="mt-1 max-w-[240px] text-xs leading-relaxed text-gray-500">{tc.typeYourQuestion}</p></div>
                    </motion.div>
                  )}

                  {!isRestoring && messages.map((message) => <MessageBubble key={message.id} message={message} dir={dir} />)}

                  {isLoading && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-violet-500/30 bg-violet-500/20"><Bot className="h-3.5 w-3.5 text-violet-400" /></div>
                      <div className="flex items-center gap-2 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-3.5 py-2.5"><Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" /><span className="text-xs text-gray-400">{tc.thinking}</span></div>
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
                  <div className={`mx-3 mt-2 flex items-center justify-between gap-2 rounded-xl border px-3 py-2 text-xs ${error ? 'border-red-500/20 bg-red-500/10 text-red-300' : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'}`}>
                    <span className="min-w-0 flex-1">{error || notice}</span>
                    {failedSend && <button onClick={onRetryMessage} disabled={isLoading} className="flex-shrink-0 rounded-lg border border-red-400/20 px-2 py-1 font-semibold hover:bg-red-500/10">{labels.retry}</button>}
                  </div>
                )}

                {isArchived && (
                  <div className="mx-3 mt-2 flex items-center justify-between gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                    <span>{labels.readOnly}</span>
                    <button onClick={() => currentConversation && void onSetConversationStatus(currentConversation.id, 'active')} className="flex-shrink-0 rounded-lg border border-amber-400/20 px-2 py-1 font-semibold hover:bg-amber-500/10">{labels.unarchive}</button>
                  </div>
                )}

                <div className="flex-shrink-0 border-t border-white/[0.07] px-3 pb-3 pt-2">
                  <div className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 transition-colors focus-within:border-brand-500/40">
                    <input
                      ref={inputRef}
                      type="text"
                      value={inputText}
                      onChange={(event) => setInputText(event.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={isArchived ? labels.cannotSend : tc.typeYourQuestion}
                      disabled={isLoading || isRestoring || isArchived}
                      dir="auto"
                      className="min-w-0 flex-1 bg-transparent text-sm text-gray-200 outline-none placeholder:text-gray-600 disabled:opacity-50"
                      id="gemini-assistant-input"
                      maxLength={2000}
                    />
                    <button onClick={handleSend} disabled={isLoading || isRestoring || isArchived || !inputText.trim()} className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg border border-brand-500/30 bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 disabled:cursor-not-allowed disabled:opacity-40" id="gemini-assistant-send" aria-label={tc.send} title={tc.send}>
                      {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className={`h-3.5 w-3.5 ${isRtl ? 'rotate-180' : ''}`} />}
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