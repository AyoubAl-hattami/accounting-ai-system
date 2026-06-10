import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Building2, Save, Edit3, AlertCircle, HelpCircle, Lock, Globe } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import { useCompanySettings } from './useCompanySettings';
import { useI18n } from '../../i18n';
import { useToast } from '../../components/feedback/useToast';
import type { Language } from '../../i18n/types';

export default function SettingsPage() {
  const { t } = useI18n();
  return (
    <PageLayout
      pageTitle={t.settingsPage.pageTitle}
      pageSubtitle={t.settingsPage.pageSubtitle}
      activePath="/settings"
    >
      {({ selectedCompanyId, companiesLoading }) => (
        <SettingsContent
          selectedCompanyId={selectedCompanyId}
          companiesLoading={companiesLoading}
        />
      )}
    </PageLayout>
  );
}

interface SettingsContentProps {
  selectedCompanyId: number | null;
  companiesLoading: boolean;
}

function SettingsContent({ selectedCompanyId, companiesLoading }: SettingsContentProps) {
  const { t, language, setLanguage } = useI18n();
  const toast = useToast();
  const [isEditing, setIsEditing] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [registrationNo, setRegistrationNo] = useState('');
  const [taxNo, setTaxNo] = useState('');
  const [baseCurrency, setBaseCurrency] = useState('USD');
  const [address, setAddress] = useState('');

  const {
    company,
    isLoading,
    error,
    statusCode,
    fetchCompany,
    updateCompany,
    isSubmitting,
    submitError,
    setSubmitError,
  } = useCompanySettings();

  useEffect(() => {
    if (selectedCompanyId) {
      fetchCompany(selectedCompanyId);
      setIsEditing(false);
    }
  }, [selectedCompanyId, fetchCompany]);

  // Sync form states when company data is fetched
  useEffect(() => {
    if (company) {
      setName(company.name || '');
      setLegalName(company.legal_name || '');
      setRegistrationNo(company.registration_no || '');
      setTaxNo(company.tax_no || '');
      setBaseCurrency(company.base_currency || 'USD');
      setAddress(company.address || '');
    }
  }, [company]);

  const handleCancel = () => {
    if (company) {
      setName(company.name || '');
      setLegalName(company.legal_name || '');
      setRegistrationNo(company.registration_no || '');
      setTaxNo(company.tax_no || '');
      setBaseCurrency(company.base_currency || 'USD');
      setAddress(company.address || '');
    }
    setSubmitError(null);
    setIsEditing(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompanyId) return;

    if (!name.trim()) {
      setSubmitError(t.settingsPage.companyNameRequired);
      return;
    }

    if (!baseCurrency.trim() || baseCurrency.length !== 3) {
      setSubmitError(t.settingsPage.currencyInvalid);
      return;
    }

    const payload = {
      name: name.trim(),
      legal_name: legalName.trim() || null,
      registration_no: registrationNo.trim() || null,
      tax_no: taxNo.trim() || null,
      base_currency: baseCurrency.trim().toUpperCase(),
      address: address.trim() || null,
    };

    const updated = await updateCompany(selectedCompanyId, payload);
    if (updated) {
      setIsEditing(false);
      toast.success(t.settingsPage.updateSuccess);
    }
  };

  if (companiesLoading) {
    return <LoadingState />;
  }

  if (!selectedCompanyId) {
    return (
      <EmptyState
        title={t.common.noCompanySelected}
        description={t.common.selectCompanyPrompt}
      />
    );
  }

  // Handle 403 Forbidden State Elegantly
  if (statusCode === 403) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-center py-20 px-4"
      >
        <div className="glass-panel p-8 max-w-md text-center border-red-500/10">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5 shadow-[0_0_15px_rgba(239,68,68,0.07)]">
            <Lock className="w-8 h-8 text-red-400 animate-pulse" />
          </div>
          <h3 className="text-white font-bold text-xl mb-3">{t.settingsPage.accessDenied}</h3>
          <p className="text-gray-400 text-sm leading-relaxed mb-6">
            {t.settingsPage.accessDeniedMessage}
          </p>
          <div className="text-xs text-gray-500 border-t border-white/[0.06] pt-4">
            {t.settingsPage.accessDeniedHelp}
          </div>
        </div>
      </motion.div>
    );
  }

  if (isLoading) {
    return <LoadingState />;
  }

  if (error || !company) {
    return <ErrorState message={error || t.common.somethingWentWrong} onRetry={() => fetchCompany(selectedCompanyId)} />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Main Form/Card */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel overflow-hidden"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/[0.01]">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Building2 className="w-5.5 h-5.5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">{t.settingsPage.companyProfile}</h3>
                <p className="text-xs text-gray-500">{t.settingsPage.companyProfileDesc}</p>
              </div>
            </div>

            {!isEditing ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08] hover:border-white/[0.1] text-gray-300 hover:text-white text-xs font-semibold transition-all duration-200"
              >
                <Edit3 className="w-3.5 h-3.5" />
                {t.settingsPage.editSettings}
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 rounded-xl border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-gray-400 hover:text-gray-200 bg-white/[0.02] transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center gap-1.5 px-4.5 py-2 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-500/25 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  <Save className="w-3.5 h-3.5" />
                  {isSubmitting ? t.settingsPage.saving : t.settingsPage.saveChanges}
                </button>
              </div>
            )}
          </div>

          {/* Form Content */}
          <div className="p-6 space-y-6">
            {submitError && (
              <motion.div
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start gap-2.5"
              >
                <AlertCircle className="w-4.5 h-4.5 shrink-0 text-red-400" />
                <div>
                  <span className="font-semibold block">{t.settingsPage.errorUpdating}</span>
                  <span>{submitError}</span>
                </div>
              </motion.div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Company Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400 block">
                  {t.settingsPage.companyName} <span className="text-red-400">*</span>
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all"
                  />
                ) : (
                  <span className="text-white text-sm block py-1 font-medium">{company.name || '—'}</span>
                )}
              </div>

              {/* Legal Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400 block">{t.settingsPage.legalName}</label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.legalNamePlaceholder}
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all"
                  />
                ) : (
                  <span className="text-white text-sm block py-1 font-medium">{company.legal_name || '—'}</span>
                )}
              </div>

              {/* Registration Number */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400 block">{t.settingsPage.registrationNo}</label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.registrationNoPlaceholder}
                    value={registrationNo}
                    onChange={(e) => setRegistrationNo(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all"
                  />
                ) : (
                  <span className="text-white text-sm font-mono block py-1 font-medium">{company.registration_no || '—'}</span>
                )}
              </div>

              {/* Tax ID */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400 block">{t.settingsPage.taxId}</label>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.taxIdPlaceholder}
                    value={taxNo}
                    onChange={(e) => setTaxNo(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all"
                  />
                ) : (
                  <span className="text-white text-sm font-mono block py-1 font-medium">{company.tax_no || '—'}</span>
                )}
              </div>

              {/* Currency */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1">
                  <label className="text-xs font-semibold text-gray-400 block">
                    {t.settingsPage.baseCurrency} <span className="text-red-400">*</span>
                  </label>
                  <div className="group relative">
                    <HelpCircle className="w-3.5 h-3.5 text-gray-500 hover:text-gray-300 cursor-pointer" />
                    <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-48 p-2 rounded-lg bg-slate-950 border border-white/[0.08] text-[10px] text-gray-400 leading-normal hidden group-hover:block z-10 shadow-xl">
                      {t.settingsPage.baseCurrencyHelp}
                    </span>
                  </div>
                </div>
                {isEditing ? (
                  <input
                    type="text"
                    required
                    maxLength={3}
                    placeholder={t.settingsPage.baseCurrencyPlaceholder}
                    value={baseCurrency}
                    onChange={(e) => setBaseCurrency(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all font-mono uppercase"
                  />
                ) : (
                  <span className="text-white text-sm font-semibold font-mono block py-1">{company.base_currency || 'USD'}</span>
                )}
              </div>

              {/* Address */}
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-xs font-semibold text-gray-400 block">{t.settingsPage.businessAddress}</label>
                {isEditing ? (
                  <textarea
                    rows={3}
                    placeholder={t.settingsPage.businessAddressPlaceholder}
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:bg-white/[0.05] focus:outline-none transition-all resize-none"
                  />
                ) : (
                  <span className="text-white text-sm block py-1 font-medium whitespace-pre-line leading-relaxed">
                    {company.address || '—'}
                  </span>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </form>

      {/* ── Language & Appearance Section ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass-panel overflow-hidden"
      >
        <div className="px-6 py-5 border-b border-white/[0.06] bg-white/[0.01]">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Globe className="w-5.5 h-5.5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">{t.settingsPage.languageAppearance}</h3>
              <p className="text-xs text-gray-500">{t.settingsPage.languageAppearanceDesc}</p>
            </div>
          </div>
        </div>

        <div className="p-6">
          <div className="max-w-md space-y-3">
            <label className="text-xs font-semibold text-gray-400 block">{t.settingsPage.language}</label>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setLanguage('en' as Language)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border text-sm font-semibold transition-all duration-200 ${
                  language === 'en'
                    ? 'bg-brand-500/10 border-brand-500/30 text-brand-400 shadow-lg shadow-brand-500/5'
                    : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:bg-white/[0.04] hover:border-white/[0.1] hover:text-gray-200'
                }`}
              >
                <span className="text-lg">🇺🇸</span>
                <span>{t.settingsPage.english}</span>
              </button>
              <button
                type="button"
                onClick={() => setLanguage('ar' as Language)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl border text-sm font-semibold transition-all duration-200 ${
                  language === 'ar'
                    ? 'bg-brand-500/10 border-brand-500/30 text-brand-400 shadow-lg shadow-brand-500/5'
                    : 'bg-white/[0.02] border-white/[0.06] text-gray-400 hover:bg-white/[0.04] hover:border-white/[0.1] hover:text-gray-200'
                }`}
              >
                <span className="text-lg">🇸🇦</span>
                <span>{t.settingsPage.arabic}</span>
              </button>
            </div>
            <p className="text-[11px] text-gray-500 leading-relaxed">
              {t.settingsPage.languageHelp}
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
