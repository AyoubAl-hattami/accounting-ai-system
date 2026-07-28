import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, UserPlus, Edit2, Lock, RefreshCw, Calendar, User, CheckCircle, XCircle, Trash2 } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useCompanyUsers } from './useCompanyUsers';
import CompanyUserRoleBadge from './CompanyUserRoleBadge';
import AddCompanyUserModal from './AddCompanyUserModal';
import UpdateCompanyUserModal from './UpdateCompanyUserModal';
import { canManageCompanyUsers } from '../../auth/permissions';
import { useAuth } from '../../auth/AuthContext';
import type { CompanyUser, CompanyUserRole } from '../../api/types';
import { useI18n } from '../../i18n';

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
  const { user: authUser } = useAuth();
  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'active' | 'pending' | 'inactive' | 'deactivated' | 'all'>('active');

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
  const [successToast, setSuccessToast] = useState<string | null>(null);

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

  // Toast effect
  useEffect(() => {
    if (successToast) {
      const timer = setTimeout(() => setSuccessToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successToast]);

  const ROLES: CompanyUserRole[] = ['admin', 'accountant', 'reviewer', 'approver', 'auditor', 'viewer'];

  const isOnlyAdmin = useMemo(() => {
    return users.filter(u => u.role === 'admin' && u.is_active).length <= 1;
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

  const handlePrevPage = () => {
    setSkip((prev) => Math.max(0, prev - pageSize));
  };

  const handleNextPage = () => {
    setSkip((prev) => prev + pageSize);
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
        setSuccessToast(`Added ${payload.email} successfully.`);
        fetchUsers();
      } else if (response.status === 'invited' && response.invite_url) {
        // We will let the modal handle showing the invite URL, 
        // but for now we can keep the modal open and pass the invite URL to it.
        // Let's modify the AddCompanyUserModal to display the link instead of closing immediately.
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
      setSuccessToast(`Updated user #${selectedUserToEdit.user_id} successfully.`);
      fetchUsers();
    }
  };

  const handleOpenRemoveAccess = (user: CompanyUser) => {
    setActionError(null);
    setRemoveAccessUser(user);
  };

  const handleConfirmRemoveAccess = async () => {
    if (!removeAccessUser) return;
    setActionError(null);
    const success = await removeCompanyAccess(removeAccessUser.id);
    if (success) {
      setRemoveAccessUser(null);
      setSuccessToast(t.companyUsersPage.accessRemoved);
      fetchUsers();
    } else {
      setActionError(submitError || 'An error occurred.');
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
      setActionError("Please type 'DELETE' to confirm.");
      return;
    }
    setActionError(null);
    const success = await deactivateUserAccount(deleteAccountUser.user_id, selectedCompanyId);
    if (success) {
      setDeleteAccountUser(null);
      setConfirmDeleteInput('');
      setSuccessToast(t.companyUsersPage.accountDeleted);
      fetchUsers();
    } else {
      setActionError(submitError || 'An error occurred.');
    }
  };

  const handleOpenCancelInvite = (user: CompanyUser) => {
    setActionError(null);
    setCancelInviteUser(user);
  };

  const handleConfirmCancelInvite = async () => {
    if (!cancelInviteUser) return;
    setActionError(null);
    const invitationId = Math.abs(cancelInviteUser.id);
    const success = await cancelInvitation(invitationId);
    if (success) {
      setCancelInviteUser(null);
      setSuccessToast(t.companyUsersPage.inviteCancelled);
      fetchUsers();
    } else {
      setActionError(submitError || 'An error occurred.');
    }
  };

  const handleOpenRestoreAccess = (user: CompanyUser) => {
    setActionError(null);
    setRestoreAccessUser(user);
  };

  const handleConfirmRestoreAccess = async () => {
    if (!restoreAccessUser) return;
    setActionError(null);
    const success = await restoreCompanyAccess(restoreAccessUser.id);
    if (success) {
      setRestoreAccessUser(null);
      setSuccessToast(t.companyUsersPage.accessRestored);
      fetchUsers();
    } else {
      setActionError(submitError || 'An error occurred.');
    }
  };

  const handleOpenReactivateAccount = (user: CompanyUser) => {
    setActionError(null);
    setReactivateAccountUser(user);
  };

  const handleConfirmReactivateAccount = async () => {
    if (!reactivateAccountUser || !selectedCompanyId) return;
    setActionError(null);
    const success = await reactivateUserAccount(reactivateAccountUser.user_id, selectedCompanyId);
    if (success) {
      setReactivateAccountUser(null);
      setSuccessToast(t.companyUsersPage.accountReactivated);
      fetchUsers();
    } else {
      setActionError(submitError || 'An error occurred.');
    }
  };

  if (companiesLoading) {
    return <LoadingState />;
  }

  if (!selectedCompanyId) {
    return (
      <EmptyState
        title={t.common.noCompanySelected}
        description={t.common.selectCompanyPrompt}
      />
    );
  }

  // Handle 403 Forbidden State Elegantly
  if (statusCode === 403) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-center py-20 px-4"
      >
        <div className="glass-panel p-8 max-w-md text-center border-red-500/10">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5 shadow-[0_0_15px_rgba(239,68,68,0.07)]">
            <Lock className="w-8 h-8 text-red-400 animate-pulse" />
          </div>
          <h3 className="text-white font-bold text-xl mb-3">{t.settingsPage.accessDenied}</h3>
          <p className="text-gray-400 text-sm leading-relaxed mb-6">
            You do not have permission to view this page. Access to company users list is strictly restricted to users with <span className="text-indigo-400 font-semibold">Admin</span> or <span className="text-indigo-400 font-semibold">Auditor</span> roles.
          </p>
          <div className="text-xs text-gray-500 border-t border-white/[0.06] pt-4">
            If you believe this is an error, please contact your administrator.
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success Toast Banner */}
      <AnimatePresence>
        {successToast && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="fixed top-20 right-6 z-50 bg-green-500 border border-green-600 text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-2.5 text-sm"
          >
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{successToast}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filters and Add User Bar */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          {/* Search bar */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder={t.companyUsersPage.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none focus:ring-0 transition-all duration-200"
            />
          </div>

          {/* Role filter dropdown */}
          <div className="relative w-full sm:w-48">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-3 pr-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">{t.companyUsersPage.allRoles}</option>
              {ROLES.map((r) => (
                <option key={r} value={r} className="bg-slate-900 text-white">
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
                <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
              </svg>
            </div>
          </div>

        </div>
 
        <div className="flex gap-2">
          <button
            onClick={fetchUsers}
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-gray-300 text-sm font-medium hover:bg-white/[0.08] hover:text-white transition-all duration-200"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          
          {/* Note: In backend creation requires "admin" role. Let's allow users to trigger it. If it fails, they will see backend error detail */}
          {canManageCompanyUsers(userRole) && (
            <button
              onClick={handleOpenAddModal}
              className="flex items-center justify-center gap-2 px-4.5 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-bold shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 hover:shadow-indigo-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 shrink-0"
            >
              <UserPlus className="w-4 h-4" />
              {t.companyUsersPage.addUser}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/[0.06] overflow-x-auto scrollbar-none gap-2">
        <button
          onClick={() => setActiveTab('active')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all shrink-0 ${activeTab === 'active' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          {t.companyUsersPage.activeUsers}
        </button>
        <button
          onClick={() => setActiveTab('pending')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all shrink-0 ${activeTab === 'pending' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          {t.companyUsersPage.pendingInvitations}
        </button>
        <button
          onClick={() => setActiveTab('inactive')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all shrink-0 ${activeTab === 'inactive' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          {t.companyUsersPage.inactiveUsers}
        </button>
        <button
          onClick={() => setActiveTab('deactivated')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all shrink-0 ${activeTab === 'deactivated' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          {t.companyUsersPage.deactivatedUsers}
        </button>
        <button
          onClick={() => setActiveTab('all')}
          className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-all shrink-0 ${activeTab === 'all' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
        >
          {t.companyUsersPage.allUsers}
        </button>
      </div>


      {/* Main Content Body */}
      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchUsers} />
      ) : filteredUsers.length === 0 ? (
        <EmptyState
          title={t.companyUsersPage.noUsersTitle}
          description={
            searchQuery || roleFilter || activeTab !== 'active'
              ? t.common.noResults
              : t.companyUsersPage.noUsersDescription
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-white/[0.01]">
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.common.user}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.companyUsersPage.role}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.common.status}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.companyUsersPage.createdAt}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.companyUsersPage.updatedAt}</th>
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400 text-right">{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  <AnimatePresence mode="popLayout">
                    {filteredUsers.map((user) => (
                      <motion.tr
                        key={user.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="hover:bg-white/[0.02] transition-colors duration-150"
                      >
                        <td className="py-4 px-6 whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="text-sm font-semibold text-white">
                              {user.user_full_name || user.user_email || `User #${user.user_id}`}
                            </span>
                            {user.user_full_name && user.user_email && (
                              <span className="text-xs text-gray-400 mt-0.5">{user.user_email}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <CompanyUserRoleBadge role={user.role} />
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          {user.is_invitation ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-yellow-500">
                              <span className="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
                              Pending
                            </span>
                          ) : user.user_is_active === false ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-400">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                              {t.companyUsersPage.deactivatedUser}
                            </span>
                          ) : user.is_active ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-400">
                              <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500">
                              <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                              {t.common.inactive}
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-400 whitespace-nowrap">
                          {formatDateTime(user.created_at)}
                        </td>
                        <td className="py-4 px-6 text-sm text-gray-400 whitespace-nowrap">
                          {formatDateTime(user.updated_at)}
                        </td>
                        <td className="py-4 px-6 text-sm text-right whitespace-nowrap">
                          {/* Note: updateCompanyUser requires "admin" role. Action will try and display errors if unauthorized */}
                          {canManageCompanyUsers(userRole) && (
                            <div className="flex items-center justify-end gap-2">
                              {user.is_invitation && (
                                <>
                                  <button
                                    onClick={() => {
                                      navigator.clipboard.writeText(`${window.location.origin}/accept-invite?token=dummy`);
                                      setSuccessToast("Invite link can only be copied immediately upon creation.");
                                    }}
                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/[0.06] hover:border-white/[0.12] text-xs font-medium text-gray-300 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] transition-all"
                                  >
                                    Copy Link
                                  </button>
                                  <button
                                    onClick={() => handleOpenCancelInvite(user)}
                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-red-500/10 hover:border-red-500/30 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/5 hover:bg-red-500/10 transition-all"
                                    title={t.companyUsersPage.cancelInvite}
                                  >
                                    <XCircle className="w-3 h-3" />
                                    {t.companyUsersPage.cancelInvite}
                                  </button>
                                </>
                              )}

                              {!user.is_invitation && (
                                <>
                                  <button
                                    onClick={() => handleOpenEditModal(user)}
                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/[0.06] hover:border-white/[0.12] text-xs font-medium text-gray-300 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] transition-all"
                                  >
                                    <Edit2 className="w-3 h-3" />
                                    {t.common.edit}
                                  </button>

                                  {user.is_active ? (
                                    <button
                                      onClick={() => handleOpenRemoveAccess(user)}
                                      disabled={isOnlyAdmin && user.role === 'admin'}
                                      className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-orange-500/10 hover:border-orange-500/30 text-xs font-medium text-orange-400 hover:text-orange-300 bg-orange-500/5 hover:bg-orange-500/10 transition-all ${isOnlyAdmin && user.role === 'admin' ? 'opacity-40 cursor-not-allowed' : ''}`}
                                      title={t.companyUsersPage.removeAccess}
                                    >
                                      <XCircle className="w-3 h-3" />
                                      {t.companyUsersPage.removeAccess}
                                    </button>
                                  ) : (
                                    <button
                                      onClick={() => handleOpenRestoreAccess(user)}
                                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-green-500/10 hover:border-green-500/30 text-xs font-medium text-green-400 hover:text-green-300 bg-green-500/5 hover:bg-green-500/10 transition-all"
                                      title={t.companyUsersPage.restoreAccess}
                                    >
                                      <RefreshCw className="w-3 h-3" />
                                      {t.companyUsersPage.restoreAccess}
                                    </button>
                                  )}

                                  {authUser?.is_superuser && user.user_is_active !== false && (
                                    <button
                                      onClick={() => handleOpenDeleteAccount(user)}
                                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-red-500/10 hover:border-red-500/30 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/5 hover:bg-red-500/10 transition-all"
                                      title={t.companyUsersPage.deleteAccount}
                                    >
                                      <Trash2 className="w-3 h-3" />
                                      {t.companyUsersPage.deleteAccount}
                                    </button>
                                  )}
                                </>
                              )}

                              {authUser?.is_superuser && !user.is_invitation && user.user_is_active === false && (
                                <button
                                  onClick={() => handleOpenReactivateAccount(user)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-indigo-500/10 hover:border-indigo-500/30 text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/5 hover:bg-indigo-500/10 transition-all"
                                  title={t.companyUsersPage.reactivateAccount}
                                >
                                  <CheckCircle className="w-3 h-3" />
                                  {t.companyUsersPage.reactivateAccount}
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Card View */}
          <div className="md:hidden space-y-3">
            <AnimatePresence mode="popLayout">
              {filteredUsers.map((user) => (
                <motion.div
                  key={user.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="glass-panel p-5 space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                    <span className="text-sm font-semibold text-white flex items-center gap-1.5 truncate">
                      <User className="w-4 h-4 text-indigo-400 shrink-0" />
                      {user.user_full_name || user.user_email || `User #${user.user_id}`}
                    </span>
                    {canManageCompanyUsers(userRole) && !user.is_invitation && (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleOpenEditModal(user)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/[0.06] hover:border-white/[0.12] text-xs font-medium text-gray-300 hover:text-white bg-white/[0.02] transition-colors"
                        >
                          <Edit2 className="w-3 h-3" />
                          {t.common.edit}
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-y-3 gap-x-2 text-sm pt-1">
                    <div>
                      <span className="text-xs text-gray-500 block">{t.companyUsersPage.role}</span>
                      <div className="mt-1">
                        <CompanyUserRoleBadge role={user.role} />
                      </div>
                    </div>

                    <div>
                      <span className="text-xs text-gray-500 block">{t.common.status}</span>
                      <div className="mt-1">
                        {user.is_invitation ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-yellow-500">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Pending
                          </span>
                        ) : user.user_is_active === false ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-400">
                            <CheckCircle className="w-3.5 h-3.5" />
                            {t.companyUsersPage.deactivatedUser}
                          </span>
                        ) : user.is_active ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-400">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500">
                            <XCircle className="w-3.5 h-3.5" />
                            {t.common.inactive}
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-xs text-gray-500 block">{t.companyUsersPage.createdAt}</span>
                      <span className="text-gray-300 font-medium text-xs mt-0.5 block flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        {formatDateTime(user.created_at)}
                      </span>
                    </div>

                    <div>
                      <span className="text-xs text-gray-500 block">{t.companyUsersPage.updatedAt}</span>
                      <span className="text-gray-300 font-medium text-xs mt-0.5 block flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        {formatDateTime(user.updated_at)}
                      </span>
                    </div>
                  </div>

                  {canManageCompanyUsers(userRole) && (
                    <div className="flex items-center gap-2 pt-2 border-t border-white/[0.04] flex-wrap">
                      {user.is_invitation && (
                        <>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(`${window.location.origin}/accept-invite?token=dummy`);
                              setSuccessToast("Invite link can only be copied immediately upon creation.");
                            }}
                            className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/[0.06] text-xs font-medium text-gray-300 bg-white/[0.02]"
                          >
                            Copy Link
                          </button>
                          <button
                            onClick={() => handleOpenCancelInvite(user)}
                            className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-red-500/10 text-xs font-medium text-red-400 bg-red-500/5"
                          >
                            <XCircle className="w-3 h-3" />
                            {t.companyUsersPage.cancelInvite}
                          </button>
                        </>
                      )}

                      {!user.is_invitation && (
                        <>
                          {user.is_active ? (
                            <button
                              onClick={() => handleOpenRemoveAccess(user)}
                              disabled={isOnlyAdmin && user.role === 'admin'}
                              className={`flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-orange-500/10 text-xs font-medium text-orange-400 bg-orange-500/5 ${isOnlyAdmin && user.role === 'admin' ? 'opacity-40 cursor-not-allowed border-orange-500/5' : ''}`}
                            >
                              <XCircle className="w-3 h-3" />
                              {t.companyUsersPage.removeAccess}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleOpenRestoreAccess(user)}
                              className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-green-500/10 text-xs font-medium text-green-400 bg-green-500/5"
                            >
                              <RefreshCw className="w-3 h-3" />
                              {t.companyUsersPage.restoreAccess}
                            </button>
                          )}

                          {authUser?.is_superuser && user.user_is_active !== false && (
                            <button
                              onClick={() => handleOpenDeleteAccount(user)}
                              className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-red-500/10 text-xs font-medium text-red-400 bg-red-500/5"
                            >
                              <Trash2 className="w-3 h-3" />
                              {t.companyUsersPage.deleteAccount}
                            </button>
                          )}
                        </>
                      )}

                      {authUser?.is_superuser && !user.is_invitation && user.user_is_active === false && (
                        <button
                          onClick={() => handleOpenReactivateAccount(user)}
                          className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded-lg border border-indigo-500/10 text-xs font-medium text-indigo-400 bg-indigo-500/5"
                        >
                          <CheckCircle className="w-3 h-3" />
                          {t.companyUsersPage.reactivateAccount}
                        </button>
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Pagination */}
          <PaginationControls
            skip={skip}
            limit={pageSize}
            total={total}
            onPrev={handlePrevPage}
            onNext={handleNextPage}
            entityName="users"
          />
        </div>
      )}

      {/* Add User Modal */}
      <AddCompanyUserModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onConfirm={handleConfirmAdd}
        isSubmitting={isSubmitting}
        error={submitError}
        setError={setSubmitError}
      />

      {/* Update User Modal */}
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

      {/* Remove Access Confirmation Modal */}
      <AnimatePresence>
        {removeAccessUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setRemoveAccessUser(null);
                setActionError(null);
              }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md bg-slate-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden p-6 space-y-4"
            >
              <div className="flex items-center gap-3 text-orange-400">
                <div className="p-2 rounded-xl bg-orange-500/10 border border-orange-500/20">
                  <XCircle className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">{t.companyUsersPage.removeAccess}</h3>
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed">
                {t.companyUsersPage.removeAccessConfirm}
              </p>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  {actionError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setRemoveAccessUser(null);
                    setActionError(null);
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmRemoveAccess}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold shadow-lg shadow-orange-500/25 transition-all"
                >
                  {isSubmitting ? t.common.loading : t.common.confirm}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Restore Access Confirmation Modal */}
      <AnimatePresence>
        {restoreAccessUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setRestoreAccessUser(null);
                setActionError(null);
              }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md bg-slate-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden p-6 space-y-4"
            >
              <div className="flex items-center gap-3 text-green-400">
                <div className="p-2 rounded-xl bg-green-500/10 border border-green-500/20">
                  <RefreshCw className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">{t.companyUsersPage.restoreAccess}</h3>
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed">
                {t.companyUsersPage.confirmRestoreAccess}
              </p>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  {actionError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setRestoreAccessUser(null);
                    setActionError(null);
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmRestoreAccess}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white text-xs font-semibold shadow-lg shadow-green-600/25 transition-all"
                >
                  {isSubmitting ? t.common.loading : t.common.confirm}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Cancel Invite Confirmation Modal */}
      <AnimatePresence>
        {cancelInviteUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setCancelInviteUser(null);
                setActionError(null);
              }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md bg-slate-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden p-6 space-y-4"
            >
              <div className="flex items-center gap-3 text-red-400">
                <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20">
                  <XCircle className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">{t.companyUsersPage.cancelInvite}</h3>
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed">
                {t.companyUsersPage.confirmCancelInvite}
              </p>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  {actionError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setCancelInviteUser(null);
                    setActionError(null);
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmCancelInvite}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-lg shadow-red-600/25 transition-all"
                >
                  {isSubmitting ? t.common.loading : t.common.confirm}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Reactivate Account Confirmation Modal */}
      <AnimatePresence>
        {authUser?.is_superuser && reactivateAccountUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setReactivateAccountUser(null);
                setActionError(null);
              }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md bg-slate-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden p-6 space-y-4"
            >
              <div className="flex items-center gap-3 text-indigo-400">
                <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">{t.companyUsersPage.reactivateAccount}</h3>
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed">
                {t.companyUsersPage.confirmReactivateAccount}
              </p>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  {actionError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setReactivateAccountUser(null);
                    setActionError(null);
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmReactivateAccount}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
                >
                  {isSubmitting ? t.common.loading : t.common.confirm}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Delete Account Confirmation Modal */}
      <AnimatePresence>
        {authUser?.is_superuser && deleteAccountUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                setDeleteAccountUser(null);
                setConfirmDeleteInput('');
                setActionError(null);
              }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-md bg-slate-900 border border-red-500/20 rounded-2xl shadow-2xl z-50 overflow-hidden p-6 space-y-4"
            >
              <div className="flex items-center gap-3 text-red-500">
                <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20">
                  <Trash2 className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-white">{t.companyUsersPage.deleteAccount}</h3>
              </div>

              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold text-center">
                {t.companyUsersPage.dangerZone.toUpperCase()}
              </div>
              
              <p className="text-sm text-gray-300 leading-relaxed">
                {t.companyUsersPage.deleteAccountConfirm}
              </p>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-gray-400 block">
                  {t.companyUsersPage.typeDeleteToConfirm}
                </label>
                <input
                  type="text"
                  placeholder="DELETE"
                  value={confirmDeleteInput}
                  onChange={(e) => setConfirmDeleteInput(e.target.value)}
                  className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2 text-sm text-white focus:border-red-500/50 focus:outline-none transition-all"
                />
              </div>

              {actionError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  {actionError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setDeleteAccountUser(null);
                    setConfirmDeleteInput('');
                    setActionError(null);
                  }}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDeleteAccount}
                  disabled={isSubmitting || confirmDeleteInput !== 'DELETE'}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-lg shadow-red-600/25 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  {isSubmitting ? t.common.loading : t.companyUsersPage.deactivateAccount}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
