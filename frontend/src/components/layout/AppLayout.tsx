import { Suspense, useMemo, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import AppShell from './AppShell';
import { PageMetaContext, type PageMeta } from './pageMeta';
import { useAuth } from '../../auth/AuthContext';
import { useCompanies } from '../../features/companies/useCompanies';
import { useCompanyRole } from '../../auth/useCompanyRole';

/**
 * The one place the application shell is mounted.
 *
 * Previously each page rendered its own PageLayout, which rendered its own
 * AppShell. React saw a different component at the route position on every
 * navigation, so the sidebar, topbar, company selector and assistant were torn
 * down and rebuilt each time — which is what made navigation feel like a full
 * page replacement rather than a change of content. As a layout route the shell
 * is mounted once and only the <Outlet /> beneath it changes.
 */
export default function AppLayout() {
  const { user, isLoading } = useAuth();
  const { companies, selectedCompany, selectCompany } = useCompanies();
  const { role: userRole } = useCompanyRole(selectedCompany?.id ?? null);
  const [meta, setMeta] = useState<PageMeta>({});

  const metaValue = useMemo(() => ({ meta, setMeta }), [meta]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 aria-hidden className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <PageMetaContext.Provider value={metaValue}>
      <AppShell
        companies={companies}
        selectedCompany={selectedCompany}
        onSelectCompany={selectCompany}
        pageTitle={meta.pageTitle}
        pageSubtitle={meta.pageSubtitle}
        activePath={meta.activePath}
        userRole={userRole}
      >
        {/* Scoped to the content well, so pulling a lazy page chunk swaps the
            main area and leaves the sidebar and topbar on screen. Hoisted to
            the router it blanked the entire window on first visit to a route. */}
        <Suspense fallback={<ContentFallback />}>
          <Outlet />
        </Suspense>
      </AppShell>
    </PageMetaContext.Provider>
  );
}

/**
 * Holds the content well open at a plausible height while a chunk arrives, so
 * the scrollbar and the footer do not jump when the page lands.
 */
function ContentFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center" role="status" aria-live="polite">
      <Loader2 aria-hidden className="h-6 w-6 animate-spin text-primary" />
    </div>
  );
}
