import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, Building2, Edit3, Globe, HelpCircle, Lock, Save } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import LoadingState from '../../components/feedback/LoadingState';
import ErrorState from '../../components/feedback/ErrorState';
import EmptyState from '../../components/feedback/EmptyState';
import SectionCard from '../../components/ui/SectionCard';
import { ThemeSegmentedControl } from '../../components/ui/ThemeToggle';
import { useCompanySettings } from './useCompanySettings';
import FiscalSettingsSection from './FiscalSettingsSection';
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
        className="flex items-center justify-center px-4 py-20"
        role="alert"
      >
        <div className="card max-w-md p-8 text-center">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-lg border border-danger-border bg-danger-soft">
            <Lock className="h-6 w-6 text-danger" />
          </div>
          <h3 className="mb-2 text-base font-semibold text-foreground">
            {t.settingsPage.accessDenied}
          </h3>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {t.settingsPage.accessDeniedMessage}
          </p>
          <p className="mt-5 border-t border-border-subtle pt-4 text-xs text-subtle-foreground">
            {t.settingsPage.accessDeniedHelp}
          </p>
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
    <div className="mx-auto max-w-4xl space-y-6">
      <form onSubmit={handleSubmit}>
        <SectionCard
          icon={Building2}
          title={t.settingsPage.companyProfile}
          description={t.settingsPage.companyProfileDesc}
          actions={
            !isEditing ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="btn btn-secondary btn-sm"
              >
                <Edit3 className="h-3.5 w-3.5" />
                {t.settingsPage.editSettings}
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="btn btn-ghost btn-sm"
                >
                  {t.common.cancel}
                </button>
                <button type="submit" disabled={isSubmitting} className="btn btn-primary btn-sm">
                  <Save className="h-3.5 w-3.5" />
                  {isSubmitting ? t.settingsPage.saving : t.settingsPage.saveChanges}
                </button>
              </>
            )
          }
        >
          <div className="space-y-6 p-5">
            {submitError && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                role="alert"
                className="callout tone-danger"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>
                  <strong className="block font-semibold">{t.settingsPage.errorUpdating}</strong>
                  {submitError}
                </span>
              </motion.div>
            )}

            <div className="grid grid-cols-1 gap-x-6 gap-y-5 md:grid-cols-2">
              <SettingField label={t.settingsPage.companyName} required>
                {isEditing ? (
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input"
                  />
                ) : (
                  <ReadOnlyValue value={company.name} />
                )}
              </SettingField>

              <SettingField label={t.settingsPage.legalName}>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.legalNamePlaceholder}
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                    className="input"
                  />
                ) : (
                  <ReadOnlyValue value={company.legal_name} />
                )}
              </SettingField>

              <SettingField label={t.settingsPage.registrationNo}>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.registrationNoPlaceholder}
                    value={registrationNo}
                    onChange={(e) => setRegistrationNo(e.target.value)}
                    className="input"
                  />
                ) : (
                  <ReadOnlyValue value={company.registration_no} mono />
                )}
              </SettingField>

              <SettingField label={t.settingsPage.taxId}>
                {isEditing ? (
                  <input
                    type="text"
                    placeholder={t.settingsPage.taxIdPlaceholder}
                    value={taxNo}
                    onChange={(e) => setTaxNo(e.target.value)}
                    className="input"
                  />
                ) : (
                  <ReadOnlyValue value={company.tax_no} mono />
                )}
              </SettingField>

              <SettingField
                label={t.settingsPage.baseCurrency}
                required
                hint={t.settingsPage.baseCurrencyHelp}
              >
                {isEditing ? (
                  <input
                    type="text"
                    required
                    maxLength={3}
                    placeholder={t.settingsPage.baseCurrencyPlaceholder}
                    value={baseCurrency}
                    onChange={(e) => setBaseCurrency(e.target.value)}
                    className="input font-mono uppercase"
                  />
                ) : (
                  <ReadOnlyValue value={company.base_currency || 'USD'} mono />
                )}
              </SettingField>

              <div className="md:col-span-2">
                <SettingField label={t.settingsPage.businessAddress}>
                  {isEditing ? (
                    <textarea
                      rows={3}
                      placeholder={t.settingsPage.businessAddressPlaceholder}
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      className="input resize-none"
                    />
                  ) : (
                    <span className="block whitespace-pre-line py-1 text-sm leading-relaxed text-foreground">
                      {company.address || '—'}
                    </span>
                  )}
                </SettingField>
              </div>
            </div>
          </div>
        </SectionCard>
      </form>

      <FiscalSettingsSection companyId={selectedCompanyId} />

      <SectionCard
        icon={Globe}
        title={t.settingsPage.languageAppearance}
        description={t.settingsPage.languageAppearanceDesc}
        tone="violet"
        delay={0.05}
      >
        <div className="space-y-6 p-5">
          <div className="max-w-md">
            <p className="field-label">{t.settingsPage.language}</p>
            <div className="flex gap-3">
              {(
                [
                  ['en', '🇺🇸', t.settingsPage.english],
                  ['ar', '🇸🇦', t.settingsPage.arabic],
                ] as const
              ).map(([code, flag, name]) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLanguage(code as Language)}
                  aria-pressed={language === code}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                    language === code
                      ? 'border-primary-border bg-primary-soft text-primary'
                      : 'border-border bg-surface text-muted-foreground hover:border-border-strong hover:text-foreground'
                  }`}
                >
                  <span aria-hidden className="text-base">
                    {flag}
                  </span>
                  {name}
                </button>
              ))}
            </div>
            <p className="field-hint mt-2">{t.settingsPage.languageHelp}</p>
          </div>

          <div className="max-w-md border-t border-border-subtle pt-5">
            <p className="field-label">{t.theme.appearance}</p>
            <ThemeSegmentedControl />
            <p className="field-hint mt-2">{t.theme.appearanceDescription}</p>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function SettingField({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <span className="field-label flex items-center gap-1.5">
        {label}
        {required && (
          <span className="text-danger" aria-hidden>
            *
          </span>
        )}
        {hint && (
          <span className="group relative inline-flex">
            <HelpCircle className="h-3.5 w-3.5 cursor-help text-subtle-foreground" />
            <span className="absolute bottom-full start-1/2 z-10 mb-1.5 hidden w-48 -translate-x-1/2 rounded-lg border border-border bg-surface-raised p-2 text-[11px] font-normal leading-normal text-muted-foreground shadow-floating group-hover:block">
              {hint}
            </span>
          </span>
        )}
      </span>
      {children}
    </div>
  );
}

function ReadOnlyValue({ value, mono }: { value?: string | null; mono?: boolean }) {
  return (
    <span className={`block py-1 text-sm font-medium text-foreground ${mono ? 'font-mono' : ''}`}>
      {value || '—'}
    </span>
  );
}
