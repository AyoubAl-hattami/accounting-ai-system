/**
 * useCompanies hook — clean version.
 *
 * Manages company list and selection with localStorage persistence.
 * Does not import from other features.
 */
import { useState, useEffect, useCallback } from 'react';
import type { Company } from '../../entities/company';
import { listCompanies } from './api';

const STORAGE_KEY = 'selected_company_id';

interface UseCompaniesReturn {
  companies: Company[];
  selectedCompanyId: number | null;
  selectedCompany: Company | null;
  isLoading: boolean;
  selectCompany: (id: number) => void;
  refetch: () => Promise<void>;
}

export function useCompanies(): UseCompaniesReturn {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCompanies = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listCompanies({ skip: 0, limit: 100 });
      const items = data.items;
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
    fetchCompanies();
  }, [fetchCompanies]);

  const selectCompany = useCallback((id: number) => {
    setSelectedCompanyId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }, []);

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId) ?? null;

  return {
    companies,
    selectedCompanyId,
    selectedCompany,
    isLoading,
    selectCompany,
    refetch: fetchCompanies,
  };
}
