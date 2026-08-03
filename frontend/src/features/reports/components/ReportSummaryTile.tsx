import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { reportToneText, type ReportTone } from './reportTone';

interface ReportSummaryTileProps {
  label: string;
  /** A node so signed figures can bring their own positive/negative colour. */
  value: ReactNode;
  tone?: ReportTone;
  icon?: LucideIcon;
  /** Secondary line under the figure, e.g. a comparison or account count. */
  hint?: string;
  /** Renders the figure larger — reserve for the single headline number. */
  emphasis?: boolean;
}

/** One cell of the summary strip rendered inside {@link ReportHeader}. */
export default function ReportSummaryTile({
  label,
  value,
  tone = 'neutral',
  icon: Icon,
  hint,
  emphasis,
}: ReportSummaryTileProps) {
  return (
    <div className="group relative bg-surface px-5 py-4 transition-colors duration-fast ease-standard hover:bg-surface-muted">
      <div className="mb-1.5 flex items-center gap-1.5">
        {Icon && (
          <Icon
            aria-hidden
            className={`h-3.5 w-3.5 flex-shrink-0 transition-transform duration-normal ease-emphasized group-hover:scale-110 ${reportToneText[tone]}`}
          />
        )}
        <span className="overline truncate">{label}</span>
      </div>
      <p
        className={`numeric font-semibold ${emphasis ? 'text-2xl' : 'text-xl'} ${reportToneText[tone]}`}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-subtle-foreground">{hint}</p>}
    </div>
  );
}
