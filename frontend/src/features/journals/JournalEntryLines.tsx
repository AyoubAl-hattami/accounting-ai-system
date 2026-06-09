import { motion } from 'framer-motion';
import type { JournalLine } from '../../api/types';
import { useI18n } from '../../i18n';

interface JournalEntryLinesProps {
  lines: JournalLine[];
}

function fmt(v: string): string {
  const n = parseFloat(v);
  if (isNaN(n) || n === 0) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function JournalEntryLines({ lines }: JournalEntryLinesProps) {
  const { t } = useI18n();
  if (lines.length === 0) {
    return (
      <p className="text-xs text-gray-500 text-center py-4">No lines for this entry.</p>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="overflow-hidden"
    >
      <div className="px-4 pb-4 pt-1">
        <div className="rounded-xl bg-white/[0.02] border border-white/[0.04] overflow-hidden">
          {/* Desktop table */}
          <table className="w-full hidden sm:table">
            <thead>
              <tr className="border-b border-white/[0.05]">
                <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-3 py-2">#</th>
                <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-3 py-2">{t.common.account}</th>
                <th className="text-right text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-3 py-2">{t.reports.trialBalance.debit}</th>
                <th className="text-right text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-3 py-2">{t.reports.trialBalance.credit}</th>
                <th className="text-left text-[9px] uppercase tracking-wider font-semibold text-gray-600 px-3 py-2">{t.common.description}</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => (
                <tr key={line.id} className="border-b border-white/[0.02] last:border-0">
                  <td className="px-3 py-2 text-xs text-gray-500">{line.line_no}</td>
                  <td className="px-3 py-2 text-xs font-mono text-brand-400">#{line.account_id}</td>
                  <td className="px-3 py-2 text-xs text-right font-mono">
                    <span className={parseFloat(line.debit) > 0 ? 'text-emerald-400' : 'text-gray-600'}>
                      {fmt(line.debit)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-right font-mono">
                    <span className={parseFloat(line.credit) > 0 ? 'text-red-400' : 'text-gray-600'}>
                      {fmt(line.credit)}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500 truncate max-w-[180px]">{line.description || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile stacked */}
          <div className="sm:hidden divide-y divide-white/[0.03]">
            {lines.map((line) => (
              <div key={line.id} className="px-3 py-2.5 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-gray-600 mr-2">#{line.line_no}</span>
                  <span className="text-xs font-mono text-brand-400">Acc #{line.account_id}</span>
                  {line.description && (
                    <p className="text-[10px] text-gray-500 mt-0.5 truncate max-w-[160px]">{line.description}</p>
                  )}
                </div>
                <div className="text-right">
                  {parseFloat(line.debit) > 0 && (
                    <p className="text-xs font-mono text-emerald-400">Dr {fmt(line.debit)}</p>
                  )}
                  {parseFloat(line.credit) > 0 && (
                    <p className="text-xs font-mono text-red-400">Cr {fmt(line.credit)}</p>
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
