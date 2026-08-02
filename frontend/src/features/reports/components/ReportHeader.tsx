import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import type { ReportTone } from './reportTone';

interface ReportStatus {
  label: string;
  tone: ReportTone;
  icon?: LucideIcon;
}

interface ReportHeaderProps {
  icon: LucideIcon;
  title: string;
  /** The reporting period, e.g. "Through 31 Dec 2025" or "All time". */
  periodLabel: string;
  status?: ReportStatus;
  /** Export buttons and other header-level actions. */
  actions?: ReactNode;
  /** Summary tiles; rendered as a hairline-separated strip below the header. */
  children?: ReactNode;
  /** Number of tiles per row on large screens. */
  columns?: 2 | 3 | 4;
}

const columnClass: Record<2 | 3 | 4, string> = {
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-2 lg:grid-cols-3',
  4: 'sm:grid-cols-2 lg:grid-cols-4',
};

/**
 * Masthead for a financial report: identifies the report and its period, states
 * whether the figures balance, and carries the export actions. The summary strip
 * below it holds the headline totals so they read before the detail table.
 */
export default function ReportHeader({
  icon: Icon,
  title,
  periodLabel,
  status,
  actions,
  children,
  columns = 4,
}: ReportHeaderProps) {
  const StatusIcon = status?.icon;

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="card overflow-hidden"
    >
      {/* The masthead carries a brand wash so a statement opens like a document
          rather than like another table. */}
      <div className="relative flex flex-col gap-4 overflow-hidden border-b border-border bg-surface-muted px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.10]"
          style={{ background: 'var(--gradient-brand)' }}
        />
        <div className="relative flex min-w-0 items-center gap-3">
          <span
            aria-hidden
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-primary text-white shadow-[0_10px_26px_-10px_var(--primary-glow)]"
          >
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h2 className="page-title truncate">{title}</h2>
            <p className="truncate text-xs text-muted-foreground">{periodLabel}</p>
          </div>
        </div>

        <div className="relative flex flex-wrap items-center gap-2">
          {status && (
            <span className={`badge tone-${status.tone} px-3 py-1 text-xs`}>
              {StatusIcon && <StatusIcon aria-hidden className="h-3.5 w-3.5" />}
              {status.label}
            </span>
          )}
          {actions}
        </div>
      </div>

      {children && (
        <div className={`grid grid-cols-1 gap-px bg-border-subtle ${columnClass[columns]}`}>
          {children}
        </div>
      )}
    </motion.section>
  );
}
