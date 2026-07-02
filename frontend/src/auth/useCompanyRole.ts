import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { useAuth } from './AuthContext';
import type { CompanyUser, CompanyUserRole } from '../api/types';

interface UseCompanyRoleResult {
  role: CompanyUserRole | null;
  isLoading: boolean;
}

/**
 * Fetches the current user's role in the selected company.
 * Superusers automatically resolve to 'admin'.
 * Returns null if no company selected or user has no access.
 */
export function useCompanyRole(companyId: number | null): UseCompanyRoleResult {
  const { user } = useAuth();
  const [role, setRole] = useState<CompanyUserRole | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Superuser → admin, no API call needed
    if (user?.is_superuser) {
      setRole('admin');
      setIsLoading(false);
      return;
    }

    if (!companyId || !user) {
      setRole(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    apiClient
      .get<CompanyUser>(`/company-users/me?company_id=${companyId}`)
      .then((res) => {
        if (cancelled) return;
        setRole(res.data.is_active ? res.data.role : null);
      })
      .catch(() => {
        if (!cancelled) setRole(null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId, user]);

  return { role, isLoading };
}
