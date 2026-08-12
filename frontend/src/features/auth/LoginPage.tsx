import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertCircle, Eye, EyeOff, Loader2, Scale } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useI18n } from '../../i18n';
import { ThemeToggleButton } from '../../components/ui/ThemeToggle';
import { defaultAuthenticatedRoute } from '../../auth/defaultRoute';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const signedIn = await login(email, password);
      navigate(
        signedIn.must_change_password
          ? '/auth/change-temporary-password'
          : defaultAuthenticatedRoute(signedIn),
        { replace: true },
      );
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        setError(axiosError.response?.data?.detail || t.login.invalidCredentials);
      } else {
        setError(t.login.networkError);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      {/* Decorative light field. Three slow-drifting blobs read as depth behind
          the glass card; they are purely presentational. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-primary-solid opacity-[0.18] blur-[120px] motion-safe:animate-aurora" />
        <div
          className="absolute -right-32 top-10 h-[30rem] w-[30rem] rounded-full bg-violet opacity-[0.16] blur-[120px] motion-safe:animate-aurora"
          style={{ animationDelay: '-5s' }}
        />
        <div
          className="absolute bottom-[-14rem] left-1/3 h-[28rem] w-[28rem] rounded-full bg-info opacity-[0.14] blur-[120px] motion-safe:animate-aurora"
          style={{ animationDelay: '-9s' }}
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
              <Scale className="h-7 w-7" />
            </span>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{t.login.title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">{t.login.subtitle}</p>
          </div>

          <div className="glass rounded-xl border p-7 shadow-floating">
            <div className="mb-6">
              <h2 className="text-base font-semibold text-foreground">{t.login.welcomeBack}</h2>
              <p className="mt-0.5 text-sm text-muted-foreground">{t.login.signInPrompt}</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  role="alert"
                  id="login-error"
                  className="callout tone-danger"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}

              <div>
                <label htmlFor="email" className="field-label">
                  {t.login.emailLabel}
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t.login.emailPlaceholder}
                  required
                  autoComplete="email"
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? 'login-error' : undefined}
                  className={`input ${error ? 'input-invalid' : ''}`}
                />
              </div>

              <div>
                <label htmlFor="password" className="field-label">
                  {t.login.passwordLabel}
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t.login.passwordPlaceholder}
                    required
                    autoComplete="current-password"
                    aria-invalid={error ? true : undefined}
                    aria-describedby={error ? 'login-error' : undefined}
                    className={`input pe-11 ${error ? 'input-invalid' : ''}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? t.login.hidePassword : t.login.showPassword}
                    aria-pressed={showPassword}
                    className="absolute end-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-subtle-foreground transition-colors hover:bg-surface-muted hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn btn-primary btn-block btn-lg"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {isLoading ? t.login.signingIn : t.login.signIn}
              </button>
            </form>
          </div>

          <p className="mt-6 text-center text-xs text-subtle-foreground">{t.login.footer}</p>
        </motion.div>
      </div>
    </div>
  );
}
