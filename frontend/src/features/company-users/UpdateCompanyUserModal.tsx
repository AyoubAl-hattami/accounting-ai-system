import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Edit2 } from 'lucide-react';
import type { CompanyUser, CompanyUserRole } from '../../api/types';

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
    <AnimatePresence>
      {isOpen && user && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-md bg-slate-900 border border-white/[0.08] rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-indigo-400" />
                Update User Role / Status
              </h3>
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-white/[0.04] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Content */}
              <div className="px-6 py-6 space-y-4">
                {/* User ID (Read-only display) */}
                <div className="space-y-1">
                  <span className="text-xs font-semibold text-gray-500 block">User ID</span>
                  <span className="text-white text-sm font-semibold font-mono bg-white/[0.02] border border-white/[0.04] px-3 py-2 rounded-xl block">
                    #{user.user_id}
                  </span>
                </div>

                {preventDemoteOrRemove && (
                  <div className="p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs flex items-start gap-2">
                    <span className="flex-1">You are the only active admin in this company. You cannot demote or remove your own account.</span>
                  </div>
                )}

                {/* Role Field */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400 block">
                    Company Role <span className="text-red-400">*</span>
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as CompanyUserRole)}
                    disabled={preventDemoteOrRemove}
                    className={`w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all ${preventDemoteOrRemove ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r} className="bg-slate-950 text-white">
                        {r.charAt(0).toUpperCase() + r.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Active Field */}
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <div className="space-y-0.5">
                    <span className="text-xs font-semibold text-gray-300 block">Active Status</span>
                    <span className="text-[10px] text-gray-500">Allow this user to access the company</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={(e) => setIsActive(e.target.checked)}
                      disabled={preventDemoteOrRemove}
                      className="sr-only peer"
                    />
                    <div className={`w-11 h-6 bg-white/[0.08] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-gray-400 peer-checked:after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600 ${preventDemoteOrRemove ? 'opacity-50 cursor-not-allowed' : ''}`}></div>
                  </label>
                </div>

                {/* Error state */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2"
                  >
                    <span className="font-semibold">Error:</span>
                    <span className="flex-1">{error}</span>
                  </motion.div>
                )}
              </div>

              {/* Footer */}
              <div className="px-6 py-4 border-t border-white/[0.06] bg-slate-900/40 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4.5 py-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-500/25 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  {isSubmitting ? <span>Updating...</span> : <span>Save Changes</span>}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
