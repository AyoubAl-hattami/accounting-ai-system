import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus, Loader2, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react';
import apiClient from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import type { CompanyUserInvitationValidateResponse } from '../../api/types';

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { user: authUser } = useAuth();
  const { t } = useI18n();

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  const [inviteData, setInviteData] = useState<CompanyUserInvitationValidateResponse | null>(null);
  
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  useEffect(() => {
    if (!token) {
      setError(t.companyUsersPage.invalidInvitation || 'Invalid or missing invitation token.');
      setIsLoading(false);
      return;
    }

    const validateToken = async () => {
      try {
        const response = await apiClient.get<CompanyUserInvitationValidateResponse>(
          `/company-users/invitations/validate?token=${token}`
        );
        setInviteData(response.data);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        const detail = err.response?.data?.detail;
        setError(detail || t.companyUsersPage.invalidInvitation || 'Failed to validate invitation.');
      } finally {
        setIsLoading(false);
      }
    };

    validateToken();
  }, [token, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !inviteData) return;

    if (!inviteData.user_exists) {
      if (password !== confirmPassword) {
        setError(t.companyUsersPage.passwordMismatch || 'Passwords do not match.');
        return;
      }
      if (password.length < 8) {
        setError(t.companyUsersPage.passwordTooShort || 'Password must be at least 8 characters.');
        return;
      }
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await apiClient.post('/company-users/invitations/accept', {
        token,
        full_name: fullName,
        password: password,
      });
      setSuccess(true);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Failed to accept invitation.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLoginRedirect = () => {
    navigate(`/login?redirect=/accept-invite?token=${token}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center p-4">
        <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center p-4 relative overflow-hidden">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md glass-panel p-8 text-center"
        >
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">
            {t.companyUsersPage.invitationAccepted || 'Invitation Accepted!'}
          </h2>
          <p className="text-gray-400 text-sm mb-6">
            You have successfully joined the company.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {t.companyUsersPage.goToLogin || 'Go to Login'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-brand-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-violet-600/6 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="glass-panel p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-2xl shadow-brand-500/30 mb-4">
              <UserPlus className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {t.companyUsersPage.acceptInvite || 'Accept Invitation'}
            </h1>
            {inviteData && (
              <p className="text-gray-400 text-sm mt-2">
                You have been invited to join <span className="text-white font-semibold">{inviteData.company_name}</span> as <span className="text-white font-semibold">{inviteData.role}</span>.
              </p>
            )}
          </div>

          {error && (
            <div className="mb-6 flex items-start gap-2.5 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {inviteData && (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t.companyUsersPage.inviteEmail || 'Email'}
                </label>
                <input
                  type="email"
                  value={inviteData.email}
                  disabled
                  className="input-field opacity-60 cursor-not-allowed"
                />
              </div>

              {!inviteData.user_exists ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      {t.companyUsersPage.setPassword || 'Password'}
                    </label>
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      {t.companyUsersPage.confirmPassword || 'Confirm Password'}
                    </label>
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="input-field"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="btn-primary w-full mt-2"
                  >
                    {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : (t.companyUsersPage.acceptInvite || 'Accept Invitation')}
                  </button>
                </>
              ) : (
                <>
                  {!authUser ? (
                    <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl text-center space-y-4 mt-2">
                      <p className="text-sm text-gray-300">
                        You already have an account with this email.
                      </p>
                      <button
                        type="button"
                        onClick={handleLoginRedirect}
                        className="btn-primary w-full"
                      >
                        Log in to Accept
                      </button>
                    </div>
                  ) : (
                    <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl text-center space-y-4 mt-2">
                      <p className="text-sm text-gray-300">
                        You are currently logged in.
                      </p>
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="btn-primary w-full"
                      >
                        {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : (t.companyUsersPage.acceptInvite || 'Accept Invitation')}
                      </button>
                    </div>
                  )}
                </>
              )}
            </form>
          )}
        </div>
      </motion.div>
    </div>
  );
}
