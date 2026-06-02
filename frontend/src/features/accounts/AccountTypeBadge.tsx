interface AccountTypeBadgeProps {
  type: string;
}

const typeStyles: Record<string, string> = {
  asset: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  liability: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  equity: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  income: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  expense: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

export default function AccountTypeBadge({ type }: AccountTypeBadgeProps) {
  const style = typeStyles[type] || 'bg-gray-500/10 text-gray-400 border-gray-500/20';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${style}`}>
      {type}
    </span>
  );
}
