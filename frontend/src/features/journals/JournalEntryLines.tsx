import { motion } from 'framer-motion';
import type { JournalLine } from '../../api/types';
import { useI18n } from '../../i18n';

interface JournalEntryLinesProps {
  lines: JournalLine[];
}

/** Zero sides render as an em dash so the posted side of each line is obvious. */
function fmt(v: string): string {
  const n = parseFloat(v);
  if (isNaN(n) || n === 0) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function JournalEntryLines({ lines }: JournalEntryLinesProps) {
  const { t } = useI18n();

  if (lines.length === 0) {
    return <p className="py-4 text-center text-xs text-subtle-foreground">{t.journals.noLines}</p>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="overflow-hidden"
    >
      <div className="px-4 pb-4 pt-2">
        <div className="overflow-hidden rounded-lg border border-border-subtle bg-surface-muted">
          {/* Desktop table */}
          <div className="table-wrap hidden sm:block">
            <table className="data-table">
              <caption className="sr-only">{t.common.journalLines}</caption>
              <thead>
                <tr>
                  <th scope="col" className="cell-numeric">
                    {t.journals.lines}
                  </th>
                  <th scope="col">{t.common.account}</th>
                  <th scope="col" className="cell-numeric">
                    {t.journals.debit}
                  </th>
                  <th scope="col" className="cell-numeric">
                    {t.journals.credit}
                  </th>
                  <th scope="col">{t.common.description}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => (
                  <tr key={line.id}>
                    <td className="cell-numeric text-xs text-subtle-foreground">{line.line_no}</td>
                    <td className="numeric text-xs text-primary">
                      {t.common.account} #{line.account_id}
                    </td>
                    <td
                      className={`cell-numeric text-xs ${
                        parseFloat(line.debit) > 0 ? 'text-debit' : 'text-subtle-foreground'
                      }`}
                    >
                      {fmt(line.debit)}
                    </td>
                    <td
                      className={`cell-numeric text-xs ${
                        parseFloat(line.credit) > 0 ? 'text-credit' : 'text-subtle-foreground'
                      }`}
                    >
                      {fmt(line.credit)}
                    </td>
                    <td className="max-w-[200px] truncate text-xs text-muted-foreground">
                      {line.description || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile stacked */}
          <div className="divide-y divide-border-subtle sm:hidden">
            {lines.map((line) => (
              <div key={line.id} className="flex items-start justify-between gap-3 px-3 py-2.5">
                <div className="min-w-0">
                  <span className="numeric text-xs text-primary">
                    {t.common.account} #{line.account_id}
                  </span>
                  <p className="mt-0.5 truncate text-[11px] text-subtle-foreground">
                    #{line.line_no}
                    {line.description ? ` · ${line.description}` : ''}
                  </p>
                </div>
                <div className="flex-shrink-0 text-end">
                  {parseFloat(line.debit) > 0 && (
                    <p className="numeric text-xs text-debit">
                      {t.journals.debit} {fmt(line.debit)}
                    </p>
                  )}
                  {parseFloat(line.credit) > 0 && (
                    <p className="numeric text-xs text-credit">
                      {t.journals.credit} {fmt(line.credit)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
