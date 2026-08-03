import { useId, useState } from 'react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';

export type ConfirmAction = 'activate' | 'suspend' | 'cancel';

interface SubscriptionConfirmModalProps {
  action: ConfirmAction;
  companyName: string;
  isOpen: boolean;
  busy: boolean;
  onClose: () => void;
  onConfirm: (reason: string | null) => void;
}

export default function SubscriptionConfirmModal({
  action,
  companyName,
  isOpen,
  busy,
  onClose,
  onConfirm,
}: SubscriptionConfirmModalProps) {
  const { t } = useI18n();
  const reasonId = useId();
  const [reason, setReason] = useState('');

  const copy = {
    activate: {
      title: t.platformSubscriptions.activateTitle,
      description: t.platformSubscriptions.activateDescription,
      confirmLabel: t.platformSubscriptions.actionActivate,
      confirmClass: 'btn btn-primary btn-sm',
    },
    suspend: {
      title: t.platformSubscriptions.suspendTitle,
      description: t.platformSubscriptions.suspendDescription,
      confirmLabel: t.platformSubscriptions.actionSuspend,
      confirmClass: 'btn btn-danger btn-sm',
    },
    cancel: {
      title: t.platformSubscriptions.cancelTitle,
      description: t.platformSubscriptions.cancelDescription,
      confirmLabel: t.platformSubscriptions.actionCancel,
      confirmClass: 'btn btn-danger btn-sm',
    },
  }[action];

  const close = () => {
    setReason('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      title={copy.title}
      description={copy.description}
      busy={busy}
      footer={
        <>
          <button type="button" onClick={close} disabled={busy} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button
            type="button"
            onClick={() => onConfirm(reason.trim() || null)}
            disabled={busy}
            className={copy.confirmClass}
          >
            {copy.confirmLabel}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-foreground">{companyName}</p>

        {action !== 'activate' && (
          <div>
            <label htmlFor={reasonId} className="field-label">
              {t.platformSubscriptions.reasonLabel}
            </label>
            <input
              id={reasonId}
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t.platformSubscriptions.reasonPlaceholder}
              className="input"
            />
          </div>
        )}
      </div>
    </Modal>
  );
}
