import { useState, useEffect, useId } from 'react';
import { RotateCcw } from 'lucide-react';
import type { JournalEntry } from '../../api/types';
import type { ReverseJournalEntryPayload } from './useReverseJournalEntry';
import Modal from '../../components/ui/Modal';
import JournalEntryFacts from './JournalEntryFacts';
import { formatCurrency, formatDate } from '../../lib/format';
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
  const formId = useId();
  const entryNoId = useId();
  const dateId = useId();
  const descriptionId = useId();

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

  const totals = originalEntry
    ? originalEntry.lines.reduce(
        (acc, line) => ({
          debit: acc.debit + (parseFloat(line.debit) || 0),
          credit: acc.credit + (parseFloat(line.credit) || 0),
        }),
        { debit: 0, credit: 0 },
      )
    : { debit: 0, credit: 0 };

  return (
    <Modal
      isOpen={isOpen && originalEntry !== null}
      onClose={onClose}
      title={t.reverseJournal.title}
      description={t.reverseJournal.consequence}
      size="md"
      error={error}
      busy={isSubmitting}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button
            type="submit"
            form={formId}
            disabled={isSubmitting || !entryNo.trim() || !entryDate.trim()}
            className="btn btn-tone tone-violet btn-sm"
          >
            <RotateCcw aria-hidden className="h-3.5 w-3.5" />
            {isSubmitting ? t.reverseJournal.reversing : t.reverseJournal.reverseBtn}
          </button>
        </>
      }
    >
      <form id={formId} onSubmit={handleSubmit} className="space-y-4">
        <div className="callout tone-violet">
          <RotateCcw aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p className="min-w-0 flex-1 text-sm">{t.reverseJournal.confirmMessage}</p>
        </div>

        {originalEntry && (
          <JournalEntryFacts
            caption={t.common.originalEntrySummary}
            facts={[
              {
                label: t.common.entryNumber,
                value: <span className="numeric font-semibold text-primary">{originalEntry.entry_no}</span>,
              },
              {
                label: t.common.date,
                value: <span className="numeric">{formatDate(originalEntry.entry_date)}</span>,
              },
              { label: t.common.description, value: originalEntry.description || '—' },
              {
                label: t.common.debitTotal,
                value: <span className="numeric font-semibold text-debit">{formatCurrency(totals.debit)}</span>,
              },
              {
                label: t.common.creditTotal,
                value: <span className="numeric font-semibold text-credit">{formatCurrency(totals.credit)}</span>,
              },
            ]}
          />
        )}

        <div className="space-y-3.5">
          <div>
            <label htmlFor={entryNoId} className="field-label">
              {t.reverseJournal.entryNoLabel} <span className="text-danger">*</span>
            </label>
            <input
              id={entryNoId}
              type="text"
              required
              value={entryNo}
              onChange={(e) => setEntryNo(e.target.value)}
              placeholder={t.reverseJournal.entryNoPlaceholder}
              className="input numeric"
            />
          </div>

          <div>
            <label htmlFor={dateId} className="field-label">
              {t.reverseJournal.dateLabel} <span className="text-danger">*</span>
            </label>
            <input
              id={dateId}
              type="date"
              required
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="input numeric"
            />
          </div>

          <div>
            <label htmlFor={descriptionId} className="field-label">
              {t.reverseJournal.descriptionLabel}
            </label>
            <input
              id={descriptionId}
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t.reverseJournal.descriptionPlaceholder}
              className="input"
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}
