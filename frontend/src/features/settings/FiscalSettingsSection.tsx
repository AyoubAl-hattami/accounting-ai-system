import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  Lock as LockIcon,
  Plus,
  Unlock,
  X,
  Zap,
} from 'lucide-react';
import { useI18n } from '../../i18n';
import SectionCard from '../../components/ui/SectionCard';
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
      <span className={`badge badge-uppercase ${isOpen ? 'tone-success' : 'tone-danger'}`}>
        {isOpen ? <Unlock className="h-3 w-3" /> : <LockIcon className="h-3 w-3" />}
        {isOpen
          ? language === 'ar'
            ? 'مفتوحة'
            : 'Open'
          : language === 'ar'
            ? 'مغلقة'
            : 'Closed'}
      </span>
    );
  };

  const inputClass = 'input';
  const labelClass = 'field-label';

  return (
    <SectionCard
      icon={Calendar}
      title={t.settingsPage.fiscalYearsAndPeriods}
      description={t.settingsPage.fiscalYearsDesc}
      tone="warning"
      delay={0.05}
      actions={
        <>
          <button
            type="button"
            onClick={handleQuickSetup}
            disabled={isQuickSetupLoading}
            className="btn btn-secondary btn-sm"
          >
            {isQuickSetupLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Zap className="h-3.5 w-3.5" />
            )}
            {t.settingsPage.createFiscalPeriodForToday}
          </button>
          <button
            type="button"
            onClick={() => setShowCreateYear(true)}
            className="btn btn-primary btn-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            {t.settingsPage.createFiscalYear}
          </button>
        </>
      }
    >
      {/* Quick Setup Result */}
      <AnimatePresence>
        {quickSetupResult && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="callout tone-success mx-5 mt-5">
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div className="flex-1 text-xs leading-relaxed">
                {t.settingsPage.fiscalSetupComplete}
                <div className="mt-1 opacity-80">
                  {quickSetupResult.fiscal_year.name} → {quickSetupResult.fiscal_period.name}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setQuickSetupResult(null)}
                aria-label={t.common.close}
                className="-m-1 rounded-md p-1 opacity-70 transition-opacity hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" />
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
            <form
              onSubmit={handleCreateYear}
              className="m-5 space-y-4 rounded-lg border border-border bg-surface-muted p-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="section-title">{t.settingsPage.createFiscalYear}</h3>
                <button
                  type="button"
                  onClick={() => setShowCreateYear(false)}
                  aria-label={t.common.close}
                  className="-m-1 rounded-md p-1 text-subtle-foreground transition-colors hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateYear(false)}
                  className="btn btn-ghost btn-sm"
                >
                  {language === 'ar' ? 'إلغاء' : 'Cancel'}
                </button>
                <button type="submit" disabled={yearSubmitting} className="btn btn-primary btn-sm">
                  {yearSubmitting
                    ? language === 'ar'
                      ? 'جاري الإنشاء...'
                      : 'Creating...'
                    : language === 'ar'
                      ? 'إنشاء'
                      : 'Create'}
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      <div className="p-5">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="callout tone-danger" role="alert">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : fiscalYears.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border py-10 text-center">
            <Calendar className="mx-auto mb-3 h-8 w-8 text-subtle-foreground" />
            <p className="mb-1 text-sm font-medium text-foreground">
              {t.settingsPage.noFiscalYears}
            </p>
            <p className="text-xs text-muted-foreground">{t.settingsPage.noFiscalYearsHelp}</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {fiscalYears.map((fy) => (
              <div key={fy.id} className="overflow-hidden rounded-lg border border-border">
                {/* Year row */}
                <button
                  type="button"
                  onClick={() => handleToggleYear(fy.id)}
                  aria-expanded={expandedYears.has(fy.id)}
                  className="flex w-full items-center gap-3 bg-surface-muted px-4 py-3 text-start transition-colors hover:bg-surface-overlay"
                >
                  {expandedYears.has(fy.id) ? (
                    <ChevronDown className="h-4 w-4 flex-shrink-0 text-subtle-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 flex-shrink-0 text-subtle-foreground rtl:rotate-180" />
                  )}
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-semibold text-foreground">{fy.name}</span>
                    <span className="numeric mx-2 text-xs text-muted-foreground">
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
                      <div className="border-t border-border bg-surface px-4 py-3">
                        {/* Period list */}
                        {(fiscalPeriods[fy.id] || []).length === 0 ? (
                          <p className="py-2 ps-7 text-xs text-muted-foreground">
                            {t.settingsPage.noFiscalPeriods}
                          </p>
                        ) : (
                          <div className="divide-y divide-border-subtle">
                            {(fiscalPeriods[fy.id] || []).map((fp) => (
                              <div key={fp.id} className="flex items-center gap-3 py-2 ps-7">
                                <div className="min-w-0 flex-1">
                                  <span className="text-xs font-medium text-foreground">{fp.name}</span>
                                  <span className="numeric mx-2 text-xs text-subtle-foreground">
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
                          <form
                            onSubmit={(e) => handleCreatePeriod(e, fy.id)}
                            className="mt-3 space-y-3 rounded-lg border border-border bg-surface-muted p-3 ms-7"
                          >
                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
                              <button
                                type="button"
                                onClick={() => setShowCreatePeriod(null)}
                                className="btn btn-ghost btn-sm"
                              >
                                {language === 'ar' ? 'إلغاء' : 'Cancel'}
                              </button>
                              <button
                                type="submit"
                                disabled={periodSubmitting}
                                className="btn btn-primary btn-sm"
                              >
                                {periodSubmitting ? '...' : language === 'ar' ? 'إنشاء' : 'Create'}
                              </button>
                            </div>
                          </form>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setShowCreatePeriod(fy.id)}
                            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary transition-opacity hover:opacity-80 ms-7"
                          >
                            <Plus className="h-3 w-3" />
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
    </SectionCard>
  );
}
