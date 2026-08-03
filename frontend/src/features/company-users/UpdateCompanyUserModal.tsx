import { useState, useEffect, useId } from 'react';
import { AlertTriangle, Save } from 'lucide-react';
import type { CompanyUser, CompanyUserRole } from '../../api/types';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';

interface UpdateCompanyUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: CompanyUser | null;
  onConfirm: (role: CompanyUserRole, isActive: boolean) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
  setError: (err: string | null) => void;
  isOnlyAdmin?: boolean;
  currentUserId?: number;
}

const ROLES: CompanyUserRole[] = ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'];

export default function UpdateCompanyUserModal({
  isOpen,
  onClose,
  user,
  onConfirm,
  isSubmitting,
  error,
  setError,
  isOnlyAdmin,
  currentUserId,
}: UpdateCompanyUserModalProps) {
  const { t } = useI18n();
  const formId = useId();
  const roleId = useId();
  const activeId = useId();
  const activeHintId = useId();

  const [role, setRole] = useState<CompanyUserRole>('viewer');
  const [isActive, setIsActive] = useState<boolean>(true);

  // Sync state with selected user details when open
  useEffect(() => {
    if (isOpen && user) {
      setRole(user.role);
      setIsActive(user.is_active);
      setError(null);
    }
  }, [isOpen, user, setError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onConfirm(role, isActive);
  };

  const isCurrentUser = user && currentUserId ? user.user_id === currentUserId : false;
  const preventDemoteOrRemove = isCurrentUser && isOnlyAdmin && user?.role === 'admin';

  return (
    <Modal
      isOpen={isOpen && user !== null}
      onClose={onClose}
      title={t.companyUsersPage.editUser}
      description={t.companyUsersPage.editUserDesc}
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
            disabled={isSubmitting || preventDemoteOrRemove}
            className="btn btn-primary btn-sm"
          >
            <Save aria-hidden className="h-3.5 w-3.5" />
            {isSubmitting ? t.companyUsersPage.savingChanges : t.companyUsersPage.saveChanges}
          </button>
        </>
      }
    >
      <form id={formId} onSubmit={handleSubmit} className="space-y-4">
        {preventDemoteOrRemove && (
          <div className="callout tone-warning">
            <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p className="min-w-0 flex-1 text-xs">{t.companyUsersPage.onlyAdminWarning}</p>
          </div>
        )}

        <div className="rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3">
          <dl className="flex items-baseline justify-between gap-4 text-xs">
            <dt className="text-subtle-foreground">{t.companyUsersPage.userId}</dt>
            <dd className="numeric font-semibold text-foreground">#{user?.user_id}</dd>
          </dl>
        </div>

        <div>
          <label htmlFor={roleId} className="field-label">
            {t.companyUsersPage.role} <span className="text-danger">*</span>
          </label>
          <select
            id={roleId}
            value={role}
            onChange={(e) => setRole(e.target.value as CompanyUserRole)}
            disabled={preventDemoteOrRemove}
            className="select"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t.companyUsersPage.roles[r]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3">
          <div className="min-w-0">
            <label htmlFor={activeId} className="text-xs font-semibold text-muted-foreground">
              {t.companyUsersPage.activeStatus}
            </label>
            <p id={activeHintId} className="mt-0.5 text-xs text-subtle-foreground">
              {t.companyUsersPage.activeStatusHint}
            </p>
          </div>
          {/* A second, text-free label so the visual track itself is clickable. */}
          <label htmlFor={activeId} className="relative inline-flex flex-shrink-0 items-center">
            <input
              id={activeId}
              type="checkbox"
              role="switch"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              disabled={preventDemoteOrRemove}
              aria-describedby={activeHintId}
              className="peer sr-only"
            />
            <span
              aria-hidden
              className="peer h-6 w-11 cursor-pointer rounded-full border border-border-strong bg-surface-overlay transition-colors after:absolute after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-border-strong after:bg-primary-foreground after:transition-transform after:content-[''] after:start-[2px] peer-checked:border-primary-solid peer-checked:bg-primary-solid peer-checked:after:translate-x-full peer-checked:after:border-transparent peer-focus-visible:ring-2 peer-focus-visible:ring-ring-soft peer-disabled:cursor-not-allowed peer-disabled:opacity-50 rtl:peer-checked:after:-translate-x-full"
            />
          </label>
        </div>
      </form>
    </Modal>
  );
}
