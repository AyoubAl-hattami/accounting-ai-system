import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ExternalLink } from 'lucide-react';
import type { GeminiMessage } from './useGeminiAssistant';

type Period = { start_date: string | null; end_date: string | null; label: string };
type ProfitLoss = { status: 'grounded'; kind: 'profit_and_loss'; requested_metric: 'revenue' | 'expenses' | 'net_profit'; period: Period; metrics: Record<'revenue' | 'expenses' | 'net_profit', string>; reference: { type: 'report'; report: 'profit_and_loss'; filters: { start_date: string | null; end_date: string | null } } };
type Entry = { journal_entry_id: number; entry_number: string; entry_date: string; description: string | null; status: string; source: string | null; creator_name: string | null; matched_amount: string; match_reason: string };
type Evidence = { status: 'grounded'; kind: 'journal_evidence'; basis: 'amount_trace' | 'profit_and_loss_contribution'; metric?: 'revenue' | 'expenses' | 'net_profit'; period?: Period; summary: { total_matches: number; returned_matches: number; has_more: boolean }; entries: Entry[] };

function validDate(value: unknown): value is string | null { return value === null || (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)); }
function valid(value: unknown): value is ProfitLoss | Evidence {
  if (!value || typeof value !== 'object') return false;
  const g = value as Record<string, unknown>;
  if (g.status !== 'grounded') return false;
  if (g.kind === 'profit_and_loss') {
    const p = g.period as Record<string, unknown> | undefined;
    const m = g.metrics as Record<string, unknown> | undefined;
    const r = g.reference as Record<string, unknown> | undefined;
    return ['revenue', 'expenses', 'net_profit'].includes(String(g.requested_metric)) && !!p && validDate(p.start_date) && validDate(p.end_date) && typeof p.label === 'string' && !!m && ['revenue', 'expenses', 'net_profit'].every((k) => typeof m[k] === 'string') && !!r && r.type === 'report' && r.report === 'profit_and_loss';
  }
  if (g.kind !== 'journal_evidence' || !['amount_trace', 'profit_and_loss_contribution'].includes(String(g.basis))) return false;
  const s = g.summary as Record<string, unknown> | undefined;
  return !!s && Number.isInteger(s.total_matches) && Number.isInteger(s.returned_matches) && typeof s.has_more === 'boolean' && Array.isArray(g.entries) && g.entries.every((entry) => { const e = entry as Record<string, unknown>; return Number.isInteger(e.journal_entry_id) && typeof e.entry_number === 'string' && typeof e.entry_date === 'string' && typeof e.matched_amount === 'string'; });
}

const text = (ar: boolean, en: string, arabic: string) => ar ? arabic : en;
const source = (value: string | null, ar: boolean) => ({ manual: text(ar, 'Manual', 'يدوي'), gemini_assistant: 'Gemini', reversal: text(ar, 'Reversal', 'عكس القيد'), opening_balance: text(ar, 'Opening balance', 'رصيد افتتاحي') }[value || 'manual'] || value || text(ar, 'Not available', 'غير متوفر'));
const status = (value: string, ar: boolean) => ({ draft: text(ar, 'Draft', 'مسودة'), reviewed: text(ar, 'Reviewed', 'مراجع'), posted: text(ar, 'Posted', 'مرحّل'), void: text(ar, 'Void', 'ملغى'), reversed: text(ar, 'Reversed', 'معكوس') }[value] || value);
const reason = (value: string, ar: boolean) => ({ debit_line: text(ar, 'Debit line', 'مبلغ مدين'), credit_line: text(ar, 'Credit line', 'مبلغ دائن'), total_debit: text(ar, 'Total debit', 'إجمالي المدين'), total_credit: text(ar, 'Total credit', 'إجمالي الدائن'), report_revenue_contribution: text(ar, 'Revenue contribution', 'مساهمة في الإيرادات'), report_expense_contribution: text(ar, 'Expense contribution', 'مساهمة في المصروفات') }[value] || value);

export default function GroundingCards({ message, language, dir }: { message: GeminiMessage; language: 'en' | 'ar'; dir: 'ltr' | 'rtl' }) {
  const navigate = useNavigate();
  const grounding = message.metadata?.grounding;
  if (!valid(grounding)) return null;
  const ar = language === 'ar';
  const periodLabel = grounding && 'period' in grounding && grounding.period?.label.toLowerCase() === 'all available data' ? 'All available data' : grounding && 'period' in grounding ? grounding.period?.label : '';
  if (grounding.kind === 'profit_and_loss') {
    const open = () => { const params = new URLSearchParams(); if (grounding.reference.filters.start_date) params.set('start_date', grounding.reference.filters.start_date); if (grounding.reference.filters.end_date) params.set('end_date', grounding.reference.filters.end_date); navigate(`/reports/profit-and-loss${params.toString() ? `?${params}` : ''}`); };
    return <div className="mt-2 space-y-2 rounded-lg border border-success-border bg-success-soft p-3" dir={dir}><div className="flex flex-wrap items-start justify-between gap-2"><div><div className="font-semibold text-success">{text(ar, 'Profit and Loss', 'الأرباح والخسائر')}</div><div className="text-[11px] text-muted-foreground">{periodLabel}</div></div><span className="flex items-center gap-1 text-[10px] text-success"><CheckCircle2 className="h-3 w-3" />{text(ar, 'Verified from accounting data', 'تم التحقق من بيانات النظام')}</span></div><div className="space-y-1">{(['revenue', 'expenses', 'net_profit'] as const).map((key) => <div key={key} className={`flex w-full min-w-0 items-center justify-between gap-3 rounded-lg px-2 py-1.5 ${grounding.requested_metric === key ? 'bg-primary-soft ring-1 ring-ring-soft' : ''}`}><span className="min-w-0 flex-1 break-words text-xs text-muted-foreground">{text(ar, key === 'revenue' ? 'Revenue' : key === 'expenses' ? 'Expenses' : 'Net profit', key === 'revenue' ? 'الإيرادات' : key === 'expenses' ? 'المصروفات' : 'صافي الربح')}</span><span className="shrink-0 whitespace-nowrap font-mono text-xs text-foreground">{grounding.metrics[key]}</span></div>)}</div><button type="button" onClick={open} className="inline-flex items-center gap-1 rounded-lg border border-primary-border px-2.5 py-1.5 text-xs font-semibold text-primary hover:bg-primary-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"><ExternalLink className="h-3.5 w-3.5" />{text(ar, 'Open Profit and Loss', 'فتح تقرير الأرباح والخسائر')}</button></div>;
  }
  const { total_matches: total, returned_matches: returned, has_more: more } = grounding.summary;
  return <div className="mt-2 space-y-2" dir={dir}><div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground"><span>{total === 0 ? text(ar, 'No matching journal entries found.', 'لم يتم العثور على قيود مطابقة.') : text(ar, `${total} matching journal entries found.`, `تم العثور على ${total} قيود مطابقة.`)}</span>{more && <span className="text-warning">{text(ar, `Showing ${returned} of ${total}.`, `يتم عرض ${returned} من أصل ${total}.`)}</span>}</div>{grounding.entries.map((entry) => <article key={entry.journal_entry_id} className="rounded-lg border border-border bg-surface-muted p-2.5 text-xs"><div className="flex items-start justify-between gap-2"><span className="min-w-0 truncate font-mono font-semibold text-primary" title={entry.entry_number}>{entry.entry_number}</span><span className="shrink-0 text-subtle-foreground">{new Date(entry.entry_date).toLocaleDateString()}</span></div><div className="mt-1 truncate text-foreground" title={entry.description || undefined}>{entry.description || text(ar, 'Not available', 'غير متوفر')}</div><div className="mt-1 grid gap-x-2 gap-y-1 text-muted-foreground sm:grid-cols-2"><span>{text(ar, 'Status', 'الحالة')}: {status(entry.status, ar)}</span><span>{text(ar, 'Source', 'المصدر')}: {source(entry.source, ar)}</span><span>{text(ar, 'By', 'بواسطة')}: {entry.creator_name || text(ar, 'Not available', 'غير متوفر')}</span><span>{text(ar, 'Contribution', 'المساهمة')}: <b className="font-mono text-foreground">{entry.matched_amount}</b></span><span className="sm:col-span-2">{text(ar, 'Match', 'سبب المطابقة')}: {reason(entry.match_reason, ar)}</span></div><button type="button" onClick={() => navigate(`/journal-entries?entry_id=${encodeURIComponent(String(entry.journal_entry_id))}`)} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-primary-border px-2.5 py-1.5 font-semibold text-primary hover:bg-primary-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"><ExternalLink className="h-3.5 w-3.5" />{text(ar, 'Open entry', 'فتح القيد')}</button></article>)}</div>;
}
