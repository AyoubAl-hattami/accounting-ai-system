import { createContext } from 'react';
import type { Company } from '../../api/types';

export interface CompaniesContextValue {
  companies: Company[];
  selectedCompanyId: number | null;
  selectedCompany: Company | null;
  selectCompany: (id: number) => void;
  isLoading: boolean;
}

/**
 * The session-wide company list and current selection.
 *
 * Kept in its own module rather than beside the provider so that
 * CompaniesProvider.tsx exports nothing but a component — which is what lets
 * Vite's fast refresh replace it in place instead of reloading the page.
 */
export const CompaniesContext = createContext<CompaniesContextValue | null>(null);
