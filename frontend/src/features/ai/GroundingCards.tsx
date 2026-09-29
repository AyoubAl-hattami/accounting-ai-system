import type React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ExternalLink } from 'lucide-react';
import type { GeminiMessage } from './useGeminiAssistant';

type Period = { start_date: string | null; end_date: string | null; label: string };
type ProfitLoss = { status: 'grounded'; kind: 'profit_and_loss'; requested_metric: 'revenue' | 'expenses' | 'net_profit'; period: Period; metrics: Record<'revenue' | 'expenses' | 'net_profit', string>; reference: { type: 'report'; report: 'profit_and_loss'; filters: { start_date: string | null; end_date: string | null } } };
type Entry = { journal_entry_id: number; entry_number: string; entry_date: string; description: string | null; status: string; source: string | null; creator_name: string | null; matched_amount: string; match_reason: string };
type Evidence = { status: 'grounded'; kind: 'journal_evidence'; basis: 'amount_trace' | 'profit_and_loss_contribution'; metric?: 'revenue' | 'expenses' | 'net_profit'; period?: Period; summary: { total_matches: number; returned_matches: number; has_more: boolean }; entries: Entry[] };

// The four kinds below were produced by the backend from 2026-07-16 and
// dropped here by valid() until 2026-09-24. See docs/open-findings.md RAG-15.
type AsOfPeriod = { as_of_date?: string | null; start_date?: string | null; end_date?: string | null; label: string };
type Metrics = Record<string, string | boolean>;
type BalanceSheet = { status: 'grounded'; kind: 'balance_sheet'; period: AsOfPeriod; metrics: Metrics; sections: { section: string; total: string; accounts: unknown[] }[]; reference: { type: 'report'; report: 'balance_sheet'; filters: Record<string, string | null> } };
type TrialBalance = { status: 'grounded'; kind: 'trial_balance'; period: AsOfPeriod; metrics: Metrics; accounts: unknown[]; summary: { total_accounts: number; returned_accounts: number; has_more: boolean }; reference: { type: 'report'; report: 'trial_balance'; filters: Record<string, string | null> } };
type LedgerAccountRow = { account_code: string; account_name: string; opening_balance: string; total_debit: string; total_credit: string; closing_balance: string; entry_count: number };
type GeneralLedger = { status: 'grounded'; kind: 'general_ledger'; period: AsOfPeriod; accounts: LedgerAccountRow[]; summary: { total_accounts: number; returned_accounts: number; has_more: boolean }; reference: { type: 'report'; report: 'general_ledger'; filters: Record<string, string | null> } };
type LedgerEntry = { journal_entry_id: number; entry_number: string; entry_date: string; description: string; status: string; debit: string; credit: string; running_balance: string };
type AccountLedger = { status: 'grounded'; kind: 'account_ledger'; period: AsOfPeriod; account: { account_id: number; account_code: string; account_name: string; account_type: string }; metrics: Metrics; entries: LedgerEntry[]; summary: { total_entries: number; returned_entries: number; has_more: boolean }; reference: { type: 'report'; report: 'account_ledger'; filters: Record<string, string | null> } };
type Grounded = ProfitLoss | Evidence | BalanceSheet | TrialBalance | GeneralLedger | AccountLedger;

function validDate(value: unknown): value is string | null { return value === null || (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)); }
function valid(value: unknown): value is Grounded {
  if (!value || typeof value !== 'object') return false;
  const g = value as Record<string, unknown>;
  if (g.status !== 'grounded') return false;
  if (g.kind === 'profit_and_loss') {
    const p = g.period as Record<string, unknown> | undefined;
    const m = g.metrics as Record<string, unknown> | undefined;
    const r = g.reference as Record<string, unknown> | undefined;
    return ['revenue', 'expenses', 'net_profit'].includes(String(g.requested_metric)) && !!p && validDate(p.start_date) && validDate(p.end_date) && typeof p.label === 'string' && !!m && ['revenue', 'expenses', 'net_profit'].every((k) => typeof m[k] === 'string') && !!r && r.type === 'report' && r.report === 'profit_and_loss';
  }
  // A card renders only when the shape it needs is all there: a half-rendered
  // card beside a "Verified" badge is worse than no card.
  const metricsAre = (keys: string[]) => { const m = g.metrics as Record<string, unknown> | undefined; return !!m && keys.every((k) => typeof m[k] === 'string'); };
  const periodLabelled = () => { const p = g.period as Record<string, unknown> | undefined; return !!p && typeof p.label === 'string'; };
  const countsAre = (keys: string[]) => { const summary = g.summary as Record<string, unknown> | undefined; return !!summary && keys.every((k) => Number.isInteger(summary[k])) && typeof summary.has_more === 'boolean'; };
  if (g.kind === 'balance_sheet') return periodLabelled() && metricsAre(['total_assets', 'total_liabilities', 'total_equity']) && Array.isArray(g.sections);
  if (g.kind === 'trial_balance') return periodLabelled() && metricsAre(['total_debit', 'total_credit', 'difference']) && countsAre(['total_accounts', 'returned_accounts']);
  if (g.kind === 'general_ledger') return periodLabelled() && Array.isArray(g.accounts) && countsAre(['total_accounts', 'returned_accounts']);
  if (g.kind === 'account_ledger') { const a = g.account as Record<string, unknown> | undefined; return periodLabelled() && !!a && typeof a.account_code === 'string' && metricsAre(['opening_balance', 'total_debit', 'total_credit', 'closing_balance']) && Array.isArray(g.entries) && countsAre(['total_entries', 'returned_entries']); }
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
  const money = (value: string | boolean | undefined) => (typeof value === 'string' ? value : String(value ?? ''));
  const openReport = (path: string, filters: Record<string, string | null>) => () => { const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); }); navigate(`${path}${params.toString() ? `?${params}` : ''}`); };
  const Shell = ({ title, subtitle, rows, onOpen, openLabel, children }: { title: string; subtitle?: string; rows?: [string, string][]; onOpen: () => void; openLabel: string; children?: React.ReactNode }) => (
    <div className="mt-2 space-y-2 rounded-lg border border-success-border bg-success-soft p-3" dir={dir}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><div className="font-semibold text-success">{title}</div>{subtitle ? <div className="text-[11px] text-muted-foreground">{subtitle}</div> : null}</div>
        <span className="flex items-center gap-1 text-[10px] text-success"><CheckCircle2 className="h-3 w-3" />{text(ar, 'Verified from accounting data', 'تم التحقق من بيانات النظام')}</span>
      </div>
      {rows ? <div className="space-y-1">{rows.map(([label, value]) => <div key={label} className="flex w-full min-w-0 items-center justify-between gap-3 rounded-lg px-2 py-1.5"><span className="min-w-0 flex-1 break-words text-xs text-muted-foreground">{label}</span><span className="shrink-0 whitespace-nowrap font-mono text-xs text-foreground">{value}</span></div>)}</div> : null}
      {children}
      <button type="button" onClick={onOpen} className="inline-flex items-center gap-1 rounded-lg border border-primary-border px-2.5 py-1.5 text-xs font-semibold text-primary hover:bg-primary-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"><ExternalLink className="h-3.5 w-3.5" />{openLabel}</button>
    </div>
  );

  if (grounding.kind === 'balance_sheet') {
    const m = grounding.metrics;
    return <Shell title={text(ar, 'Balance Sheet', 'الميزانية العمومية')} subtitle={grounding.period.label}
      rows={[[text(ar, 'Assets', 'الأصول'), money(m.total_assets)], [text(ar, 'Liabilities', 'الالتزامات'), money(m.total_liabilities)], [text(ar, 'Equity', 'حقوق الملكية'), money(m.total_equity)], [text(ar, 'Balanced', 'متوازنة'), m.is_balanced ? text(ar, 'Yes', 'نعم') : text(ar, 'No', 'لا')]]}
      onOpen={openReport('/reports/balance-sheet', grounding.reference.filters)} openLabel={text(ar, 'Open Balance Sheet', 'فتح الميزانية العمومية')} />;
  }
  if (grounding.kind === 'trial_balance') {
    const m = grounding.metrics;
    return <Shell title={text(ar, 'Trial Balance', 'ميزان المراجعة')} subtitle={grounding.period.label}
      rows={[[text(ar, 'Total debit', 'إجمالي المدين'), money(m.total_debit)], [text(ar, 'Total credit', 'إجمالي الدائن'), money(m.total_credit)], [text(ar, 'Difference', 'الفرق'), money(m.difference)], [text(ar, 'Balanced', 'متوازن'), m.is_balanced ? text(ar, 'Yes', 'نعم') : text(ar, 'No', 'لا')]]}
      onOpen={openReport('/reports/trial-balance', grounding.reference.filters)} openLabel={text(ar, 'Open Trial Balance', 'فتح ميزان المراجعة')} />;
  }
  if (grounding.kind === 'general_ledger') {
    const { total_accounts: totalAccounts, returned_accounts: shownAccounts, has_more: moreAccounts } = grounding.summary;
    return <Shell title={text(ar, 'General Ledger', 'دفتر الأستاذ العام')} subtitle={grounding.period.label}
      onOpen={openReport('/reports/general-ledger', grounding.reference.filters)} openLabel={text(ar, 'Open General Ledger', 'فتح دفتر الأستاذ العام')}>
      <div className="text-[11px] text-muted-foreground">{moreAccounts ? text(ar, `Showing ${shownAccounts} of ${totalAccounts} accounts.`, `يتم عرض ${shownAccounts} من أصل ${totalAccounts} حساباً.`) : text(ar, `${totalAccounts} accounts.`, `${totalAccounts} حساباً.`)}</div>
      <div className="space-y-1">{grounding.accounts.slice(0, 8).map((row) => <div key={row.account_code} className="flex w-full min-w-0 items-center justify-between gap-3 rounded-lg px-2 py-1.5"><span className="min-w-0 flex-1 break-words text-xs text-muted-foreground"><span className="font-mono">{row.account_code}</span> {row.account_name}</span><span className="shrink-0 whitespace-nowrap font-mono text-xs text-foreground">{row.closing_balance}</span></div>)}</div>
    </Shell>;
  }
  if (grounding.kind === 'account_ledger') {
    const m = grounding.metrics;
    const { total_entries: totalEntries, returned_entries: shownEntries, has_more: moreEntries } = grounding.summary;
    return <Shell title={`${text(ar, 'Account Ledger', 'دفتر أستاذ الحساب')} — ${grounding.account.account_code} ${grounding.account.account_name}`} subtitle={grounding.period.label}
      rows={[[text(ar, 'Opening balance', 'الرصيد الافتتاحي'), money(m.opening_balance)], [text(ar, 'Total debit', 'إجمالي المدين'), money(m.total_debit)], [text(ar, 'Total credit', 'إجمالي الدائن'), money(m.total_credit)], [text(ar, 'Closing balance', 'الرصيد الختامي'), money(m.closing_balance)]]}
      onOpen={openReport('/reports/account-ledger', grounding.reference.filters)} openLabel={text(ar, 'Open Account Ledger', 'فتح دفتر أستاذ الحساب')}>
      {moreEntries ? <div className="text-[11px] text-warning">{text(ar, `Showing ${shownEntries} of ${totalEntries} entries.`, `يتم عرض ${shownEntries} من أصل ${totalEntries} قيد.`)}</div> : null}
      <div className="space-y-1">{grounding.entries.slice(0, 5).map((entry) => <div key={entry.journal_entry_id} className="rounded-lg border border-border bg-surface-muted p-2 text-xs"><div className="flex items-start justify-between gap-2"><span className="min-w-0 truncate font-mono font-semibold text-primary">{entry.entry_number}</span><span className="shrink-0 text-subtle-foreground">{new Date(entry.entry_date).toLocaleDateString()}</span></div><div className="mt-1 flex flex-wrap gap-x-3 text-muted-foreground"><span>{text(ar, 'Status', 'الحالة')}: {status(entry.status, ar)}</span><span>{text(ar, 'Debit', 'مدين')}: <b className="font-mono text-foreground">{entry.debit}</b></span><span>{text(ar, 'Credit', 'دائن')}: <b className="font-mono text-foreground">{entry.credit}</b></span><span>{text(ar, 'Balance', 'الرصيد')}: <b className="font-mono text-foreground">{entry.running_balance}</b></span></div></div>)}</div>
    </Shell>;
  }
  const { total_matches: total, returned_matches: returned, has_more: more } = grounding.summary;
  return <div className="mt-2 space-y-2" dir={dir}><div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground"><span>{total === 0 ? text(ar, 'No matching journal entries found.', 'لم يتم العثور على قيود مطابقة.') : text(ar, `${total} matching journal entries found.`, `تم العثور على ${total} قيود مطابقة.`)}</span>{more && <span className="text-warning">{text(ar, `Showing ${returned} of ${total}.`, `يتم عرض ${returned} من أصل ${total}.`)}</span>}</div>{grounding.entries.map((entry) => <article key={entry.journal_entry_id} className="rounded-lg border border-border bg-surface-muted p-2.5 text-xs"><div className="flex items-start justify-between gap-2"><span className="min-w-0 truncate font-mono font-semibold text-primary" title={entry.entry_number}>{entry.entry_number}</span><span className="shrink-0 text-subtle-foreground">{new Date(entry.entry_date).toLocaleDateString()}</span></div><div className="mt-1 truncate text-foreground" title={entry.description || undefined}>{entry.description || text(ar, 'Not available', 'غير متوفر')}</div><div className="mt-1 grid gap-x-2 gap-y-1 text-muted-foreground sm:grid-cols-2"><span>{text(ar, 'Status', 'الحالة')}: {status(entry.status, ar)}</span><span>{text(ar, 'Source', 'المصدر')}: {source(entry.source, ar)}</span><span>{text(ar, 'By', 'بواسطة')}: {entry.creator_name || text(ar, 'Not available', 'غير متوفر')}</span><span>{text(ar, 'Contribution', 'المساهمة')}: <b className="font-mono text-foreground">{entry.matched_amount}</b></span><span className="sm:col-span-2">{text(ar, 'Match', 'سبب المطابقة')}: {reason(entry.match_reason, ar)}</span></div><button type="button" onClick={() => navigate(`/journal-entries?entry_id=${encodeURIComponent(String(entry.journal_entry_id))}`)} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-primary-border px-2.5 py-1.5 font-semibold text-primary hover:bg-primary-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"><ExternalLink className="h-3.5 w-3.5" />{text(ar, 'Open entry', 'فتح القيد')}</button></article>)}</div>;
}
