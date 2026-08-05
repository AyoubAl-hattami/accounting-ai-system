import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, ClipboardCopy, KeyRound, RotateCcw, ShieldAlert } from 'lucide-react';
import { useToast } from '../../components/feedback/useToast';
import { useI18n } from '../../i18n';
import type { ClientOnboardingResult, SubscriptionStatus } from '../../api/types';
import { buildHandoverMessage, formatHandoverDate } from './handoverMessage';

const STATUS_TONE: Record<SubscriptionStatus, string> = {
  trial: 'tone-info',
  active: 'tone-success',
  past_due: 'tone-warning',
  suspended: 'tone-warning',
  cancelled: 'tone-danger',
};

interface OnboardingSuccessProps {
  result: ClientOnboardingResult;
  onOnboardAnother: () => void;
}

export default function OnboardingSuccess({
  result,
  onOnboardAnother,
}: OnboardingSuccessProps) {
  const { t } = useI18n();
  const toast = useToast();
  const copy = t.clientOnboarding;
  const [copyFailed, setCopyFailed] = useState(false);

  const message = buildHandoverMessage(copy, {
    companyName: result.company_name,
    adminEmail: result.admin_email,
    temporaryPassword: result.generated_password,
    expiresAt: result.expires_at,
    loginUrl: result.public_login_url,
  });

  // The server sends its placeholder when APP_PUBLIC_URL is unset, which is the
  // one thing an operator must fix before the message is worth sending.
  const urlConfigured = !result.public_login_url.startsWith('[');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setCopyFailed(false);
      toast.success(copy.copiedToast);
    } catch {
      // Clipboard access is denied outside secure contexts, so the message stays
      // on screen in a selectable field and the operator is told to copy it.
      setCopyFailed(true);
      toast.error(copy.copyFailed);
    }
  };

  const summary: Array<{ label: string; value: string }> = [
    { label: copy.summaryCompanyId, value: String(result.company_id) },
    { label: copy.summaryAdminUserId, value: String(result.admin_user_id) },
    { label: copy.summarySeededAccounts, value: String(result.seeded_accounts_count) },
    {
      label: copy.summaryFiscalYear,
      value: result.fiscal_year_created ? copy.fiscalYearCreated : copy.fiscalYearExisting,
    },
    { label: copy.summaryFiscalPeriods, value: String(result.fiscal_periods_created) },
    {
      label: copy.summaryExpiry,
      value: formatHandoverDate(result.expires_at) ?? copy.reviewNoExpiry,
    },
    { label: copy.handoverLoginUrl, value: result.public_login_url },
  ];

  return (
    <div className="space-y-5">
      <section className="card p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-success-soft text-success"
          >
            <CheckCircle2 className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-foreground">{copy.successTitle}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{copy.successDescription}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-foreground">{result.company_name}</span>
              <span className={`badge ${STATUS_TONE[result.effective_status]}`}>
                {t.subscriptionStatus[result.effective_status]}
              </span>
              {result.days_remaining !== null && (
                <span className="badge tone-neutral numeric">
                  {copy.daysRemainingValue.replace('{days}', String(result.days_remaining))}
                </span>
              )}
            </div>
          </div>
        </div>

        <dl className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {summary.map((item) => (
            <div key={item.label} className="panel px-3.5 py-2.5">
              <dt className="overline">{item.label}</dt>
              <dd className="numeric mt-0.5 text-sm font-medium text-foreground">{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {result.generated_password && (
        <div className="callout tone-warning">
          <ShieldAlert aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>{copy.passwordShownOnceWarning}</p>
        </div>
      )}

      {!urlConfigured && (
        <div className="callout tone-warning">
          <ShieldAlert aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>{copy.handoverUrlNotConfigured}</p>
        </div>
      )}

      <section className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-foreground">{copy.handoverTitle}</h3>
            <p className="mt-1 text-xs text-subtle-foreground">{copy.handoverHelp}</p>
          </div>
          <button type="button" onClick={handleCopy} className="btn btn-secondary btn-sm">
            <ClipboardCopy aria-hidden className="h-3.5 w-3.5" />
            {copy.copyMessage}
          </button>
        </div>

        {copyFailed && (
          <p className="mt-3 text-xs font-medium text-danger">{copy.copyFailed}</p>
        )}

        <pre
          data-testid="handover-message"
          className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-border-subtle bg-surface-muted px-3.5 py-3 text-sm text-foreground"
        >
          {message}
        </pre>

        {result.must_change_password && (
          <p className="mt-3 flex items-start gap-1.5 text-xs text-subtle-foreground">
            <KeyRound aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            {copy.changePasswordWarning}
          </p>
        )}
      </section>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={onOnboardAnother} className="btn btn-primary btn-sm">
          <RotateCcw aria-hidden className="h-3.5 w-3.5" />
          {copy.onboardAnother}
        </button>
        <Link to="/platform/subscriptions" className="btn btn-secondary btn-sm">
          {copy.goToSubscriptions}
        </Link>
      </div>
    </div>
  );
}
