
interface AuditActionBadgeProps {
  action: string;
}

export default function AuditActionBadge({ action }: AuditActionBadgeProps) {
  let colorClass = 'bg-white/[0.04] text-gray-400 border-white/[0.06]';
  const normalizedAction = action.toLowerCase();

  if (normalizedAction.includes('post')) {
    colorClass = 'bg-green-500/10 text-green-400 border-green-500/20';
  } else if (normalizedAction.includes('void') || normalizedAction.includes('delete')) {
    colorClass = 'bg-red-500/10 text-red-400 border-red-500/20';
  } else if (normalizedAction.includes('reverse')) {
    colorClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  } else if (normalizedAction.includes('create')) {
    colorClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  } else if (normalizedAction.includes('update') || normalizedAction.includes('edit')) {
    colorClass = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
  } else if (normalizedAction.includes('review') || normalizedAction.includes('approve')) {
    colorClass = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
  }

  // Format action text for readability (e.g. "create_journal_entry" -> "Create Journal Entry")
  const formattedAction = action
    .split(/_|-|\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {formattedAction}
    </span>
  );
}
