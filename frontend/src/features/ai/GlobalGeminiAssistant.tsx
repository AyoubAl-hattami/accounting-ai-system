/**
 * GlobalGeminiAssistant — floating button + panel wrapper.
 *
 * Mounts in AppShell, visible on every authenticated page where a company is selected.
 * Floating button adapts position to RTL/LTR layout.
 * Wraps useGeminiAssistant hook and GeminiAssistantPanel component.
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X } from 'lucide-react';
import { useI18n } from '../../i18n';
import { useGeminiAssistant } from './useGeminiAssistant';
import GeminiAssistantPanel from './GeminiAssistantPanel';
import type { CompanyUserRole } from '../../api/types';

interface GlobalGeminiAssistantProps {
  companyId: number | null;
  userRole?: CompanyUserRole | null;
  companyName?: string | null;
}

export default function GlobalGeminiAssistant({
  companyId,
  companyName,
}: GlobalGeminiAssistantProps) {
  const { t, language } = useI18n();
  const tc = t.geminiAssistant;
  const [isOpen, setIsOpen] = useState(false);

  const {
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
    loadMoreConversations,
    retryHistory,
  } = useGeminiAssistant({
    companyId,
    language: language as 'en' | 'ar',
  });

  // Don't render if no company is selected
  if (!companyId) return null;

  const hasUnread = messages.length > 0 && !isOpen;
  const lastMsg = messages[messages.length - 1];
  const hasAction = !!suggestedAction;

  return (
    <>
      {/* Floating action button */}
      <div className="fixed bottom-6 z-[58] end-6">
        <motion.button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          className="relative flex h-14 w-14 items-center justify-center rounded-xl bg-primary-solid text-primary-foreground shadow-lg transition-shadow duration-200 hover:bg-primary-solid-hover hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          title={isOpen ? tc.cancelAction : tc.askAI}
          aria-label={isOpen ? tc.cancelAction : tc.askAI}
          aria-expanded={isOpen}
          id="gemini-assistant-fab"
        >
          <AnimatePresence mode="wait">
            {isOpen ? (
              <motion.div
                key="close"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <X aria-hidden className="h-6 w-6" />
              </motion.div>
            ) : (
              <motion.div
                key="sparkles"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <Sparkles aria-hidden className="h-6 w-6" />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Unread dot */}
          <AnimatePresence>
            {(hasUnread || hasAction) && !isOpen && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                aria-hidden
                className={`absolute -top-1 h-4 w-4 rounded-full border-2 border-surface -end-1 ${
                  hasAction ? 'bg-warning-solid' : 'bg-success-solid'
                }`}
              />
            )}
          </AnimatePresence>
        </motion.button>

        {/* Tooltip on hover (when closed) */}
        <AnimatePresence>
          {!isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 4, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.95 }}
              className="pointer-events-none absolute bottom-16 end-0"
            >
              {/* Only show tooltip when there's a last message preview */}
              {lastMsg && lastMsg.role === 'assistant' && (
                <div className="max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap rounded-lg border border-border bg-surface-raised px-3 py-2 text-start shadow-lg">
                  <p className="mb-0.5 text-[10px] text-subtle-foreground">{tc.assistant}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {lastMsg.content.split('\n')[0].replace(/\*\*/g, '').slice(0, 40)}…
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Panel */}
      <GeminiAssistantPanel
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        messages={messages}
        conversations={conversations}
        currentConversation={currentConversation}
        currentConversationId={currentConversationId}
        isLoading={isLoading}
        isRestoring={isRestoring}
        isHistoryLoading={isHistoryLoading}
        historyError={historyError}
        historySearch={historySearch}
        historyStatus={historyStatus}
        historyTotal={historyTotal}
        hasMoreConversations={hasMoreConversations}
        error={error}
        failedSend={failedSend}
        isConfirming={isConfirming}
        suggestedAction={suggestedAction}
        currentPage={currentPage}
        onSendMessage={sendMessage}
        onRetryMessage={retryLastMessage}
        onConfirmAction={confirmAction}
        onCancelAction={cancelAction}
        onNewConversation={createNewConversation}
        onSelectConversation={selectConversation}
        onRenameConversation={renameConversation}
        onSetConversationStatus={setConversationStatus}
        onDeleteConversation={deleteConversation}
        onHistorySearchChange={setHistorySearch}
        onHistoryStatusChange={setHistoryStatus}
        onLoadMoreConversations={loadMoreConversations}
        onRetryHistory={retryHistory}
        companyName={companyName}
      />
    </>
  );
}
