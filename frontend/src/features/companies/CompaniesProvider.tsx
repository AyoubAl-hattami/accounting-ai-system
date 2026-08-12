import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import apiClient from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { CompaniesContext, type CompaniesContextValue } from './companiesContext';
import type { Company, PaginatedResponse } from '../../api/types';

const STORAGE_KEY = 'selected_company_id';

/**
 * Owns the company list and the current selection for the whole session.
 *
 * This used to be a plain hook, which meant every component that called it ran
 * its own fetch and kept its own copy of the selection. Both ProtectedRoute and
 * PageLayout called it, and both were rebuilt on every navigation — so each
 * route change fired two requests for `/companies` and reset the selected
 * company to null in between. Pages keyed their data on that id, so they
 * emptied and refilled on arrival. Holding it once, above the router, is what
 * makes a navigation change only the content.
 */
export function CompaniesProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCompanies = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<PaginatedResponse<Company>>(
        '/companies?skip=0&limit=100',
      );
      const items = response.data.items;
      setCompanies(items);

      const storedId = localStorage.getItem(STORAGE_KEY);
      const storedNum = storedId ? parseInt(storedId, 10) : null;

      if (storedNum && items.some((c) => c.id === storedNum)) {
        setSelectedCompanyId(storedNum);
      } else if (items.length > 0) {
        setSelectedCompanyId(items[0].id);
        localStorage.setItem(STORAGE_KEY, String(items[0].id));
      } else {
        setSelectedCompanyId(null);
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      setCompanies([]);
      setSelectedCompanyId(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Signed out there is nothing to ask for, and asking would only earn a 401.
    // Holding a temporary password earns a 403 for the same reason.
    if (!user || user.must_change_password || user.is_superuser) {
      setCompanies([]);
      setSelectedCompanyId(null);
      if (user?.is_superuser) localStorage.removeItem(STORAGE_KEY);
      setIsLoading(false);
      return;
    }
    void fetchCompanies();
  }, [user, fetchCompanies]);

  const selectCompany = useCallback((id: number) => {
    setSelectedCompanyId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }, []);

  const value = useMemo<CompaniesContextValue>(() => {
    const selectedCompany = companies.find((c) => c.id === selectedCompanyId) || null;
    return { companies, selectedCompanyId, selectedCompany, selectCompany, isLoading };
  }, [companies, selectedCompanyId, selectCompany, isLoading]);

  return <CompaniesContext.Provider value={value}>{children}</CompaniesContext.Provider>;
}
