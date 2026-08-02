import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { AccountTypeBadge } from '../../../entities/account';
import { useI18n } from '../../../i18n';
import { formatCurrency } from '../../../lib/format';
import { reportToneText, type ReportTone } from './reportTone';

/** Common shape of a single account row across the statement reports. */
export interface ReportAccountLine {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  amount: string;
}

interface ReportSectionTableProps {
  title: string;
  icon: LucideIcon;
  tone: ReportTone;
  lines: ReportAccountLine[];
  totalLabel: string;
  totalAmount: string;
  delay?: number;
}

function parseAmount(v: string): number {
  return parseFloat(v) || 0;
}

/** Zero rows render as an em dash so the figures that matter stand out. */
function fmtAmt(v: string): string {
  const n = parseAmount(v);
  return n === 0 ? '—' : formatCurrency(Math.abs(n));
}

/**
 * One statement section (Assets, Liabilities, Income, …): a titled panel with a
 * right-aligned amount column and a subtotal row that reads as a summary rather
 * than as another line of data.
 */
export default function ReportSectionTable({
  title,
  icon: Icon,
  tone,
  lines,
  totalLabel,
  totalAmount,
  delay = 0,
}: ReportSectionTableProps) {
  const { t } = useI18n();
  const figureClass = reportToneText[tone];

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      className="card overflow-hidden"
    >
      <div className="flex items-center gap-3 border-b border-border bg-surface-muted px-5 py-3">
        <span
          aria-hidden
          className={`badge tone-${tone} h-8 w-8 flex-shrink-0 justify-center rounded-lg p-0`}
        >
          <Icon className="h-4 w-4" />
        </span>
        <h2 className="section-title">{title}</h2>
        <span className="numeric ms-auto text-xs text-subtle-foreground">
          {lines.length} {t.reports.shared.accountsShown}
        </span>
      </div>

      {lines.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-subtle-foreground">{t.common.noResults}</p>
      ) : (
        <>
          {/* Desktop table */}
          <div className="table-wrap hidden md:block">
            <table className="data-table">
              <caption className="sr-only">{title}</caption>
              <thead>
                <tr>
                  <th scope="col">{t.common.code}</th>
                  <th scope="col">{t.common.account}</th>
                  <th scope="col">{t.common.type}</th>
                  <th scope="col" className="cell-numeric">
                    {t.common.amount}
                  </th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => (
                  <tr key={line.account_id}>
                    <td>
                      <span className="numeric text-sm font-semibold text-primary">
                        {line.account_code}
                      </span>
                    </td>
                    <td className="font-medium">{line.account_name}</td>
                    <td>
                      <AccountTypeBadge type={line.account_type} />
                    </td>
                    <td className={`cell-numeric ${figureClass}`}>{fmtAmt(line.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3}>{totalLabel}</td>
                  <td className={`cell-numeric ${figureClass}`}>
                    {formatCurrency(parseAmount(totalAmount))}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Mobile cards */}
          <div className="divide-y divide-border-subtle md:hidden">
            {lines.map((line) => (
              <div key={line.account_id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="numeric text-xs font-semibold text-primary">
                      {line.account_code}
                    </span>
                    <h3 className="mt-0.5 text-sm font-medium text-foreground">
                      {line.account_name}
                    </h3>
                  </div>
                  <AccountTypeBadge type={line.account_type} />
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="overline">{t.common.amount}</span>
                  <span className={`numeric text-sm font-semibold ${figureClass}`}>
                    {fmtAmt(line.amount)}
                  </span>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between bg-surface-muted px-4 py-3">
              <span className="text-xs font-semibold text-foreground">{totalLabel}</span>
              <span className={`numeric text-sm font-semibold ${figureClass}`}>
                {formatCurrency(parseAmount(totalAmount))}
              </span>
            </div>
          </div>
        </>
      )}
    </motion.section>
  );
}
