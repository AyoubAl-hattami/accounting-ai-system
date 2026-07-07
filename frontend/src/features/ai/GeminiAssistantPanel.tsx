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
} from 'lucide-react';
import { useI18n } from '../../i18n';
import type { GeminiMessage, ConfirmActionReply, SuggestedAction } from './useGeminiAssistant';

interface GeminiAssistantPanelProps {
  isOpen: boolean;
  onClose: () => void;
  messages: GeminiMessage[];
  isLoading: boolean;
  isConfirming: boolean;
  suggestedAction: SuggestedAction | null;
  currentPage: string;
  onSendMessage: (text: string) => void;
  onConfirmAction: (action: SuggestedAction) => Promise<ConfirmActionReply | null>;
  onCancelAction: () => void;
  onClearHistory: () => void;
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
  isLoading,
  isConfirming,
  suggestedAction,
  currentPage,
  onSendMessage,
  onConfirmAction,
  onCancelAction,
  onClearHistory,
  companyName,
}: GeminiAssistantPanelProps) {
  const { t, dir } = useI18n();
  const tc = t.geminiAssistant;
  const [inputText, setInputText] = useState('');
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isRtl = dir === 'rtl';

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = () => {
    if (inputText.trim() && !isLoading) {
      onSendMessage(inputText.trim());
      setInputText('');
      setConfirmError(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop (mobile) */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[59] lg:hidden"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className={`
              fixed bottom-20 z-[60]
              ${isRtl ? 'left-4' : 'right-4'}
              w-[360px] max-w-[calc(100vw-2rem)]
              flex flex-col
              rounded-2xl overflow-hidden
              bg-surface-800/90 backdrop-blur-2xl
              border border-white/[0.1]
              shadow-2xl shadow-black/50
            `}
            style={{ maxHeight: 'calc(100vh - 120px)', height: '540px' }}
            id="gemini-assistant-panel"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.07] bg-white/[0.02] flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-brand-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{tc.assistant}</p>
                  {companyName && (
                    <p className="text-[10px] text-gray-500 truncate max-w-[160px]">{companyName}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Current page badge */}
                <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                  <ChevronRight className="w-3 h-3 text-gray-600" />
                  <span className="text-[10px] text-gray-500">{currentPage.replace(/_/g, ' ')}</span>
                </div>

                {/* Clear */}
                {messages.length > 0 && (
                  <button
                    onClick={onClearHistory}
                    className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/[0.05] transition-colors"
                    title={tc.clearChat}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}

                {/* Close */}
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/[0.05] transition-colors"
                  id="gemini-assistant-close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
              {/* Welcome message */}
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center h-full gap-3 text-center py-6"
                >
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-500/20 to-brand-500/20 border border-violet-500/20 flex items-center justify-center">
                    <Sparkles className="w-7 h-7 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-300">{tc.assistant}</p>
                    <p className="text-xs text-gray-500 mt-1 max-w-[240px] leading-relaxed">
                      {tc.typeYourQuestion}
                    </p>
                  </div>
                  <p className="text-[10px] text-gray-600">{tc.poweredByAI}</p>
                </motion.div>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} dir={dir} />
              ))}

              {/* Thinking indicator */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-2.5 items-center"
                >
                  <div className="w-7 h-7 rounded-full bg-violet-500/20 border border-violet-500/30 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-3.5 h-3.5 text-violet-400" />
                  </div>
                  <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl px-3.5 py-2.5 flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 text-violet-400 animate-spin" />
                    <span className="text-xs text-gray-400">{tc.thinking}</span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Suggested action card */}
            <AnimatePresence>
              {suggestedAction && (
                <SuggestedActionCard
                  action={suggestedAction}
                  isConfirming={isConfirming}
                  confirmError={confirmError}
                  onConfirm={async () => {
                    setConfirmError(null);
                    const result = await onConfirmAction(suggestedAction);
                    // If confirm returned a failure, surface the error in the card
                    if (result && !result.success) {
                      const code = result.error_code;
                      const suggestion = result.open_period_suggestion;
                      const fiscalCodes: Record<string, string> = {
                        fiscal_period_not_found: tc.todayNotInOpenFiscalPeriod,
                        fiscal_period_closed: tc.todayNotInOpenFiscalPeriod,
                        fiscal_year_not_found: tc.fiscalYearNotFound,
                        fiscal_year_closed: tc.fiscalYearClosed,
                        gemini_date_must_be_today: tc.dateMustBeToday,
                        today_not_in_open_fiscal_period: tc.todayNotInOpenFiscalPeriod,
                      };
                      let msg = (code && fiscalCodes[code]) || tc.confirmFailed;
                      if (suggestion) msg += ` (${tc.suggestedDate}: ${suggestion})`;
                      setConfirmError(msg);
                    } else {
                      setConfirmError(null);
                    }
                  }}
                  onCancel={() => {
                    setConfirmError(null);
                    onCancelAction();
                  }}
                  dir={dir}
                />
              )}
            </AnimatePresence>

            {/* Input area */}
            <div className="px-3 pb-3 pt-2 border-t border-white/[0.07] flex-shrink-0">
              <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 focus-within:border-brand-500/40 transition-colors">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={tc.typeYourQuestion}
                  disabled={isLoading}
                  dir="auto"
                  className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-600 outline-none min-w-0 disabled:opacity-50"
                  id="gemini-assistant-input"
                  maxLength={2000}
                />
                <button
                  onClick={handleSend}
                  disabled={isLoading || !inputText.trim()}
                  className="flex-shrink-0 w-7 h-7 rounded-lg bg-brand-500/20 border border-brand-500/30 text-brand-400 flex items-center justify-center hover:bg-brand-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                  id="gemini-assistant-send"
                >
                  {isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Send className={`w-3.5 h-3.5 ${isRtl ? 'rotate-180' : ''}`} />
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
