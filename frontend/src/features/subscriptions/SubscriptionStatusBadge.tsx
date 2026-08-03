import { Ban, CheckCircle2, Clock, PauseCircle, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { SubscriptionStatus } from '../../api/types';

const APPEARANCE: Record<SubscriptionStatus, { tone: string; icon: LucideIcon }> = {
  active: { tone: 'tone-success', icon: CheckCircle2 },
  trial: { tone: 'tone-primary', icon: Sparkles },
  past_due: { tone: 'tone-warning', icon: Clock },
  suspended: { tone: 'tone-danger', icon: PauseCircle },
  cancelled: { tone: 'tone-neutral', icon: Ban },
};

interface SubscriptionStatusBadgeProps {
  status: SubscriptionStatus;
}

export default function SubscriptionStatusBadge({ status }: SubscriptionStatusBadgeProps) {
  const { t } = useI18n();
  const { tone, icon: Icon } = APPEARANCE[status];

  return (
    <span className={`badge ${tone}`}>
      <Icon aria-hidden className="h-3 w-3" />
      {t.subscriptionStatus[status]}
    </span>
  );
}
