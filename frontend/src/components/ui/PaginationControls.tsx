import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useI18n } from '../../i18n';

interface PaginationControlsProps {
  skip: number;
  limit: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  /** Localised plural noun for the rows being paged, e.g. "entries". */
  entityName?: string;
}

export default function PaginationControls({
  skip,
  limit,
  total,
  onPrev,
  onNext,
  entityName,
}: PaginationControlsProps) {
  const { t } = useI18n();
  const start = total === 0 ? 0 : skip + 1;
  const end = Math.min(skip + limit, total);
  const hasPrev = skip > 0;
  const hasNext = skip + limit < total;

  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle pt-4"
      aria-label={t.common.pagination}
    >
      <p className="text-xs text-muted-foreground">
        {t.common.showing}{' '}
        <span className="numeric font-semibold text-foreground">
          {start}–{end}
        </span>{' '}
        {t.common.of} <span className="numeric font-semibold text-foreground">{total}</span>
        {entityName ? ` ${entityName}` : ''}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPrev}
          disabled={!hasPrev}
          className="btn btn-secondary btn-sm"
        >
          <ChevronLeft className="h-3.5 w-3.5 rtl:rotate-180" />
          {t.common.previous}
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!hasNext}
          className="btn btn-secondary btn-sm"
        >
          {t.common.next}
          <ChevronRight className="h-3.5 w-3.5 rtl:rotate-180" />
        </button>
      </div>
    </nav>
  );
}
