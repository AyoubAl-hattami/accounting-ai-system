import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, RotateCcw } from 'lucide-react';
import type { JournalEntry } from '../../api/types';
import type { ReverseJournalEntryPayload } from './useReverseJournalEntry';
import { formatCurrency } from '../../lib/format';
import { useI18n } from '../../i18n';

interface ReverseJournalEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (payload: ReverseJournalEntryPayload) => void;
  isSubmitting: boolean;
  error: string | null;
  originalEntry: JournalEntry | null;
}

const generateReversalEntryNo = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  return `REV-FE-${year}${month}${day}${hours}${minutes}${seconds}`;
};

export default function ReverseJournalEntryModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  error,
  originalEntry,
}: ReverseJournalEntryModalProps) {
  const { t } = useI18n();
  const [entryNo, setEntryNo] = useState('');
  const [entryDate, setEntryDate] = useState('2026-01-16');
  const [description, setDescription] = useState('');

  // Initialize fields on open
  useEffect(() => {
    if (isOpen && originalEntry) {
      setEntryNo(generateReversalEntryNo());
      setEntryDate('2026-01-16');
      setDescription(`Reversal of ${originalEntry.entry_no}`);
    }
  }, [isOpen, originalEntry]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!entryNo.trim() || !entryDate.trim()) return;
    onConfirm({
      entry_no: entryNo.trim(),
      entry_date: entryDate.trim(),
      description: description.trim(),
    });
  };

  // Calculate totals of original entry
  const totals = originalEntry ? (() => {
    let debit = 0;
    let credit = 0;
    for (const line of originalEntry.lines) {
      debit += parseFloat(line.debit) || 0;
      credit += parseFloat(line.credit) || 0;
    }
    return { debit, credit };
  })() : { debit: 0, credit: 0 };

  return (
    <AnimatePresence>
      {isOpen && originalEntry && (
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
            className="relative w-full max-w-lg bg-surface-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-base font-bold text-white">{t.reverseJournal.title}</h3>
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-white/[0.04] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex-1 flex flex-col min-h-0">
              {/* Content */}
              <div className="px-6 py-6 space-y-4 max-h-[70vh] overflow-y-auto">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                    <RotateCcw className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-white">Reverse this posted journal entry?</p>
                    <p className="text-xs text-gray-400 leading-relaxed">
                      This will create a new draft reversal entry with opposite debit and credit lines.
                    </p>
                  </div>
                </div>

                {/* Original Entry Details */}
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] space-y-2.5">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-gray-500">{t.common.originalEntrySummary}</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500 block">{t.common.entryNumber}</span>
                      <span className="font-mono font-semibold text-brand-400">{originalEntry.entry_no}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">{t.common.date}</span>
                      <span className="text-gray-300">{new Date(originalEntry.entry_date).toLocaleDateString()}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-gray-500 block">{t.common.description}</span>
                      <span className="text-gray-300 block truncate">{originalEntry.description || '—'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">{t.common.debitTotal}</span>
                      <span className="font-mono font-semibold text-emerald-400">{formatCurrency(totals.debit)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500 block">{t.common.creditTotal}</span>
                      <span className="font-mono font-semibold text-red-400">{formatCurrency(totals.credit)}</span>
                    </div>
                  </div>
                </div>

                {/* Form Fields */}
                <div className="space-y-3.5 pt-2">
                  <div>
                    <label htmlFor="reversalEntryNo" className="block text-xs font-semibold text-gray-400 mb-1.5">
                      {t.reverseJournal.entryNoLabel} <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="reversalEntryNo"
                      type="text"
                      required
                      value={entryNo}
                      onChange={(e) => setEntryNo(e.target.value)}
                      placeholder="e.g. REV-FE-..."
                      className="input-field text-sm"
                    />
                  </div>

                  <div>
                    <label htmlFor="reversalDate" className="block text-xs font-semibold text-gray-400 mb-1.5">
                      {t.reverseJournal.dateLabel} <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="reversalDate"
                      type="date"
                      required
                      value={entryDate}
                      onChange={(e) => setEntryDate(e.target.value)}
                      className="input-field text-sm cursor-pointer"
                    />
                  </div>

                  <div>
                    <label htmlFor="reversalDescription" className="block text-xs font-semibold text-gray-400 mb-1.5">
                      {t.reverseJournal.descriptionLabel}
                    </label>
                    <input
                      id="reversalDescription"
                      type="text"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Optional description"
                      className="input-field text-sm"
                    />
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
              <div className="px-6 py-4 border-t border-white/[0.06] bg-surface-800/40 flex items-center justify-end gap-3 mt-auto">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !entryNo.trim() || !entryDate.trim()}
                  className="inline-flex items-center gap-1.5 px-4.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-purple-500/25 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  {isSubmitting ? (
                    <span>{t.reverseJournal.reversing}</span>
                  ) : (
                    <>
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>{t.reverseJournal.reverseBtn}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
