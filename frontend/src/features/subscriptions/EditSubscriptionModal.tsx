import { useEffect, useId, useState } from 'react';
import { Save } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';
import type { CompanySubscription, SubscriptionStatus } from '../../api/types';

const STATUSES: SubscriptionStatus[] = [
  'trial',
  'active',
  'past_due',
  'suspended',
  'cancelled',
];

interface EditSubscriptionModalProps {
  entry: CompanySubscription | null;
  isOpen: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    status: SubscriptionStatus;
    plan_code: string | null;
    expires_at: string | null;
  }) => void;
}

/** ISO instant → the `YYYY-MM-DD` a date input understands. */
function toDateInput(value: string | null): string {
  if (!value) return '';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '' : parsed.toISOString().slice(0, 10);
}

export default function EditSubscriptionModal({
  entry,
  isOpen,
  busy,
  onClose,
  onSubmit,
}: EditSubscriptionModalProps) {
  const { t } = useI18n();
  const formId = useId();
  const statusId = useId();
  const expiresId = useId();
  const expiresHintId = useId();
  const planId = useId();

  const [status, setStatus] = useState<SubscriptionStatus>('active');
  const [expiresAt, setExpiresAt] = useState('');
  const [planCode, setPlanCode] = useState('');

  useEffect(() => {
    if (!isOpen || !entry) return;
    setStatus(entry.subscription.status);
    setExpiresAt(toDateInput(entry.subscription.expires_at));
    setPlanCode(entry.subscription.plan_code ?? '');
  }, [isOpen, entry]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      status,
      plan_code: planCode.trim() || null,
      // A bare date means "expires at the end of that day" to a human, so the
      // instant sent to the server is the end of it rather than midnight.
      expires_at: expiresAt ? new Date(`${expiresAt}T23:59:59Z`).toISOString() : null,
    });
  };

  return (
    <Modal
      isOpen={isOpen && entry !== null}
      onClose={onClose}
      title={t.platformSubscriptions.editTitle}
      description={t.platformSubscriptions.editDescription}
      busy={busy}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={busy} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button type="submit" form={formId} disabled={busy} className="btn btn-primary btn-sm">
            <Save aria-hidden className="h-3.5 w-3.5" />
            {t.platformSubscriptions.saveChanges}
          </button>
        </>
      }
    >
      <form id={formId} onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm font-medium text-foreground">{entry?.company_name}</p>

        <div>
          <label htmlFor={statusId} className="field-label">
            {t.platformSubscriptions.statusLabel}
          </label>
          <select
            id={statusId}
            value={status}
            onChange={(e) => setStatus(e.target.value as SubscriptionStatus)}
            className="select"
          >
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {t.subscriptionStatus[value]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor={expiresId} className="field-label">
            {t.platformSubscriptions.expiresAtLabel}
          </label>
          <input
            id={expiresId}
            type="date"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            aria-describedby={expiresHintId}
            className="input"
          />
          <p id={expiresHintId} className="mt-1 text-xs text-subtle-foreground">
            {t.platformSubscriptions.expiresAtHelp}
          </p>
        </div>

        <div>
          <label htmlFor={planId} className="field-label">
            {t.platformSubscriptions.planCodeLabel}
          </label>
          <input
            id={planId}
            type="text"
            value={planCode}
            maxLength={50}
            onChange={(e) => setPlanCode(e.target.value)}
            placeholder={t.platformSubscriptions.planCodePlaceholder}
            className="input"
          />
        </div>
      </form>
    </Modal>
  );
}
