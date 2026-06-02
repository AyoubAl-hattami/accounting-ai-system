import type { JournalEntryStatus } from '../../api/types';

interface JournalStatusBadgeProps {
  status: JournalEntryStatus;
}

const statusStyles: Record<JournalEntryStatus, string> = {
  draft: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
  reviewed: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  posted: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  void: 'bg-red-500/10 text-red-400 border-red-500/20',
  reversed: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
};

export default function JournalStatusBadge({ status }: JournalStatusBadgeProps) {
  const style = statusStyles[status] || 'bg-gray-500/10 text-gray-400 border-gray-500/20';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${style}`}>
      {status}
    </span>
  );
}
