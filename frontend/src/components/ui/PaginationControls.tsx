import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useI18n } from '../../i18n';

interface PaginationControlsProps {
  skip: number;
  limit: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  entityName?: string;
}

export default function PaginationControls({
  skip,
  limit,
  total,
  onPrev,
  onNext,
  entityName = 'accounts',
}: PaginationControlsProps) {
  const { t } = useI18n();
  const start = total === 0 ? 0 : skip + 1;
  const end = Math.min(skip + limit, total);
  const hasPrev = skip > 0;
  const hasNext = skip + limit < total;

  return (
    <div className="flex items-center justify-between pt-4">
      <p className="text-xs text-gray-500">
        {t.common.showing} <span className="text-gray-300 font-medium">{start}–{end}</span> {t.common.of}{' '}
        <span className="text-gray-300 font-medium">{total}</span> {entityName}
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          disabled={!hasPrev}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-white/[0.06] bg-white/[0.03] text-gray-300 hover:bg-white/[0.06] hover:text-white transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-white/[0.03]"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          {t.common.previous}
        </button>
        <button
          onClick={onNext}
          disabled={!hasNext}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border border-white/[0.06] bg-white/[0.03] text-gray-300 hover:bg-white/[0.06] hover:text-white transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-white/[0.03]"
        >
          {t.common.next}
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
