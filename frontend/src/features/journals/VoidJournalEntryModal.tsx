import { Ban, AlertTriangle } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import JournalEntryFacts, { type JournalEntryFact } from './JournalEntryFacts';
import { formatDate } from '../../lib/format';
import { useI18n } from '../../i18n';

interface VoidJournalEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isSubmitting: boolean;
  error: string | null;
  entryNo: string;
  entryDate?: string;
  entryDescription?: string;
}

export default function VoidJournalEntryModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  error,
  entryNo,
  entryDate,
  entryDescription,
}: VoidJournalEntryModalProps) {
  const { t } = useI18n();

  const facts: JournalEntryFact[] = [
    {
      label: t.common.entryNumber,
      value: <span className="numeric font-semibold text-primary">{entryNo}</span>,
    },
  ];
  if (entryDate) {
    facts.push({ label: t.common.date, value: <span className="numeric">{formatDate(entryDate)}</span> });
  }
  if (entryDescription) {
    facts.push({ label: t.common.description, value: entryDescription });
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.voidJournal.title}
      description={t.voidJournal.consequence}
      error={error}
      busy={isSubmitting}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button type="button" onClick={onConfirm} disabled={isSubmitting} className="btn btn-danger btn-sm">
            <Ban aria-hidden className="h-3.5 w-3.5" />
            {isSubmitting ? t.voidJournal.voiding : t.voidJournal.voidBtn}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="callout tone-danger">
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p className="min-w-0 flex-1 text-sm">{t.voidJournal.confirmMessage}</p>
        </div>

        <JournalEntryFacts facts={facts} />
      </div>
    </Modal>
  );
}
