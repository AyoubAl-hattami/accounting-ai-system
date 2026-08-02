import { useState, useEffect, useId } from 'react';
import { Check, Copy, MailCheck, UserPlus } from 'lucide-react';
import type { CompanyUserRole } from '../../api/types';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';

interface AddCompanyUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (payload: { email: string; role: CompanyUserRole }) => Promise<string | void>;
  isSubmitting: boolean;
  error: string | null;
  setError: (err: string | null) => void;
}

const ROLES: CompanyUserRole[] = ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'];

export default function AddCompanyUserModal({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  error,
  setError,
}: AddCompanyUserModalProps) {
  const { t } = useI18n();
  const formId = useId();
  const emailId = useId();
  const roleId = useId();
  const linkId = useId();

  const [email, setEmail] = useState<string>('');
  const [role, setRole] = useState<CompanyUserRole>('viewer');
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setEmail('');
      setRole('viewer');
      setInviteLink(null);
      setCopied(false);
      setError(null);
    }
  }, [isOpen, setError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError(t.companyUsersPage.emailRequired);
      return;
    }
    const result = await onConfirm({ email: email.trim(), role });

    if (typeof result === 'string') {
      setInviteLink(window.location.origin + result);
    }
  };

  const handleCopy = () => {
    if (inviteLink) {
      navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Once the invite exists the dialog switches from a form to a hand-off screen.
  if (inviteLink) {
    return (
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={t.companyUsersPage.inviteCreated}
        description={t.companyUsersPage.inviteShareHint}
        footer={
          <button type="button" onClick={onClose} className="btn btn-primary btn-sm">
            {t.companyUsersPage.done}
          </button>
        }
      >
        <div className="space-y-4">
          <div className="callout tone-success">
            <MailCheck aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="min-w-0 flex-1 break-all text-sm">{email}</p>
          </div>

          <div>
            <label htmlFor={linkId} className="field-label">
              {t.companyUsersPage.inviteLink}
            </label>
            <div className="flex items-center gap-2">
              <input id={linkId} type="text" readOnly value={inviteLink} className="input text-xs" />
              <button type="button" onClick={handleCopy} className="btn btn-secondary btn-sm flex-shrink-0">
                {copied ? (
                  <Check aria-hidden className="h-3.5 w-3.5" />
                ) : (
                  <Copy aria-hidden className="h-3.5 w-3.5" />
                )}
                {copied ? t.companyUsersPage.copied : t.companyUsersPage.copy}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.companyUsersPage.inviteUser}
      description={t.companyUsersPage.inviteShareHint}
      error={error}
      busy={isSubmitting}
      footer={
        <>
          <button type="button" onClick={onClose} disabled={isSubmitting} className="btn btn-ghost btn-sm">
            {t.common.cancel}
          </button>
          <button type="submit" form={formId} disabled={isSubmitting} className="btn btn-primary btn-sm">
            <UserPlus aria-hidden className="h-3.5 w-3.5" />
            {isSubmitting ? t.companyUsersPage.sendingInvite : t.companyUsersPage.sendInvite}
          </button>
        </>
      }
    >
      <form id={formId} onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor={emailId} className="field-label">
            {t.companyUsersPage.inviteEmail} <span className="text-danger">*</span>
          </label>
          <input
            id={emailId}
            type="email"
            required
            autoComplete="email"
            placeholder={t.companyUsersPage.emailPlaceholder}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
          />
        </div>

        <div>
          <label htmlFor={roleId} className="field-label">
            {t.companyUsersPage.inviteRole} <span className="text-danger">*</span>
          </label>
          <select
            id={roleId}
            value={role}
            onChange={(e) => setRole(e.target.value as CompanyUserRole)}
            className="select"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t.companyUsersPage.roles[r]}
              </option>
            ))}
          </select>
        </div>
      </form>
    </Modal>
  );
}
