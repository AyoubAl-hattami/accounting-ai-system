import { useI18n } from '../../i18n';
import { getActionLabel } from './auditActionLabels';

interface AuditActionBadgeProps {
  action: string;
}

/**
 * Audit actions are free-form strings from the backend, so the tone is derived
 * from the verb rather than an exhaustive map. Order matters: the more specific
 * checks (login_failure) must run before their prefixes (login).
 */
function getTone(action: string): string {
  const a = action.toLowerCase();

  if (a.includes('login_failure') || a.includes('login_failed')) return 'tone-danger';
  if (a.includes('login_success')) return 'tone-success';
  if (a.includes('login')) return 'tone-info';
  if (a.includes('post')) return 'tone-success';
  if (a.includes('void') || a.includes('delete') || a.includes('remove') || a.includes('deactivate'))
    return 'tone-danger';
  if (a.includes('reverse') || a.includes('cancel')) return 'tone-warning';
  if (a.includes('create') || a.includes('accept')) return 'tone-info';
  if (a.includes('update') || a.includes('edit') || a.includes('restore') || a.includes('reactivate'))
    return 'tone-primary';
  if (a.includes('review') || a.includes('approve')) return 'tone-violet';

  return 'tone-neutral';
}

export default function AuditActionBadge({ action }: AuditActionBadgeProps) {
  const { t } = useI18n();

  // Cast so we can do an index lookup
  const auditT = t.auditLogs as unknown as Record<string, string>;
  const label = getActionLabel(action, auditT);

  return <span className={`badge ${getTone(action)}`}>{label}</span>;
}
