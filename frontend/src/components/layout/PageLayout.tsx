import { useLayoutEffect, type ReactNode } from 'react';
import EmptyState from '../feedback/EmptyState';
import { usePageMeta } from './pageMeta';
import { useCompanies } from '../../features/companies/useCompanies';
import { useCompanyRole } from '../../auth/useCompanyRole';
import { useI18n } from '../../i18n';
import { Building2 } from 'lucide-react';
import type { Company, CompanyUserRole } from '../../api/types';

interface PageLayoutChildProps {
  selectedCompanyId: number | null;
  selectedCompany: Company | null;
  companies: Company[];
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

interface PageLayoutProps {
  pageTitle?: string;
  pageSubtitle?: string;
  activePath?: string;
  children: (props: PageLayoutChildProps) => ReactNode;
}

/**
 * Page-level content wrapper. It no longer renders the application shell — that
 * is mounted once by {@link AppLayout} and survives navigation. What remains is
 * the page's contract with the shell: it announces its title and active nav
 * entry, and hands the current company down to the page body.
 *
 * The call signature is unchanged, so every page keeps working as written.
 */
export default function PageLayout({
  pageTitle,
  pageSubtitle,
  activePath,
  children,
}: PageLayoutProps) {
  const { t } = useI18n();
  const { setMeta } = usePageMeta();
  const {
    companies,
    selectedCompanyId,
    selectedCompany,
    isLoading: companiesLoading,
  } = useCompanies();
  const { role: userRole } = useCompanyRole(selectedCompanyId);

  // Layout effect rather than a plain effect: it runs before the browser paints,
  // so the topbar shows the new page's title on the first frame instead of
  // flashing the previous one.
  useLayoutEffect(() => {
    setMeta({ pageTitle, pageSubtitle, activePath });
  }, [pageTitle, pageSubtitle, activePath, setMeta]);

  if (!companiesLoading && companies.length === 0) {
    return (
      <EmptyState
        icon={<Building2 className="h-7 w-7 text-primary" />}
        title={t.common.noCompaniesYet}
        description={t.common.noCompaniesDescription}
        className="py-32"
      />
    );
  }

  return (
    <>
      {children({
        selectedCompanyId,
        selectedCompany,
        companies,
        companiesLoading,
        userRole,
      })}
    </>
  );
}
