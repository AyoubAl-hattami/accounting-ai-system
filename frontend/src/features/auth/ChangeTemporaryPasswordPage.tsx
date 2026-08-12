import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertCircle, Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import { ThemeToggleButton } from '../../components/ui/ThemeToggle';
import { defaultAuthenticatedRoute } from '../../auth/defaultRoute';

/**
 * The screen a handed-over account is locked to until it replaces its password.
 *
 * Deliberately rendered outside the application shell: the account can reach
 * nothing behind that shell yet, so a sidebar full of links that all bounce back
 * here would be a menu of dead ends.
 */
export default function ChangeTemporaryPasswordPage() {
  const { user, logout, refreshUser } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const copy = t.changePassword;

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = (): string => {
    if (newPassword !== confirmPassword) return copy.mismatch;
    if (newPassword === currentPassword) return copy.sameAsCurrent;
    if (
      newPassword.length < 8 ||
      !/[a-z]/.test(newPassword) ||
      !/[A-Z]/.test(newPassword) ||
      !/[0-9]/.test(newPassword)
    ) {
      return copy.tooWeak;
    }
    return '';
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const localError = validate();
    if (localError) {
      setError(localError);
      return;
    }

    setError('');
    setIsSubmitting(true);

    try {
      await apiClient.post('/auth/change-temporary-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      await refreshUser();
      navigate(defaultAuthenticatedRoute({ is_superuser: Boolean(user?.is_superuser) }), {
        replace: true,
      });
    } catch (err: unknown) {
      setError(resolveError(err, copy));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignOut = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-primary-solid opacity-[0.18] blur-[120px] motion-safe:animate-aurora" />
        <div
          className="absolute -right-32 top-10 h-[30rem] w-[30rem] rounded-full bg-violet opacity-[0.16] blur-[120px] motion-safe:animate-aurora"
          style={{ animationDelay: '-5s' }}
        />
      </div>

      <div className="flex justify-end p-4">
        <ThemeToggleButton />
      </div>

      <div className="flex flex-1 items-center justify-center px-4 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          <div className="mb-8 text-center">
            <span className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-brand text-white shadow-[0_18px_40px_-12px_var(--primary-glow)]">
              <ShieldCheck className="h-7 w-7" />
            </span>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{copy.description}</p>
          </div>

          <div className="glass rounded-xl border p-7 shadow-floating">
            {user && (
              <p className="mb-6 truncate text-sm text-muted-foreground" title={user.email}>
                {user.email}
              </p>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  role="alert"
                  id="change-password-error"
                  className="callout tone-danger"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}

              <div>
                <label htmlFor="current-password" className="field-label">
                  {copy.currentPasswordLabel}
                </label>
                <input
                  id="current-password"
                  type={showPasswords ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  placeholder={copy.currentPasswordPlaceholder}
                  required
                  autoComplete="current-password"
                  aria-describedby={error ? 'change-password-error' : undefined}
                  className="input"
                />
              </div>

              <div>
                <label htmlFor="new-password" className="field-label">
                  {copy.newPasswordLabel}
                </label>
                <div className="relative">
                  <input
                    id="new-password"
                    type={showPasswords ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    placeholder={copy.newPasswordPlaceholder}
                    required
                    autoComplete="new-password"
                    aria-describedby="new-password-requirements"
                    className="input pe-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswords(!showPasswords)}
                    aria-label={showPasswords ? t.login.hidePassword : t.login.showPassword}
                    aria-pressed={showPasswords}
                    className="absolute end-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-subtle-foreground transition-colors hover:bg-surface-muted hover:text-foreground"
                  >
                    {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <p id="new-password-requirements" className="mt-1.5 text-xs text-subtle-foreground">
                  {copy.requirements}
                </p>
              </div>

              <div>
                <label htmlFor="confirm-password" className="field-label">
                  {copy.confirmPasswordLabel}
                </label>
                <input
                  id="confirm-password"
                  type={showPasswords ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder={copy.confirmPasswordPlaceholder}
                  required
                  autoComplete="new-password"
                  className="input"
                />
              </div>

              <button type="submit" disabled={isSubmitting} className="btn btn-primary btn-block btn-lg">
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {isSubmitting ? copy.submitting : copy.submit}
              </button>
            </form>
          </div>

          <div className="mt-6 text-center">
            <button type="button" onClick={handleSignOut} className="btn btn-ghost btn-sm">
              {copy.signOut}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

/** Maps the backend refusal onto localized copy, never onto raw response JSON. */
function resolveError(err: unknown, copy: { currentIncorrect: string; sameAsCurrent: string; genericError: string; networkError: string }): string {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return copy.networkError;
  }

  const status = (err as { response?: { status?: number } }).response?.status;

  if (status === 400) return copy.currentIncorrect;
  if (status === 422) return copy.sameAsCurrent;

  return copy.genericError;
}
