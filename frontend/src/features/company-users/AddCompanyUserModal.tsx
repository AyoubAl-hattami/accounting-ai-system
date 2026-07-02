import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, UserPlus } from 'lucide-react';
import type { CompanyUserRole } from '../../api/types';

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
  const [email, setEmail] = useState<string>('');
  const [role, setRole] = useState<CompanyUserRole>('viewer');
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Reset state when opening/closing
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
      setError('Email is required.');
      return;
    }
    const result = await onConfirm({
      email: email.trim(),
      role,
    });
    
    if (typeof result === 'string') {
      const fullUrl = window.location.origin + result;
      setInviteLink(fullUrl);
    }
  };
  
  const handleCopy = () => {
    if (inviteLink) {
      navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
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
                <UserPlus className="w-5 h-5 text-indigo-400" />
                Add Company User
              </h3>
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-white/[0.04] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {inviteLink ? (
              <div className="px-6 py-6 space-y-6">
                <div className="flex flex-col items-center justify-center space-y-3">
                  <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                    <UserPlus className="w-6 h-6 text-green-400" />
                  </div>
                  <h4 className="text-white font-semibold text-center">Invitation Created</h4>
                  <p className="text-gray-400 text-sm text-center">
                    Share this link with {email} so they can set up their account and join the company.
                  </p>
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-gray-400 block">Invite Link</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={inviteLink}
                      className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-gray-300 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleCopy}
                      className="px-4 py-2.5 bg-white/[0.05] hover:bg-white/[0.1] text-white text-sm font-medium rounded-xl border border-white/[0.06] transition-colors"
                    >
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
                
                <div className="flex justify-end pt-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl transition-colors"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                {/* Content */}
                <div className="px-6 py-6 space-y-4">
                  {/* Email Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400 block">
                      Email Address <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="user@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none focus:ring-0 transition-all"
                    />
                  </div>

                  {/* Role Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400 block">
                      Company Role <span className="text-red-400">*</span>
                    </label>
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value as CompanyUserRole)}
                      className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition-all cursor-pointer"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r} className="bg-slate-950 text-white">
                          {r.charAt(0).toUpperCase() + r.slice(1)}
                        </option>
                      ))}
                    </select>
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
                    {isSubmitting ? <span>Sending Invite...</span> : <span>Send Invite</span>}
                  </button>
                </div>
              </form>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
