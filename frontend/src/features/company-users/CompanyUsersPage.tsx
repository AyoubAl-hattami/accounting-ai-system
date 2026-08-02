import { useState, useEffect, useId, useMemo, type ReactNode } from 'react';
import {
  Ban,
  CheckCircle2,
  Clock,
  Link2,
  Lock,
  Pencil,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
  UserPlus,
  Users,
  XCircle,
} from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import Modal from '../../components/ui/Modal';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useToast } from '../../components/feedback/useToast';
import { useCompanyUsers } from './useCompanyUsers';
import CompanyUserRoleBadge from './CompanyUserRoleBadge';
import AddCompanyUserModal from './AddCompanyUserModal';
import UpdateCompanyUserModal from './UpdateCompanyUserModal';
import { canManageCompanyUsers } from '../../auth/permissions';
import { useAuth } from '../../auth/AuthContext';
import type { CompanyUser, CompanyUserRole } from '../../api/types';
import { useI18n } from '../../i18n';

const ROLES: CompanyUserRole[] = ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'];

type MemberTab = 'active' | 'pending' | 'inactive' | 'deactivated' | 'all';

export default function CompanyUsersPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.companyUsersPage.pageTitle}
      pageSubtitle={t.companyUsersPage.pageSubtitle}
      activePath="/company-users"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <CompanyUsersContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface CompanyUsersContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function CompanyUsersContent({ selectedCompanyId, companiesLoading, userRole }: CompanyUsersContentProps) {
  const { t } = useI18n();
  const toast = useToast();
  const { user: authUser } = useAuth();

  const searchId = useId();
  const roleFilterId = useId();
  const membersPanelId = useId();
  const deleteConfirmId = useId();

  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [activeTab, setActiveTab] = useState<MemberTab>('active');

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedUserToEdit, setSelectedUserToEdit] = useState<CompanyUser | null>(null);
  const [removeAccessUser, setRemoveAccessUser] = useState<CompanyUser | null>(null);
  const [deleteAccountUser, setDeleteAccountUser] = useState<CompanyUser | null>(null);
  const [cancelInviteUser, setCancelInviteUser] = useState<CompanyUser | null>(null);
  const [restoreAccessUser, setRestoreAccessUser] = useState<CompanyUser | null>(null);
  const [reactivateAccountUser, setReactivateAccountUser] = useState<CompanyUser | null>(null);
  const [confirmDeleteInput, setConfirmDeleteInput] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    users,
    total,
    isLoading,
    error,
    statusCode,
    fetchUsers,
    pageSize,
    inviteCompanyUser,
    updateCompanyUser,
    removeCompanyAccess,
    deactivateUserAccount,
    cancelInvitation,
    restoreCompanyAccess,
    reactivateUserAccount,
    isSubmitting,
    submitError,
    setSubmitError,
  } = useCompanyUsers({
    companyId: selectedCompanyId,
    skip,
  });

  useEffect(() => {
    if (selectedCompanyId) {
      fetchUsers();
    }
  }, [selectedCompanyId, skip, fetchUsers]);

  const isOnlyAdmin = useMemo(() => {
    return users.filter((u) => u.role === 'admin' && u.is_active).length <= 1;
  }, [users]);

  // Tab-based user categorisation and search
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // 1. Tab check
      if (activeTab === 'active') {
        if (u.is_invitation || !u.is_active || u.user_is_active === false) return false;
      } else if (activeTab === 'pending') {
        if (!u.is_invitation) return false;
      } else if (activeTab === 'inactive') {
        if (u.is_invitation || u.is_active || u.user_is_active === false) return false;
      } else if (activeTab === 'deactivated') {
        if (u.is_invitation || u.user_is_active !== false) return false;
      }

      // 2. Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = u.user_id.toString().includes(query);
        const matchesRole = u.role.toLowerCase().includes(query);
        const matchesEmail = u.user_email?.toLowerCase().includes(query) || false;
        const matchesName = u.user_full_name?.toLowerCase().includes(query) || false;
        if (!matchesId && !matchesRole && !matchesEmail && !matchesName) return false;
      }

      // 3. Role filter
      if (roleFilter && u.role !== roleFilter) {
        return false;
      }

      return true;
    });
  }, [users, activeTab, searchQuery, roleFilter]);

  const formatDateTime = (dateString: string | null | undefined): string => {
    if (!dateString) return '—';
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return '—';
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleOpenAddModal = () => {
    setSubmitError(null);
    setIsAddModalOpen(true);
  };

  const handleConfirmAdd = async (payload: { email: string; role: CompanyUserRole }) => {
    if (!selectedCompanyId) return;
    const response = await inviteCompanyUser({
      company_id: selectedCompanyId,
      email: payload.email,
      role: payload.role,
    });

    if (response) {
      if (response.status === 'added_existing') {
        setIsAddModalOpen(false);
        toast.success(t.companyUsersPage.userAdded);
        fetchUsers();
      } else if (response.status === 'invited' && response.invite_url) {
        // The dialog switches to a hand-off screen showing this link.
        return response.invite_url;
      }
    }
    return undefined;
  };

  const handleOpenEditModal = (user: CompanyUser) => {
    setSubmitError(null);
    setSelectedUserToEdit(user);
  };

  const handleConfirmEdit = async (role: CompanyUserRole, isActive: boolean) => {
    if (!selectedUserToEdit) return;
    const updated = await updateCompanyUser(selectedUserToEdit.id, { role, is_active: isActive });
    if (updated) {
      setSelectedUserToEdit(null);
      toast.success(t.companyUsersPage.userUpdated);
      fetchUsers();
    }
  };

  const handleConfirmRemoveAccess = async () => {
    if (!removeAccessUser) return;
    setActionError(null);
    const success = await removeCompanyAccess(removeAccessUser.id);
    if (success) {
      setRemoveAccessUser(null);
      toast.success(t.companyUsersPage.accessRemoved);
      fetchUsers();
    } else {
      setActionError(submitError || t.common.somethingWentWrong);
    }
  };

  const handleOpenDeleteAccount = (user: CompanyUser) => {
    setActionError(null);
    setConfirmDeleteInput('');
    setDeleteAccountUser(user);
  };

  const handleConfirmDeleteAccount = async () => {
    if (!deleteAccountUser || !selectedCompanyId) return;
    if (confirmDeleteInput !== 'DELETE') {
      setActionError(t.companyUsersPage.mustTypeDelete);
      return;
    }
    setActionError(null);
    const success = await deactivateUserAccount(deleteAccountUser.user_id, selectedCompanyId);
    if (success) {
      setDeleteAccountUser(null);
      setConfirmDeleteInput('');
      toast.success(t.companyUsersPage.accountDeleted);
      fetchUsers();
    } else {
      setActionError(submitError || t.common.somethingWentWrong);
    }
  };

  const handleConfirmCancelInvite = async () => {
    if (!cancelInviteUser) return;
    setActionError(null);
    const invitationId = Math.abs(cancelInviteUser.id);
    const success = await cancelInvitation(invitationId);
    if (success) {
      setCancelInviteUser(null);
      toast.success(t.companyUsersPage.inviteCancelled);
      fetchUsers();
    } else {
      setActionError(submitError || t.common.somethingWentWrong);
    }
  };

  const handleConfirmRestoreAccess = async () => {
    if (!restoreAccessUser) return;
    setActionError(null);
    const success = await restoreCompanyAccess(restoreAccessUser.id);
    if (success) {
      setRestoreAccessUser(null);
      toast.success(t.companyUsersPage.accessRestored);
      fetchUsers();
    } else {
      setActionError(submitError || t.common.somethingWentWrong);
    }
  };

  const handleConfirmReactivateAccount = async () => {
    if (!reactivateAccountUser || !selectedCompanyId) return;
    setActionError(null);
    const success = await reactivateUserAccount(reactivateAccountUser.user_id, selectedCompanyId);
    if (success) {
      setReactivateAccountUser(null);
      toast.success(t.companyUsersPage.accountReactivated);
      fetchUsers();
    } else {
      setActionError(submitError || t.common.somethingWentWrong);
    }
  };

  const openConfirm = (setter: (user: CompanyUser) => void) => (user: CompanyUser) => {
    setActionError(null);
    setter(user);
  };

  const displayName = (user: CompanyUser) =>
    user.user_full_name || user.user_email || `${t.common.user} #${user.user_id}`;

  /** Status combines an icon with a tone so it stays legible without colour. */
  const renderStatus = (user: CompanyUser) => {
    if (user.is_invitation) {
      return (
        <span className="badge tone-warning">
          <Clock aria-hidden className="h-3 w-3" />
          {t.companyUsersPage.pendingStatus}
        </span>
      );
    }
    if (user.user_is_active === false) {
      return (
        <span className="badge tone-danger">
          <Ban aria-hidden className="h-3 w-3" />
          {t.companyUsersPage.deactivatedUser}
        </span>
      );
    }
    if (user.is_active) {
      return (
        <span className="badge tone-success">
          <CheckCircle2 aria-hidden className="h-3 w-3" />
          {t.common.active}
        </span>
      );
    }
    return (
      <span className="badge tone-neutral">
        <XCircle aria-hidden className="h-3 w-3" />
        {t.common.inactive}
      </span>
    );
  };

  /**
   * The same action set drives the desktop rows and the mobile cards; on cards
   * the buttons stretch so they stay comfortable to tap.
   */
  const renderActions = (user: CompanyUser, layout: 'row' | 'card') => {
    if (!canManageCompanyUsers(userRole)) return null;

    const grow = layout === 'card' ? 'flex-1 justify-center' : '';
    const lockedLastAdmin = isOnlyAdmin && user.role === 'admin';

    return (
      <div className={`flex flex-wrap items-center gap-2 ${layout === 'row' ? 'justify-end' : ''}`}>
        {user.is_invitation && (
          <>
            <button
              type="button"
              onClick={() => toast.info(t.companyUsersPage.inviteLinkOnceOnly)}
              className={`btn btn-secondary btn-sm ${grow}`}
            >
              <Link2 aria-hidden className="h-3.5 w-3.5" />
              {t.companyUsersPage.copyInviteLink}
            </button>
            <button
              type="button"
              onClick={() => openConfirm(setCancelInviteUser)(user)}
              className={`btn btn-tone tone-danger btn-sm ${grow}`}
            >
              <XCircle aria-hidden className="h-3.5 w-3.5" />
              {t.companyUsersPage.cancelInvite}
            </button>
          </>
        )}

        {!user.is_invitation && (
          <>
            <button
              type="button"
              onClick={() => handleOpenEditModal(user)}
              className={`btn btn-secondary btn-sm ${grow}`}
            >
              <Pencil aria-hidden className="h-3.5 w-3.5" />
              {t.common.edit}
            </button>

            {user.is_active ? (
              <button
                type="button"
                onClick={() => openConfirm(setRemoveAccessUser)(user)}
                disabled={lockedLastAdmin}
                title={lockedLastAdmin ? t.companyUsersPage.cannotRemoveLastAdmin : undefined}
                className={`btn btn-tone tone-warning btn-sm ${grow}`}
              >
                <XCircle aria-hidden className="h-3.5 w-3.5" />
                {t.companyUsersPage.removeAccess}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => openConfirm(setRestoreAccessUser)(user)}
                className={`btn btn-tone tone-success btn-sm ${grow}`}
              >
                <RotateCcw aria-hidden className="h-3.5 w-3.5" />
                {t.companyUsersPage.restoreAccess}
              </button>
            )}

            {authUser?.is_superuser && user.user_is_active !== false && (
              <button
                type="button"
                onClick={() => handleOpenDeleteAccount(user)}
                className={`btn btn-danger-ghost btn-sm ${grow}`}
              >
                <Trash2 aria-hidden className="h-3.5 w-3.5" />
                {t.companyUsersPage.deleteAccount}
              </button>
            )}
          </>
        )}

        {authUser?.is_superuser && !user.is_invitation && user.user_is_active === false && (
          <button
            type="button"
            onClick={() => openConfirm(setReactivateAccountUser)(user)}
            className={`btn btn-tone tone-primary btn-sm ${grow}`}
          >
            <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
            {t.companyUsersPage.reactivateAccount}
          </button>
        )}
      </div>
    );
  };

  if (companiesLoading) {
    return <LoadingState />;
  }

  if (!selectedCompanyId) {
    return <EmptyState title={t.common.noCompanySelected} description={t.common.selectCompanyPrompt} />;
  }

  if (statusCode === 403) {
    return (
      <EmptyState
        icon={<Lock className="h-6 w-6 text-danger" />}
        title={t.settingsPage.accessDenied}
        description={t.companyUsersPage.accessDeniedDescription}
        action={<p className="text-xs text-subtle-foreground">{t.companyUsersPage.accessDeniedHint}</p>}
      />
    );
  }

  const tabs: { id: MemberTab; label: string }[] = [
    { id: 'active', label: t.companyUsersPage.activeUsers },
    { id: 'pending', label: t.companyUsersPage.pendingInvitations },
    { id: 'inactive', label: t.companyUsersPage.inactiveUsers },
    { id: 'deactivated', label: t.companyUsersPage.deactivatedUsers },
    { id: 'all', label: t.companyUsersPage.allUsers },
  ];

  return (
    <div className="space-y-5">
      <div className="filter-bar">
        <div className="min-w-[220px] flex-1">
          <label htmlFor={searchId} className="field-label">
            {t.common.search}
          </label>
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute start-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground"
            />
            <input
              id={searchId}
              type="search"
              placeholder={t.companyUsersPage.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input ps-9"
            />
          </div>
        </div>

        <div className="w-full sm:w-48">
          <label htmlFor={roleFilterId} className="field-label">
            {t.companyUsersPage.role}
          </label>
          <select
            id={roleFilterId}
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="select"
          >
            <option value="">{t.companyUsersPage.allRoles}</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t.companyUsersPage.roles[r]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button type="button" onClick={fetchUsers} className="btn btn-secondary btn-sm">
            <RefreshCw aria-hidden className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            {t.common.refresh}
          </button>

          {canManageCompanyUsers(userRole) && (
            <button type="button" onClick={handleOpenAddModal} className="btn btn-primary btn-sm">
              <UserPlus aria-hidden className="h-3.5 w-3.5" />
              {t.companyUsersPage.addUser}
            </button>
          )}
        </div>
      </div>

      <div
        role="tablist"
        aria-label={t.companyUsersPage.memberGroups}
        className="flex gap-1 overflow-x-auto border-b border-border"
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls={membersPanelId}
              onClick={() => setActiveTab(tab.id)}
              className={`-mb-px shrink-0 border-b-2 px-4 pb-2.5 pt-1 text-sm font-medium transition-colors ${
                isActive
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div id={membersPanelId} role="tabpanel">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchUsers} />
        ) : filteredUsers.length === 0 ? (
          <EmptyState
            icon={<Users className="h-6 w-6" />}
            title={t.companyUsersPage.noUsersTitle}
            description={
              searchQuery || roleFilter || activeTab !== 'active'
                ? t.common.noResults
                : t.companyUsersPage.noUsersDescription
            }
            action={
              canManageCompanyUsers(userRole) && !searchQuery && !roleFilter && activeTab === 'active' ? (
                <button type="button" onClick={handleOpenAddModal} className="btn btn-primary btn-sm">
                  <UserPlus aria-hidden className="h-3.5 w-3.5" />
                  {t.companyUsersPage.addUser}
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="space-y-4">
            {/* Desktop table */}
            <div className="card hidden overflow-hidden lg:block">
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="sr-only">{t.companyUsersPage.pageTitle}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t.common.user}</th>
                      <th scope="col">{t.companyUsersPage.role}</th>
                      <th scope="col">{t.common.status}</th>
                      <th scope="col">{t.companyUsersPage.createdAt}</th>
                      <th scope="col">{t.companyUsersPage.updatedAt}</th>
                      <th scope="col" className="text-end">
                        {t.common.actions}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((user) => (
                      <tr key={user.id}>
                        <th scope="row" className="text-start align-middle font-normal">
                          <span className="block text-sm font-medium text-foreground">{displayName(user)}</span>
                          {user.user_full_name && user.user_email && (
                            <span className="block text-xs text-subtle-foreground">{user.user_email}</span>
                          )}
                        </th>
                        <td>
                          <CompanyUserRoleBadge role={user.role} />
                        </td>
                        <td>{renderStatus(user)}</td>
                        <td className="numeric whitespace-nowrap text-xs text-muted-foreground">
                          {formatDateTime(user.created_at)}
                        </td>
                        <td className="numeric whitespace-nowrap text-xs text-muted-foreground">
                          {formatDateTime(user.updated_at)}
                        </td>
                        <td className="text-end">{renderActions(user, 'row')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile cards */}
            <div className="space-y-3 lg:hidden">
              {filteredUsers.map((user) => (
                <div key={user.id} className="card space-y-3 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">{displayName(user)}</p>
                      {user.user_full_name && user.user_email && (
                        <p className="truncate text-xs text-subtle-foreground">{user.user_email}</p>
                      )}
                    </div>
                    {renderStatus(user)}
                  </div>

                  <dl className="grid grid-cols-2 gap-x-3 gap-y-3 border-t border-border-subtle pt-3">
                    <div>
                      <dt className="overline">{t.companyUsersPage.role}</dt>
                      <dd className="mt-1">
                        <CompanyUserRoleBadge role={user.role} />
                      </dd>
                    </div>
                    <div>
                      <dt className="overline">{t.companyUsersPage.createdAt}</dt>
                      <dd className="numeric mt-1 text-xs text-muted-foreground">
                        {formatDateTime(user.created_at)}
                      </dd>
                    </div>
                    <div>
                      <dt className="overline">{t.companyUsersPage.updatedAt}</dt>
                      <dd className="numeric mt-1 text-xs text-muted-foreground">
                        {formatDateTime(user.updated_at)}
                      </dd>
                    </div>
                  </dl>

                  {canManageCompanyUsers(userRole) && (
                    <div className="border-t border-border-subtle pt-3">{renderActions(user, 'card')}</div>
                  )}
                </div>
              ))}
            </div>

            <PaginationControls
              skip={skip}
              limit={pageSize}
              total={total}
              onPrev={() => setSkip((prev) => Math.max(0, prev - pageSize))}
              onNext={() => setSkip((prev) => prev + pageSize)}
              entityName={t.companyUsersPage.usersEntity}
            />
          </div>
        )}
      </div>

      <AddCompanyUserModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onConfirm={handleConfirmAdd}
        isSubmitting={isSubmitting}
        error={submitError}
        setError={setSubmitError}
      />

      <UpdateCompanyUserModal
        isOpen={selectedUserToEdit !== null}
        onClose={() => setSelectedUserToEdit(null)}
        user={selectedUserToEdit}
        onConfirm={handleConfirmEdit}
        isSubmitting={isSubmitting}
        error={submitError}
        setError={setSubmitError}
        isOnlyAdmin={isOnlyAdmin}
        currentUserId={authUser?.id}
      />

      <ConfirmActionModal
        isOpen={removeAccessUser !== null}
        onClose={() => {
          setRemoveAccessUser(null);
          setActionError(null);
        }}
        onConfirm={handleConfirmRemoveAccess}
        title={t.companyUsersPage.removeAccess}
        message={t.companyUsersPage.removeAccessConfirm}
        subject={removeAccessUser ? displayName(removeAccessUser) : null}
        tone="tone-warning"
        icon={<XCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />}
        confirmClassName="btn btn-tone tone-warning btn-sm"
        error={actionError}
        isSubmitting={isSubmitting}
      />

      <ConfirmActionModal
        isOpen={restoreAccessUser !== null}
        onClose={() => {
          setRestoreAccessUser(null);
          setActionError(null);
        }}
        onConfirm={handleConfirmRestoreAccess}
        title={t.companyUsersPage.restoreAccess}
        message={t.companyUsersPage.confirmRestoreAccess}
        subject={restoreAccessUser ? displayName(restoreAccessUser) : null}
        tone="tone-success"
        icon={<RotateCcw aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />}
        confirmClassName="btn btn-tone tone-success btn-sm"
        error={actionError}
        isSubmitting={isSubmitting}
      />

      <ConfirmActionModal
        isOpen={cancelInviteUser !== null}
        onClose={() => {
          setCancelInviteUser(null);
          setActionError(null);
        }}
        onConfirm={handleConfirmCancelInvite}
        title={t.companyUsersPage.cancelInvite}
        message={t.companyUsersPage.confirmCancelInvite}
        subject={cancelInviteUser ? displayName(cancelInviteUser) : null}
        tone="tone-danger"
        icon={<XCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />}
        confirmClassName="btn btn-danger btn-sm"
        error={actionError}
        isSubmitting={isSubmitting}
      />

      <ConfirmActionModal
        isOpen={!!authUser?.is_superuser && reactivateAccountUser !== null}
        onClose={() => {
          setReactivateAccountUser(null);
          setActionError(null);
        }}
        onConfirm={handleConfirmReactivateAccount}
        title={t.companyUsersPage.reactivateAccount}
        message={t.companyUsersPage.confirmReactivateAccount}
        subject={reactivateAccountUser ? displayName(reactivateAccountUser) : null}
        tone="tone-primary"
        icon={<CheckCircle2 aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />}
        confirmClassName="btn btn-primary btn-sm"
        error={actionError}
        isSubmitting={isSubmitting}
      />

      <ConfirmActionModal
        isOpen={!!authUser?.is_superuser && deleteAccountUser !== null}
        onClose={() => {
          setDeleteAccountUser(null);
          setConfirmDeleteInput('');
          setActionError(null);
        }}
        onConfirm={handleConfirmDeleteAccount}
        title={t.companyUsersPage.deleteAccount}
        description={t.companyUsersPage.dangerZone}
        message={t.companyUsersPage.deleteAccountConfirm}
        subject={deleteAccountUser ? displayName(deleteAccountUser) : null}
        tone="tone-danger"
        icon={<Trash2 aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />}
        confirmLabel={t.companyUsersPage.deactivateAccount}
        confirmClassName="btn btn-danger btn-sm"
        confirmDisabled={confirmDeleteInput !== 'DELETE'}
        error={actionError}
        isSubmitting={isSubmitting}
      >
        <div>
          <label htmlFor={deleteConfirmId} className="field-label">
            {t.companyUsersPage.typeDeleteToConfirm}
          </label>
          <input
            id={deleteConfirmId}
            type="text"
            autoComplete="off"
            placeholder="DELETE"
            value={confirmDeleteInput}
            onChange={(e) => setConfirmDeleteInput(e.target.value)}
            className="input"
          />
        </div>
      </ConfirmActionModal>
    </div>
  );
}

interface ConfirmActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  /** Optional line under the title, used to flag irreversible actions. */
  description?: string;
  message: string;
  /** Name of the member the action applies to, so the wrong row is obvious. */
  subject: string | null;
  tone: string;
  icon: ReactNode;
  confirmLabel?: string;
  confirmClassName: string;
  confirmDisabled?: boolean;
  error: string | null;
  isSubmitting: boolean;
  children?: ReactNode;
}

/** Shared shape for the five member-management confirmations on this page. */
function ConfirmActionModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  message,
  subject,
  tone,
  icon,
  confirmLabel,
  confirmClassName,
  confirmDisabled = false,
  error,
  isSubmitting,
  children,
}: ConfirmActionModalProps) {
  const { t } = useI18n();

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      description={description}
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
            disabled={isSubmitting || confirmDisabled}
            className={confirmClassName}
          >
            {isSubmitting ? t.common.loading : (confirmLabel ?? t.common.confirm)}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className={`callout ${tone}`}>
          {icon}
          <p className="min-w-0 flex-1 text-sm">{message}</p>
        </div>

        {subject && (
          <div className="rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3">
            <dl className="flex items-baseline justify-between gap-4 text-xs">
              <dt className="text-subtle-foreground">{t.common.user}</dt>
              <dd className="min-w-0 truncate text-end font-medium text-foreground">{subject}</dd>
            </dl>
          </div>
        )}

        {children}
      </div>
    </Modal>
  );
}
