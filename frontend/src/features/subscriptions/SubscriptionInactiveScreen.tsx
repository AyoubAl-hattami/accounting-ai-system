import { motion } from 'framer-motion';
import { Lock } from 'lucide-react';
import { useI18n } from '../../i18n';
import SubscriptionStatusBadge from './SubscriptionStatusBadge';
import type { CompanySubscriptionStatus } from '../../api/types';

interface SubscriptionInactiveScreenProps {
  status: CompanySubscriptionStatus;
}

/**
 * Replaces the page content when the selected company may no longer transact.
 * The business endpoints answer 403 in this state, so rendering a page here
 * would only produce a wall of failed requests.
 */
export default function SubscriptionInactiveScreen({ status }: SubscriptionInactiveScreenProps) {
  const { t, language } = useI18n();

  const expiredOn = status.expires_at
    ? new Date(status.expires_at).toLocaleDateString(language === 'ar' ? 'ar' : 'en-GB', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
      })
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center justify-center py-24"
      role="alert"
    >
      <div className="card max-w-md p-10 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-warning-border bg-warning-soft text-warning">
          <Lock className="h-6 w-6" />
        </div>

        <h2 className="mb-2 text-xl font-semibold text-foreground">
          {t.subscriptionInactive.title}
        </h2>
        <p className="mx-auto max-w-sm text-sm leading-relaxed text-muted-foreground">
          {t.subscriptionInactive.message}
        </p>

        <dl className="mt-7 space-y-2 text-sm">
          <div className="flex items-center justify-between gap-3">
            <dt className="text-subtle-foreground">{t.subscriptionInactive.currentStatus}</dt>
            <dd>
              <SubscriptionStatusBadge status={status.effective_status} />
            </dd>
          </div>
          {expiredOn && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-subtle-foreground">{t.subscriptionInactive.expiredOn}</dt>
              <dd className="numeric text-foreground">{expiredOn}</dd>
            </div>
          )}
        </dl>
      </div>
    </motion.div>
  );
}
