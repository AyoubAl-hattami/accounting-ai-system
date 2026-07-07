import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  ChevronDown,
  ChevronRight,
  Plus,
  Zap,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import { useToast } from '../../components/feedback/useToast';
import { useFiscalSettings } from './useFiscalSettings';
import type { QuickSetupResult } from './useFiscalSettings';

interface FiscalSettingsSectionProps {
  companyId: number;
}

export default function FiscalSettingsSection({ companyId }: FiscalSettingsSectionProps) {
  const { t, language } = useI18n();
  const toast = useToast();
  const {
    fiscalYears,
    fiscalPeriods,
    isLoading,
    error,
    isQuickSetupLoading,
    quickSetupResult,
    expandedYears,
    toggleYear,
    fetchFiscalYears,
    fetchFiscalPeriods,
    createFiscalYear,
    createFiscalPeriod,
    quickSetupToday,
    setQuickSetupResult,
  } = useFiscalSettings();

  const [showCreateYear, setShowCreateYear] = useState(false);
  const [showCreatePeriod, setShowCreatePeriod] = useState<number | null>(null);

  // Create year form
  const [yearName, setYearName] = useState('');
  const [yearStart, setYearStart] = useState('');
  const [yearEnd, setYearEnd] = useState('');
  const [yearSubmitting, setYearSubmitting] = useState(false);

  // Create period form
  const [periodName, setPeriodName] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [periodNo, setPeriodNo] = useState(1);
  const [periodSubmitting, setPeriodSubmitting] = useState(false);

  useEffect(() => {
    if (companyId) {
      fetchFiscalYears(companyId);
    }
  }, [companyId, fetchFiscalYears]);

  const handleToggleYear = useCallback((yearId: number) => {
    toggleYear(yearId);
    if (!fiscalPeriods[yearId]) {
      fetchFiscalPeriods(companyId, yearId);
    }
  }, [toggleYear, fiscalPeriods, fetchFiscalPeriods, companyId]);

  const handleQuickSetup = async () => {
    try {
      const result = await quickSetupToday(companyId);
      if (result) {
        const msg = buildQuickSetupMessage(result);
        toast.success(msg);
        // Auto-expand the created/found fiscal year
        if (result.fiscal_year?.id) {
          toggleYear(result.fiscal_year.id);
          fetchFiscalPeriods(companyId, result.fiscal_year.id);
        }
      }
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message || 'Failed');
    }
  };

  const buildQuickSetupMessage = (result: QuickSetupResult): string => {
    const parts: string[] = [];
    if (language === 'ar') {
      if (result.fiscal_year_created) parts.push(`تم إنشاء السنة المالية: ${result.fiscal_year.name}`);
      else parts.push(`السنة المالية موجودة: ${result.fiscal_year.name}`);
      if (result.fiscal_period_created) parts.push(`تم إنشاء الفترة المالية: ${result.fiscal_period.name}`);
      else parts.push(`الفترة المالية موجودة: ${result.fiscal_period.name}`);
      if (result.fiscal_year_opened) parts.push('تم فتح السنة المالية');
      if (result.fiscal_period_opened) parts.push('تم فتح الفترة المالية');
    } else {
      if (result.fiscal_year_created) parts.push(`Created fiscal year: ${result.fiscal_year.name}`);
      else parts.push(`Fiscal year exists: ${result.fiscal_year.name}`);
      if (result.fiscal_period_created) parts.push(`Created fiscal period: ${result.fiscal_period.name}`);
      else parts.push(`Fiscal period exists: ${result.fiscal_period.name}`);
      if (result.fiscal_year_opened) parts.push('Fiscal year opened');
      if (result.fiscal_period_opened) parts.push('Fiscal period opened');
    }
    return parts.join(' • ');
  };

  const handleCreateYear = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!yearName.trim() || !yearStart || !yearEnd) return;
    setYearSubmitting(true);
    try {
      await createFiscalYear({
        company_id: companyId,
        name: yearName.trim(),
        start_date: yearStart,
        end_date: yearEnd,
        status: 'open',
      });
      toast.success(language === 'ar' ? 'تم إنشاء السنة المالية' : 'Fiscal year created');
      setShowCreateYear(false);
      setYearName('');
      setYearStart('');
      setYearEnd('');
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message);
    } finally {
      setYearSubmitting(false);
    }
  };

  const handleCreatePeriod = async (e: React.FormEvent, fiscalYearId: number) => {
    e.preventDefault();
    if (!periodName.trim() || !periodStart || !periodEnd) return;
    setPeriodSubmitting(true);
    try {
      await createFiscalPeriod({
        company_id: companyId,
        fiscal_year_id: fiscalYearId,
        period_no: periodNo,
        name: periodName.trim(),
        start_date: periodStart,
        end_date: periodEnd,
        status: 'open',
      });
      toast.success(language === 'ar' ? 'تم إنشاء الفترة المالية' : 'Fiscal period created');
      setShowCreatePeriod(null);
      setPeriodName('');
      setPeriodStart('');
      setPeriodEnd('');
      setPeriodNo(1);
    } catch (err: unknown) {
      const error = err as Error;
      toast.error(error.message);
    } finally {
      setPeriodSubmitting(false);
    }
  };

  const statusBadge = (status: string) => {
    const isOpen = status === 'open';
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
          isOpen
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${isOpen ? 'bg-emerald-400' : 'bg-red-400'}`} />
        {isOpen
          ? (language === 'ar' ? 'مفتوحة' : 'Open')
          : (language === 'ar' ? 'مغلقة' : 'Closed')
        }
      </span>
    );
  };

  const inputClass = 'w-full px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20 transition-colors';
  const labelClass = 'block text-xs font-semibold text-gray-400 mb-1';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="glass-panel overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/[0.01]">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <Calendar className="w-5.5 h-5.5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">{t.settingsPage.fiscalYearsAndPeriods}</h3>
            <p className="text-xs text-gray-500">{t.settingsPage.fiscalYearsDesc}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleQuickSetup}
            disabled={isQuickSetupLoading}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-amber-500/25 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {isQuickSetupLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Zap className="w-3.5 h-3.5" />
            )}
            {t.settingsPage.createFiscalPeriodForToday}
          </button>
          <button
            type="button"
            onClick={() => setShowCreateYear(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] hover:border-white/[0.1] text-gray-300 hover:text-white text-xs font-semibold transition-all duration-200"
          >
            <Plus className="w-3.5 h-3.5" />
            {t.settingsPage.createFiscalYear}
          </button>
        </div>
      </div>

      {/* Quick Setup Result */}
      <AnimatePresence>
        {quickSetupResult && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mx-6 mt-4 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              <div className="flex-1 text-xs text-emerald-300 leading-relaxed">
                {t.settingsPage.fiscalSetupComplete}
                <div className="mt-1 text-emerald-400/70">
                  {quickSetupResult.fiscal_year.name} → {quickSetupResult.fiscal_period.name}
                </div>
              </div>
              <button onClick={() => setQuickSetupResult(null)} className="text-emerald-400/50 hover:text-emerald-300 transition-colors">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Create Year Form */}
      <AnimatePresence>
        {showCreateYear && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <form onSubmit={handleCreateYear} className="m-6 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-3">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-bold text-white">{t.settingsPage.createFiscalYear}</h4>
                <button type="button" onClick={() => setShowCreateYear(false)} className="text-gray-500 hover:text-gray-300">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>{t.settingsPage.fiscalYearName}</label>
                  <input value={yearName} onChange={(e) => setYearName(e.target.value)} placeholder="FY 2026" className={inputClass} required />
                </div>
                <div>
                  <label className={labelClass}>{t.settingsPage.startDate}</label>
                  <input type="date" value={yearStart} onChange={(e) => setYearStart(e.target.value)} className={inputClass} required />
                </div>
                <div>
                  <label className={labelClass}>{t.settingsPage.endDate}</label>
                  <input type="date" value={yearEnd} onChange={(e) => setYearEnd(e.target.value)} className={inputClass} required />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setShowCreateYear(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors">
                  {language === 'ar' ? 'إلغاء' : 'Cancel'}
                </button>
                <button type="submit" disabled={yearSubmitting} className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-40 transition-colors">
                  {yearSubmitting ? (language === 'ar' ? 'جاري الإنشاء...' : 'Creating...') : (language === 'ar' ? 'إنشاء' : 'Create')}
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      <div className="p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 py-6 justify-center text-red-400 text-sm">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        ) : fiscalYears.length === 0 ? (
          <div className="text-center py-10">
            <Calendar className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-400 mb-1">{t.settingsPage.noFiscalYears}</p>
            <p className="text-xs text-gray-500">{t.settingsPage.noFiscalYearsHelp}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {fiscalYears.map((fy) => (
              <div key={fy.id} className="rounded-xl border border-white/[0.06] overflow-hidden bg-white/[0.01]">
                {/* Year row */}
                <button
                  type="button"
                  onClick={() => handleToggleYear(fy.id)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors text-left"
                >
                  {expandedYears.has(fy.id) ? (
                    <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-semibold text-white">{fy.name}</span>
                    <span className="text-[11px] text-gray-500 mx-2">
                      {fy.start_date} → {fy.end_date}
                    </span>
                  </div>
                  {statusBadge(fy.status)}
                </button>

                {/* Periods */}
                <AnimatePresence>
                  {expandedYears.has(fy.id) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-white/[0.04] px-4 pb-3">
                        {/* Period list */}
                        {(fiscalPeriods[fy.id] || []).length === 0 ? (
                          <p className="text-xs text-gray-500 py-3 ps-8">{t.settingsPage.noFiscalPeriods}</p>
                        ) : (
                          <div className="mt-2 space-y-1">
                            {(fiscalPeriods[fy.id] || []).map((fp) => (
                              <div key={fp.id} className="flex items-center gap-3 px-3 py-2 ps-8 rounded-lg hover:bg-white/[0.02] transition-colors">
                                <div className="flex-1 min-w-0">
                                  <span className="text-xs font-medium text-gray-300">{fp.name}</span>
                                  <span className="text-[10px] text-gray-500 mx-2">
                                    {fp.start_date} → {fp.end_date}
                                  </span>
                                </div>
                                {statusBadge(fp.status)}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Add period button */}
                        {showCreatePeriod === fy.id ? (
                          <form onSubmit={(e) => handleCreatePeriod(e, fy.id)} className="mt-3 ms-8 p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] space-y-2">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                              <div>
                                <label className={labelClass}>{t.settingsPage.periodName}</label>
                                <input value={periodName} onChange={(e) => setPeriodName(e.target.value)} placeholder="July 2026" className={inputClass} required />
                              </div>
                              <div>
                                <label className={labelClass}>{t.settingsPage.startDate}</label>
                                <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} className={inputClass} required />
                              </div>
                              <div>
                                <label className={labelClass}>{t.settingsPage.endDate}</label>
                                <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} className={inputClass} required />
                              </div>
                              <div>
                                <label className={labelClass}>{t.settingsPage.periodNo}</label>
                                <input type="number" min={1} max={12} value={periodNo} onChange={(e) => setPeriodNo(Number(e.target.value))} className={inputClass} required />
                              </div>
                            </div>
                            <div className="flex justify-end gap-2">
                              <button type="button" onClick={() => setShowCreatePeriod(null)} className="px-3 py-1 text-xs text-gray-400 hover:text-gray-200 transition-colors">
                                {language === 'ar' ? 'إلغاء' : 'Cancel'}
                              </button>
                              <button type="submit" disabled={periodSubmitting} className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-40 transition-colors">
                                {periodSubmitting ? '...' : (language === 'ar' ? 'إنشاء' : 'Create')}
                              </button>
                            </div>
                          </form>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setShowCreatePeriod(fy.id)}
                            className="mt-2 ms-8 inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
                          >
                            <Plus className="w-3 h-3" />
                            {t.settingsPage.createFiscalPeriod}
                          </button>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
