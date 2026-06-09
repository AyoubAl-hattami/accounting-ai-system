import { type ReactNode } from 'react';
import AppShell from './AppShell';
import EmptyState from '../feedback/EmptyState';
import { useCompanies } from '../../features/companies/useCompanies';
import { useI18n } from '../../i18n';
import { Building2 } from 'lucide-react';
import type { Company } from '../../api/types';

interface PageLayoutChildProps {
  selectedCompanyId: number | null;
  selectedCompany: Company | null;
  companies: Company[];
  companiesLoading: boolean;
}

interface PageLayoutProps {
  pageTitle?: string;
  pageSubtitle?: string;
  activePath?: string;
  children: (props: PageLayoutChildProps) => ReactNode;
}

export default function PageLayout({
  pageTitle,
  pageSubtitle,
  activePath,
  children,
}: PageLayoutProps) {
  const { t } = useI18n();
  const {
    companies,
    selectedCompanyId,
    selectedCompany,
    selectCompany,
    isLoading: companiesLoading,
  } = useCompanies();

  // No companies guard
  if (!companiesLoading && companies.length === 0) {
    return (
      <AppShell
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={selectCompany}
        pageTitle={pageTitle}
        pageSubtitle={pageSubtitle}
        activePath={activePath}
      >
        <EmptyState
          icon={<Building2 className="w-7 h-7 text-brand-400" />}
          title={t.common.noCompaniesYet}
          description={t.common.noCompaniesDescription}
          className="py-32"
        />
      </AppShell>
    );
  }

  return (
    <AppShell
      companies={companies}
      selectedCompany={selectedCompany}
      onSelectCompany={selectCompany}
      pageTitle={pageTitle}
      pageSubtitle={pageSubtitle}
      activePath={activePath}
    >
      {children({
        selectedCompanyId,
        selectedCompany,
        companies,
        companiesLoading,
      })}
    </AppShell>
  );
}
