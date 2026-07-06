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
  const { t, dir, language } = useI18n();
  const tc = t.geminiAssistant;
  const [isOpen, setIsOpen] = useState(false);
  const isRtl = dir === 'rtl';

  const {
    messages,
    isLoading,
    isConfirming,
    suggestedAction,
    currentPage,
    sendMessage,
    confirmAction,
    cancelAction,
    clearHistory,
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
      <div
        className={`fixed bottom-6 z-[58] ${isRtl ? 'left-6' : 'right-6'}`}
      >
        <motion.button
          onClick={() => setIsOpen((prev) => !prev)}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          className={`
            relative w-14 h-14 rounded-2xl
            bg-gradient-to-br from-violet-600 to-brand-600
            shadow-lg shadow-violet-500/30
            flex items-center justify-center
            text-white
            transition-all duration-200
            hover:shadow-violet-500/50 hover:shadow-xl
            border border-white/10
          `}
          title={isOpen ? tc.cancelAction : tc.askAI}
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
                <X className="w-6 h-6" />
              </motion.div>
            ) : (
              <motion.div
                key="sparkles"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <Sparkles className="w-6 h-6" />
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
                className={`
                  absolute -top-1 ${isRtl ? '-left-1' : '-right-1'}
                  w-4 h-4 rounded-full
                  ${hasAction ? 'bg-amber-400' : 'bg-emerald-400'}
                  border-2 border-surface-800
                `}
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
              className={`
                absolute bottom-16 ${isRtl ? 'left-0' : 'right-0'}
                pointer-events-none
              `}
            >
              {/* Only show tooltip when there's a last message preview */}
              {lastMsg && lastMsg.role === 'assistant' && (
                <div
                  className={`
                    px-3 py-2 rounded-xl bg-surface-700/90 border border-white/[0.08]
                    shadow-xl backdrop-blur-sm
                    ${isRtl ? 'text-right' : 'text-left'}
                    max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis
                  `}
                >
                  <p className="text-[10px] text-gray-500 mb-0.5">{tc.assistant}</p>
                  <p className="text-xs text-gray-300 truncate">
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
        isLoading={isLoading}
        isConfirming={isConfirming}
        suggestedAction={suggestedAction}
        currentPage={currentPage}
        onSendMessage={sendMessage}
        onConfirmAction={confirmAction}
        onCancelAction={cancelAction}
        onClearHistory={clearHistory}
        companyName={companyName}
      />
    </>
  );
}
