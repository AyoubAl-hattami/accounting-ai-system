
import { useI18n } from '../../i18n';
import { getActionLabel } from './auditActionLabels';

interface AuditActionBadgeProps {
  action: string;
}

// ── Action → colour class map ─────────────────────────────────────────────────
function getColorClass(action: string): string {
  const a = action.toLowerCase();

  if (a.includes('post')) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  if (a.includes('void'))  return 'bg-red-500/10 text-red-400 border-red-500/20';
  if (a.includes('delete') || a.includes('remove') || a.includes('deactivate'))
    return 'bg-red-500/10 text-red-400 border-red-500/20';
  if (a.includes('reverse')) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  if (a.includes('create') || a.includes('accept')) return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  if (a.includes('update') || a.includes('edit') || a.includes('restore') || a.includes('reactivate'))
    return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
  if (a.includes('review') || a.includes('approve'))
    return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
  if (a.includes('cancel')) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  if (a.includes('login_success')) return 'bg-green-500/10 text-green-400 border-green-500/20';
  if (a.includes('login_failure') || a.includes('login_failed'))
    return 'bg-red-500/10 text-red-400 border-red-500/20';
  if (a.includes('login')) return 'bg-sky-500/10 text-sky-400 border-sky-500/20';

  return 'bg-white/[0.04] text-gray-400 border-white/[0.06]';
}

export default function AuditActionBadge({ action }: AuditActionBadgeProps) {
  const { t } = useI18n();
  const colorClass = getColorClass(action);

  // Cast so we can do an index lookup
  const auditT = t.auditLogs as unknown as Record<string, string>;
  const label = getActionLabel(action, auditT);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}
    >
      {label}
    </span>
  );
}
