import { useEffect, useId, useLayoutEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Info,
  Loader2,
  UserPlus,
} from 'lucide-react';
import { usePageMeta } from '../../components/layout/pageMeta';
import { useToast } from '../../components/feedback/useToast';
import { useI18n } from '../../i18n';
import type { ClientOnboardingRequest } from '../../api/types';
import OnboardingStepper from './OnboardingStepper';
import OnboardingSuccess from './OnboardingSuccess';
import { useClientOnboarding } from './useClientOnboarding';

const FALLBACK_CURRENCIES = ['USD', 'EUR', 'GBP', 'SAR', 'AED', 'EGP'];
const FALLBACK_PLAN_CODES = ['monthly', 'quarterly', 'yearly'];
const FALLBACK_PLAN_CODE = 'monthly';
const TOTAL_STEPS = 5;

/** Mirrors `validate_password_strength` on the backend, so the wizard refuses
 *  what the API would refuse without paying for a round trip. */
const PASSWORD_POLICY = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$/;
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type PasswordMode = 'generate' | 'manual' | 'reuse';

interface WizardForm {
  companyName: string;
  baseCurrency: string;
  adminEmail: string;
  adminFullName: string;
  passwordMode: PasswordMode;
  temporaryPassword: string;
  planCode: string;
  subscriptionStatus: 'active' | 'trial';
  expiresAt: string;
  seedDefaultAccounts: boolean;
  createFiscalYear: boolean;
  openMonthlyPeriods: boolean;
  onboardingNote: string;
}

/** `YYYY-MM-DD` for a date `months` from today, in the operator's own timezone. */
function dateInMonths(months: number): string {
  const target = new Date();
  target.setMonth(target.getMonth() + months);
  const offsetMs = target.getTimezoneOffset() * 60_000;
  return new Date(target.getTime() - offsetMs).toISOString().slice(0, 10);
}

/** A bare date means "through the end of that day" to a human. */
function toInstant(date: string): string | null {
  if (!date) return null;
  const parsed = new Date(`${date}T23:59:59Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

function daysUntil(date: string): number | null {
  if (!date) return null;
  const parsed = new Date(`${date}T23:59:59Z`);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.ceil((parsed.getTime() - Date.now()) / 86_400_000);
}

const INITIAL_FORM: WizardForm = {
  companyName: '',
  baseCurrency: 'USD',
  adminEmail: '',
  adminFullName: '',
  passwordMode: 'generate',
  temporaryPassword: '',
  planCode: FALLBACK_PLAN_CODE,
  subscriptionStatus: 'active',
  expiresAt: dateInMonths(1),
  seedDefaultAccounts: true,
  createFiscalYear: true,
  openMonthlyPeriods: true,
  onboardingNote: '',
};

export default function ClientOnboardingPage() {
  const { t } = useI18n();
  const { setMeta } = usePageMeta();
  const toast = useToast();
  const copy = t.clientOnboarding;

  const ids = {
    companyName: useId(),
    currency: useId(),
    email: useId(),
    fullName: useId(),
    password: useId(),
    plan: useId(),
    status: useId(),
    expires: useId(),
    note: useId(),
    seedAccounts: useId(),
    fiscalYear: useId(),
    periods: useId(),
  };

  const [step, setStep] = useState(0);
  const [form, setForm] = useState<WizardForm>(INITIAL_FORM);
  const [validationKey, setValidationKey] = useState<string | null>(null);

  const {
    defaults,
    isSubmitting,
    errorKey,
    result,
    fetchDefaults,
    onboard,
    reset,
    clearError,
  } = useClientOnboarding();

  useLayoutEffect(() => {
    setMeta({
      pageTitle: copy.pageTitle,
      pageSubtitle: copy.pageSubtitle,
      activePath: '/platform/onboarding',
    });
  }, [setMeta, copy]);

  useEffect(() => {
    void fetchDefaults();
  }, [fetchDefaults]);

  // Server-provided policy wins over the built-in fallbacks, but only for fields
  // the operator has not already touched.
  useEffect(() => {
    if (!defaults) return;
    setForm((previous) =>
      previous.companyName === '' && previous.adminEmail === ''
        ? {
            ...previous,
            baseCurrency: defaults.default_currency,
            planCode: defaults.default_plan_code,
            subscriptionStatus: defaults.default_subscription_status,
          }
        : previous,
    );
  }, [defaults]);

  const currencies = defaults?.suggested_currencies?.length
    ? defaults.suggested_currencies
    : FALLBACK_CURRENCIES;
  const planCodes = defaults?.suggested_plan_codes?.length
    ? defaults.suggested_plan_codes
    : FALLBACK_PLAN_CODES;

  const steps = useMemo(
    () => [
      copy.stepCompany,
      copy.stepAdmin,
      copy.stepSubscription,
      copy.stepAccounting,
      copy.stepReview,
    ],
    [copy],
  );

  const update = <K extends keyof WizardForm>(key: K, value: WizardForm[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }));
    setValidationKey(null);
    clearError();
  };

  /** Returns the translation key of the first unmet requirement of a step. */
  const validateStep = (index: number): string | null => {
    if (index === 0) {
      if (!form.companyName.trim()) return copy.validationCompanyNameRequired;
      if (form.baseCurrency.trim().length !== 3) return copy.validationCurrencyRequired;
    }
    if (index === 1) {
      if (!form.adminEmail.trim()) return copy.validationEmailRequired;
      if (!EMAIL_SHAPE.test(form.adminEmail.trim())) return copy.validationEmailInvalid;
      if (form.passwordMode === 'manual') {
        if (!form.temporaryPassword) return copy.validationPasswordRequired;
        if (!PASSWORD_POLICY.test(form.temporaryPassword)) {
          return copy.validationPasswordTooWeak;
        }
      }
    }
    if (index === 2 && !form.expiresAt) return copy.validationExpiryRequired;
    return null;
  };

  const goNext = () => {
    const failure = validateStep(step);
    if (failure) {
      setValidationKey(failure);
      return;
    }
    setValidationKey(null);
    setStep((current) => Math.min(current + 1, TOTAL_STEPS - 1));
  };

  const goBack = () => {
    setValidationKey(null);
    setStep((current) => Math.max(current - 1, 0));
  };

  const handleSubmit = async () => {
    // Re-check every step, not just the last one: the operator can jump back and
    // empty a field that was valid when it was first passed.
    for (let index = 0; index < TOTAL_STEPS; index += 1) {
      const failure = validateStep(index);
      if (failure) {
        setValidationKey(failure);
        setStep(index);
        return;
      }
    }

    const isTrial = form.subscriptionStatus === 'trial';
    const instant = toInstant(form.expiresAt);

    const payload: ClientOnboardingRequest = {
      company_name: form.companyName.trim(),
      base_currency: form.baseCurrency.trim().toUpperCase(),
      admin_email: form.adminEmail.trim(),
      admin_full_name: form.adminFullName.trim() || null,
      generate_password: form.passwordMode === 'generate',
      plan_code: form.planCode.trim() || null,
      subscription_status: form.subscriptionStatus,
      // A trial carries its end date in `trial_ends_at`; the backend derives the
      // expiry from it so the trial actually lapses.
      subscription_expires_at: isTrial ? null : instant,
      trial_ends_at: isTrial ? instant : null,
      seed_default_accounts: form.seedDefaultAccounts,
      create_fiscal_year: form.createFiscalYear,
      open_monthly_periods: form.createFiscalYear && form.openMonthlyPeriods,
      reuse_existing_user: form.passwordMode === 'reuse',
      onboarding_note: form.onboardingNote.trim() || null,
    };

    if (form.passwordMode === 'manual') {
      payload.temporary_password = form.temporaryPassword;
    }

    const created = await onboard(payload);
    if (created) toast.success(copy.createdToast);
  };

  const startOver = () => {
    reset();
    setForm({ ...INITIAL_FORM, expiresAt: dateInMonths(1) });
    setStep(0);
    setValidationKey(null);
  };

  if (result) {
    return <OnboardingSuccess result={result} onOnboardAnother={startOver} />;
  }

  const remaining = daysUntil(form.expiresAt);
  const expiryIsPast = remaining !== null && remaining < 0;

  const passwordSummary =
    form.passwordMode === 'generate'
      ? copy.reviewPasswordGenerated
      : form.passwordMode === 'manual'
        ? copy.reviewPasswordManual
        : copy.reviewPasswordReuse;

  const toggleRow = (
    id: string,
    label: string,
    help: string,
    checked: boolean,
    disabled: boolean,
    onChange: (next: boolean) => void,
  ) => (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3">
      <div className="min-w-0">
        <label htmlFor={id} className="text-xs font-semibold text-muted-foreground">
          {label}
        </label>
        <p className="mt-0.5 text-xs text-subtle-foreground">{help}</p>
      </div>
      <label htmlFor={id} className="relative inline-flex flex-shrink-0 items-center">
        <input
          id={id}
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden
          className="peer h-6 w-11 cursor-pointer rounded-full border border-border-strong bg-surface-overlay transition-colors after:absolute after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-border-strong after:bg-primary-foreground after:transition-transform after:content-[''] after:start-[2px] peer-checked:border-primary-solid peer-checked:bg-primary-solid peer-checked:after:translate-x-full peer-checked:after:border-transparent peer-focus-visible:ring-2 peer-focus-visible:ring-ring-soft peer-disabled:cursor-not-allowed peer-disabled:opacity-50 rtl:peer-checked:after:-translate-x-full"
        />
      </label>
    </div>
  );

  const reviewRow = (label: string, value: string) => (
    <div key={label} className="flex items-baseline justify-between gap-4 py-1.5">
      <dt className="text-xs text-subtle-foreground">{label}</dt>
      <dd className="truncate text-xs font-medium text-foreground">{value}</dd>
    </div>
  );

  return (
    <div className="space-y-5">
      <OnboardingStepper
        steps={steps}
        current={step}
        progressLabel={copy.stepProgress
          .replace('{current}', String(step + 1))
          .replace('{total}', String(TOTAL_STEPS))}
        onSelect={setStep}
      />

      <section className="card p-5 sm:p-6">
        {step === 0 && (
          <div className="space-y-4">
            <header>
              <h2 className="text-base font-semibold text-foreground">{copy.companyStepTitle}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{copy.companyStepDescription}</p>
            </header>

            <div>
              <label htmlFor={ids.companyName} className="field-label">
                {copy.companyNameLabel}
              </label>
              <input
                id={ids.companyName}
                type="text"
                maxLength={255}
                value={form.companyName}
                onChange={(e) => update('companyName', e.target.value)}
                placeholder={copy.companyNamePlaceholder}
                className="input"
              />
            </div>

            <div>
              <label htmlFor={ids.currency} className="field-label">
                {copy.baseCurrencyLabel}
              </label>
              <select
                id={ids.currency}
                value={form.baseCurrency}
                onChange={(e) => update('baseCurrency', e.target.value)}
                className="select"
              >
                {currencies.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-subtle-foreground">{copy.baseCurrencyHelp}</p>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <header>
              <h2 className="text-base font-semibold text-foreground">{copy.adminStepTitle}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{copy.adminStepDescription}</p>
            </header>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor={ids.email} className="field-label">
                  {copy.adminEmailLabel}
                </label>
                <input
                  id={ids.email}
                  type="email"
                  autoComplete="off"
                  value={form.adminEmail}
                  onChange={(e) => update('adminEmail', e.target.value)}
                  placeholder={copy.adminEmailPlaceholder}
                  className="input"
                />
              </div>
              <div>
                <label htmlFor={ids.fullName} className="field-label">
                  {copy.adminFullNameLabel}
                </label>
                <input
                  id={ids.fullName}
                  type="text"
                  maxLength={255}
                  value={form.adminFullName}
                  onChange={(e) => update('adminFullName', e.target.value)}
                  placeholder={copy.adminFullNamePlaceholder}
                  className="input"
                />
              </div>
            </div>

            <fieldset>
              <legend className="field-label">{copy.passwordModeLabel}</legend>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {(
                  [
                    ['generate', copy.passwordModeGenerate],
                    ['manual', copy.passwordModeManual],
                    ['reuse', copy.passwordModeReuse],
                  ] as ReadonlyArray<readonly [PasswordMode, string]>
                ).map(([mode, label]) => (
                  <label
                    key={mode}
                    className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors duration-fast ${
                      form.passwordMode === mode
                        ? 'border-primary-solid bg-primary-soft text-primary'
                        : 'border-border bg-surface text-muted-foreground hover:border-border-strong'
                    }`}
                  >
                    <input
                      type="radio"
                      name="password-mode"
                      value={mode}
                      checked={form.passwordMode === mode}
                      onChange={() => update('passwordMode', mode)}
                      className="sr-only"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            {form.passwordMode === 'generate' && (
              <div className="callout tone-info">
                <Info aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>{copy.generatePasswordHelp}</p>
              </div>
            )}

            {form.passwordMode === 'manual' && (
              <div>
                <label htmlFor={ids.password} className="field-label">
                  {copy.temporaryPasswordLabel}
                </label>
                <input
                  id={ids.password}
                  type="text"
                  autoComplete="off"
                  maxLength={128}
                  value={form.temporaryPassword}
                  onChange={(e) => update('temporaryPassword', e.target.value)}
                  placeholder={copy.temporaryPasswordPlaceholder}
                  className="input"
                />
                <p className="mt-1 text-xs text-subtle-foreground">{copy.passwordPolicyHelp}</p>
              </div>
            )}

            {form.passwordMode === 'reuse' && (
              <div className="callout tone-info">
                <Info aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>{copy.reuseExistingUserHelp}</p>
              </div>
            )}

            {form.passwordMode !== 'reuse' && (
              <div className="callout tone-warning">
                <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>{copy.changePasswordWarning}</p>
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <header>
              <h2 className="text-base font-semibold text-foreground">
                {copy.subscriptionStepTitle}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {copy.subscriptionStepDescription}
              </p>
            </header>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor={ids.plan} className="field-label">
                  {copy.planCodeLabel}
                </label>
                <input
                  id={ids.plan}
                  type="text"
                  list={`${ids.plan}-options`}
                  maxLength={50}
                  value={form.planCode}
                  onChange={(e) => update('planCode', e.target.value)}
                  placeholder={copy.planCodePlaceholder}
                  className="input"
                />
                <datalist id={`${ids.plan}-options`}>
                  {planCodes.map((code) => (
                    <option key={code} value={code} />
                  ))}
                </datalist>
              </div>
              <div>
                <label htmlFor={ids.status} className="field-label">
                  {copy.statusLabel}
                </label>
                <select
                  id={ids.status}
                  value={form.subscriptionStatus}
                  onChange={(e) =>
                    update('subscriptionStatus', e.target.value as 'active' | 'trial')
                  }
                  className="select"
                >
                  <option value="active">{t.subscriptionStatus.active}</option>
                  <option value="trial">{t.subscriptionStatus.trial}</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor={ids.expires} className="field-label">
                {form.subscriptionStatus === 'trial'
                  ? copy.trialEndsAtLabel
                  : copy.expiresAtLabel}
              </label>
              <input
                id={ids.expires}
                type="date"
                value={form.expiresAt}
                onChange={(e) => update('expiresAt', e.target.value)}
                className="input"
              />
              <p className="mt-1 text-xs text-subtle-foreground">
                {form.subscriptionStatus === 'trial'
                  ? copy.trialEndsAtHelp
                  : copy.expiresAtHelp}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {(
                [
                  [1, copy.presetMonth],
                  [3, copy.presetQuarter],
                  [12, copy.presetYear],
                ] as ReadonlyArray<readonly [number, string]>
              ).map(([months, label]) => (
                <button
                  key={months}
                  type="button"
                  onClick={() => update('expiresAt', dateInMonths(months))}
                  className="btn btn-secondary btn-sm"
                >
                  {label}
                </button>
              ))}
              {remaining !== null && !expiryIsPast && (
                <span className="badge tone-neutral numeric">
                  {copy.daysRemainingLabel}:{' '}
                  {copy.daysRemainingValue.replace('{days}', String(remaining))}
                </span>
              )}
            </div>

            {expiryIsPast && (
              <div className="callout tone-danger">
                <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>{copy.expiryInPastWarning}</p>
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <header>
              <h2 className="text-base font-semibold text-foreground">
                {copy.accountingStepTitle}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {copy.accountingStepDescription}
              </p>
            </header>

            <div className="space-y-3">
              {toggleRow(
                ids.seedAccounts,
                copy.seedAccountsLabel,
                copy.seedAccountsHelp,
                form.seedDefaultAccounts,
                false,
                (next) => update('seedDefaultAccounts', next),
              )}
              {toggleRow(
                ids.fiscalYear,
                copy.createFiscalYearLabel,
                copy.createFiscalYearHelp,
                form.createFiscalYear,
                false,
                (next) => update('createFiscalYear', next),
              )}
              {toggleRow(
                ids.periods,
                copy.openPeriodsLabel,
                form.createFiscalYear
                  ? copy.openPeriodsHelp
                  : copy.openPeriodsRequiresFiscalYear,
                form.createFiscalYear && form.openMonthlyPeriods,
                !form.createFiscalYear,
                (next) => update('openMonthlyPeriods', next),
              )}
            </div>

            <div>
              <label htmlFor={ids.note} className="field-label">
                {copy.onboardingNoteLabel}
              </label>
              <textarea
                id={ids.note}
                rows={3}
                maxLength={2000}
                value={form.onboardingNote}
                onChange={(e) => update('onboardingNote', e.target.value)}
                placeholder={copy.onboardingNotePlaceholder}
                className="input resize-y"
              />
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <header>
              <h2 className="text-base font-semibold text-foreground">{copy.reviewStepTitle}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{copy.reviewStepDescription}</p>
            </header>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="panel px-3.5 py-3">
                <p className="overline mb-1">{copy.reviewCompanySection}</p>
                <dl className="divide-y divide-border-subtle">
                  {reviewRow(copy.companyNameLabel, form.companyName)}
                  {reviewRow(copy.baseCurrencyLabel, form.baseCurrency)}
                </dl>
              </div>

              <div className="panel px-3.5 py-3">
                <p className="overline mb-1">{copy.reviewAdminSection}</p>
                <dl className="divide-y divide-border-subtle">
                  {reviewRow(copy.adminEmailLabel, form.adminEmail)}
                  {reviewRow(
                    copy.adminFullNameLabel,
                    form.adminFullName.trim() || copy.reviewNotProvided,
                  )}
                  {reviewRow(copy.passwordModeLabel, passwordSummary)}
                </dl>
              </div>

              <div className="panel px-3.5 py-3">
                <p className="overline mb-1">{copy.reviewSubscriptionSection}</p>
                <dl className="divide-y divide-border-subtle">
                  {reviewRow(copy.planCodeLabel, form.planCode.trim() || copy.reviewNoPlan)}
                  {reviewRow(copy.statusLabel, t.subscriptionStatus[form.subscriptionStatus])}
                  {reviewRow(
                    form.subscriptionStatus === 'trial'
                      ? copy.trialEndsAtLabel
                      : copy.expiresAtLabel,
                    form.expiresAt || copy.reviewNoExpiry,
                  )}
                </dl>
              </div>

              <div className="panel px-3.5 py-3">
                <p className="overline mb-1">{copy.reviewAccountingSection}</p>
                <dl className="divide-y divide-border-subtle">
                  {reviewRow(
                    copy.seedAccountsLabel,
                    form.seedDefaultAccounts ? t.common.yes : t.common.no,
                  )}
                  {reviewRow(
                    copy.createFiscalYearLabel,
                    form.createFiscalYear ? t.common.yes : t.common.no,
                  )}
                  {reviewRow(
                    copy.openPeriodsLabel,
                    form.createFiscalYear && form.openMonthlyPeriods
                      ? t.common.yes
                      : t.common.no,
                  )}
                </dl>
              </div>
            </div>

            {form.passwordMode === 'generate' && (
              <div className="callout tone-warning">
                <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <p>{copy.passwordShownOnceWarning}</p>
              </div>
            )}
          </div>
        )}

        {validationKey && (
          <p role="alert" className="mt-4 text-xs font-medium text-danger">
            {validationKey}
          </p>
        )}

        {errorKey && (
          <div role="alert" className="callout tone-danger mt-4">
            <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>{copy[errorKey]}</p>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between gap-3 border-t border-border-subtle pt-4">
          <button
            type="button"
            onClick={goBack}
            disabled={step === 0 || isSubmitting}
            className="btn btn-ghost btn-sm"
          >
            <ArrowLeft aria-hidden className="h-3.5 w-3.5 rtl:rotate-180" />
            {t.common.back}
          </button>

          {step < TOTAL_STEPS - 1 ? (
            <button type="button" onClick={goNext} className="btn btn-primary btn-sm">
              {t.common.next}
              <ArrowRight aria-hidden className="h-3.5 w-3.5 rtl:rotate-180" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={isSubmitting}
              className="btn btn-primary btn-sm"
            >
              {isSubmitting ? (
                <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <UserPlus aria-hidden className="h-3.5 w-3.5" />
              )}
              {isSubmitting ? copy.creating : copy.createClient}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
