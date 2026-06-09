import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, UserPlus, Edit2, Lock, RefreshCw, Calendar, User, CheckCircle, XCircle } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import PaginationControls from '../../components/ui/PaginationControls';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useCompanyUsers } from './useCompanyUsers';
import CompanyUserRoleBadge from './CompanyUserRoleBadge';
import AddCompanyUserModal from './AddCompanyUserModal';
import UpdateCompanyUserModal from './UpdateCompanyUserModal';
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
      {({ selectedCompanyId, companiesLoading }) => (
        <CompanyUsersContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface CompanyUsersContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function CompanyUsersContent({ selectedCompanyId, companiesLoading }: CompanyUsersContentProps) {
  const { t } = useI18n();
  const [skip, setSkip] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedUserToEdit, setSelectedUserToEdit] = useState<CompanyUser | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const {
    users,
    total,
    isLoading,
    error,
    statusCode,
    fetchUsers,
    pageSize,
    addCompanyUser,
    updateCompanyUser,
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

  // Client-side search and filters
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // Search query filter (matches user ID or role)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = u.user_id.toString().includes(query);
        const matchesRole = u.role.toLowerCase().includes(query);
        if (!matchesId && !matchesRole) return false;
      }

      // Role filter
      if (roleFilter && u.role !== roleFilter) {
        return false;
      }

      // Active status filter
      if (activeFilter) {
        const wantsActive = activeFilter === 'active';
        if (u.is_active !== wantsActive) {
          return false;
        }
      }

      return true;
    });
  }, [users, searchQuery, roleFilter, activeFilter]);

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

  const handleConfirmAdd = async (payload: { user_id: number; role: CompanyUserRole; is_active: boolean }) => {
    if (!selectedCompanyId) return;
    const added = await addCompanyUser({
      company_id: selectedCompanyId,
      ...payload,
    });
    if (added) {
      setIsAddModalOpen(false);
      setSuccessToast(`Added user #${payload.user_id} successfully.`);
      fetchUsers();
    }
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

          {/* Active status dropdown */}
          <div className="relative w-full sm:w-44">
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
              className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] py-2.5 pl-3 pr-8 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all appearance-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-white">{t.companyUsersPage.allStatuses}</option>
              <option value="active" className="bg-slate-900 text-white">{t.common.active}</option>
              <option value="inactive" className="bg-slate-900 text-white">{t.common.inactive}</option>
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
          <button
            onClick={handleOpenAddModal}
            className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-500/25 active:scale-[0.98] transition-all"
          >
            <UserPlus className="w-4 h-4" />
            {t.companyUsersPage.addUser}
          </button>
        </div>
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
            searchQuery || roleFilter || activeFilter
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
                    <th className="py-4 px-6 text-xs font-semibold uppercase tracking-wider text-gray-400">{t.companyUsersPage.userId}</th>
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
                        <td className="py-4 px-6 text-sm font-semibold font-mono text-white whitespace-nowrap">
                          #{user.user_id}
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          <CompanyUserRoleBadge role={user.role} />
                        </td>
                        <td className="py-4 px-6 whitespace-nowrap">
                          {user.is_active ? (
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
                          <button
                            onClick={() => handleOpenEditModal(user)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-white/[0.06] hover:border-white/[0.12] text-xs font-medium text-gray-300 hover:text-white bg-white/[0.02] hover:bg-white/[0.04] transition-all"
                          >
                            <Edit2 className="w-3 h-3" />
                            {t.common.edit}
                          </button>
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
                    <span className="text-sm font-semibold font-mono text-white flex items-center gap-1.5">
                      <User className="w-4 h-4 text-indigo-400 shrink-0" />
                      User #{user.user_id}
                    </span>
                    <button
                      onClick={() => handleOpenEditModal(user)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/[0.06] hover:border-white/[0.12] text-xs font-medium text-gray-300 hover:text-white bg-white/[0.02] transition-colors"
                    >
                      <Edit2 className="w-3 h-3" />
                      {t.common.edit}
                    </button>
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
                        {user.is_active ? (
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
      />
    </div>
  );
}
