import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useI18n } from '../../i18n';

interface ReviewJournalEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isSubmitting: boolean;
  error: string | null;
  entryNo: string;
}

export default function ReviewJournalEntryModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  error,
  entryNo,
}: ReviewJournalEntryModalProps) {
  const { t } = useI18n();
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-md bg-surface-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-base font-bold text-white">{t.reviewJournal.title}</h3>
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-white/[0.04] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-white">{t.reviewJournal.confirmMessage}</p>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Reviewed entries can be posted by an approver.
                  </p>
                </div>
              </div>

              {/* Journal Entry Details */}
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">{t.common.entryNumber}</span>
                  <span className="font-mono font-semibold text-brand-400">{entryNo}</span>
                </div>
              </div>

              {/* Error state */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2"
                >
                  <span className="font-semibold">{t.common.errorLabel}</span>
                  <span className="flex-1">{error}</span>
                </motion.div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-white/[0.06] bg-surface-800/40 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
              >
                {t.common.cancel}
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4.5 py-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-brand-500/25 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {isSubmitting ? (
                  <span>{t.reviewJournal.reviewing}</span>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{t.reviewJournal.reviewBtn}</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
