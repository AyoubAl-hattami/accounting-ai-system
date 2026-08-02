import { useState, useEffect, useId } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertCircle, ArrowRight, CheckCircle2, Loader2, UserPlus } from 'lucide-react';
import apiClient from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import { ThemeToggleButton } from '../../components/ui/ThemeToggle';
import CompanyUserRoleBadge from './CompanyUserRoleBadge';
import type { CompanyUserInvitationValidateResponse } from '../../api/types';

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();
  const { user: authUser } = useAuth();
  const { t } = useI18n();

  const errorId = useId();
  const emailId = useId();
  const fullNameId = useId();
  const passwordId = useId();
  const confirmPasswordId = useId();

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
      setError(t.companyUsersPage.invalidInvitation);
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
        setError(detail || t.companyUsersPage.invalidInvitation);
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
        setError(t.companyUsersPage.passwordMismatch);
        return;
      }
      if (password.length < 8) {
        setError(t.companyUsersPage.passwordTooShort);
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
      setError(detail || t.companyUsersPage.acceptFailed);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLoginRedirect = () => {
    navigate(`/login?redirect=/accept-invite?token=${token}`);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-background p-4">
        <Loader2 aria-hidden className="h-5 w-5 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">{t.companyUsersPage.validatingInvite}</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="flex justify-end p-4">
        <ThemeToggleButton />
      </div>

      <div className="flex flex-1 items-center justify-center px-4 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="w-full max-w-sm"
        >
          {success ? (
            <div className="card p-7 text-center">
              <span className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl border border-success-border bg-success-soft">
                <CheckCircle2 aria-hidden className="h-6 w-6 text-success" />
              </span>
              <h1 className="text-lg font-semibold text-foreground">
                {t.companyUsersPage.invitationAccepted}
              </h1>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {t.companyUsersPage.joinedSuccessfully}
              </p>
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="btn btn-primary btn-block mt-6"
              >
                {t.companyUsersPage.goToLogin}
                <ArrowRight aria-hidden className="h-4 w-4 rtl:rotate-180" />
              </button>
            </div>
          ) : (
            <>
              <div className="mb-8 text-center">
                <span className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary-solid text-primary-foreground shadow-md">
                  <UserPlus aria-hidden className="h-6 w-6" />
                </span>
                <h1 className="text-xl font-semibold tracking-tight text-foreground">
                  {t.companyUsersPage.acceptInvite}
                </h1>
                {inviteData && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t.companyUsersPage.invitedDescription}
                  </p>
                )}
              </div>

              <div className="card p-7">
                {error && (
                  <div role="alert" id={errorId} className="callout tone-danger mb-6">
                    <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                    <p className="min-w-0 flex-1 text-sm">{error}</p>
                  </div>
                )}

                {inviteData && (
                  <>
                    <dl className="mb-6 space-y-2.5 rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3 text-sm">
                      <div className="flex items-baseline justify-between gap-4">
                        <dt className="text-xs text-subtle-foreground">
                          {t.companyUsersPage.companyLabel}
                        </dt>
                        <dd className="min-w-0 truncate text-end font-medium text-foreground">
                          {inviteData.company_name}
                        </dd>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <dt className="text-xs text-subtle-foreground">{t.companyUsersPage.role}</dt>
                        <dd>
                          <CompanyUserRoleBadge role={inviteData.role} />
                        </dd>
                      </div>
                    </dl>

                    <form onSubmit={handleSubmit} className="space-y-5">
                      <div>
                        <label htmlFor={emailId} className="field-label">
                          {t.companyUsersPage.inviteEmail}
                        </label>
                        <input
                          id={emailId}
                          type="email"
                          value={inviteData.email}
                          disabled
                          readOnly
                          className="input"
                        />
                      </div>

                      {!inviteData.user_exists ? (
                        <>
                          <div>
                            <label htmlFor={fullNameId} className="field-label">
                              {t.companyUsersPage.fullName}
                            </label>
                            <input
                              id={fullNameId}
                              type="text"
                              required
                              autoComplete="name"
                              value={fullName}
                              onChange={(e) => setFullName(e.target.value)}
                              className="input"
                            />
                          </div>

                          <div>
                            <label htmlFor={passwordId} className="field-label">
                              {t.companyUsersPage.setPassword}
                            </label>
                            <input
                              id={passwordId}
                              type="password"
                              required
                              minLength={8}
                              autoComplete="new-password"
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              aria-describedby={error ? errorId : undefined}
                              className="input"
                            />
                            <p className="field-hint">{t.companyUsersPage.passwordTooShort}</p>
                          </div>

                          <div>
                            <label htmlFor={confirmPasswordId} className="field-label">
                              {t.companyUsersPage.confirmPassword}
                            </label>
                            <input
                              id={confirmPasswordId}
                              type="password"
                              required
                              autoComplete="new-password"
                              value={confirmPassword}
                              onChange={(e) => setConfirmPassword(e.target.value)}
                              aria-describedby={error ? errorId : undefined}
                              className="input"
                            />
                          </div>

                          <button type="submit" disabled={isSubmitting} className="btn btn-primary btn-block">
                            {isSubmitting && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                            {isSubmitting ? t.companyUsersPage.accepting : t.companyUsersPage.acceptInvite}
                          </button>
                        </>
                      ) : (
                        <div className="space-y-4 rounded-lg border border-border-subtle bg-surface-muted p-4">
                          <p className="text-sm text-muted-foreground">
                            {authUser
                              ? t.companyUsersPage.readyToAccept
                              : t.companyUsersPage.accountExists}
                          </p>
                          {authUser ? (
                            <button
                              type="submit"
                              disabled={isSubmitting}
                              className="btn btn-primary btn-block"
                            >
                              {isSubmitting && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                              {isSubmitting
                                ? t.companyUsersPage.accepting
                                : t.companyUsersPage.acceptInvite}
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={handleLoginRedirect}
                              className="btn btn-primary btn-block"
                            >
                              {t.companyUsersPage.logInToAccept}
                            </button>
                          )}
                        </div>
                      )}
                    </form>
                  </>
                )}
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
