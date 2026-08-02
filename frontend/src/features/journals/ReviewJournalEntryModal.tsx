import { CheckCircle2, ShieldCheck } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import JournalEntryFacts from './JournalEntryFacts';
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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.reviewJournal.title}
      description={t.reviewJournal.consequence}
      error={error}
      busy={isSubmitting}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="btn btn-tone tone-primary btn-sm"
          >
            <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
            {isSubmitting ? t.reviewJournal.reviewing : t.reviewJournal.reviewBtn}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="callout tone-primary">
          <ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p className="min-w-0 flex-1 text-sm">{t.reviewJournal.confirmMessage}</p>
        </div>

        <JournalEntryFacts
          facts={[
            {
              label: t.common.entryNumber,
              value: <span className="numeric font-semibold text-primary">{entryNo}</span>,
            },
          ]}
        />
      </div>
    </Modal>
  );
}
