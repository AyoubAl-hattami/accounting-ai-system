import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import type { Company, PaginatedResponse } from '../api/types';

const STORAGE_KEY = 'selected_company_id';

export function useCompanies() {
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
    fetchCompanies();
  }, [fetchCompanies]);

  const selectCompany = (id: number) => {
    setSelectedCompanyId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  const selectedCompany = companies.find((c) => c.id === selectedCompanyId) || null;

  return {
    companies,
    selectedCompanyId,
    selectedCompany,
    selectCompany,
    isLoading,
  };
}
