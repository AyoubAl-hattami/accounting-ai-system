import { useContext } from 'react';
import { CompaniesContext, type CompaniesContextValue } from './companiesContext';

/**
 * Reads the session-wide company list and selection.
 *
 * The fetch lives in {@link CompaniesProvider}; this is only the reader. Calling
 * it from several components is therefore free, and every caller sees the same
 * selection rather than its own private copy.
 */
export function useCompanies(): CompaniesContextValue {
  const context = useContext(CompaniesContext);
  if (!context) {
    throw new Error('useCompanies must be used within a CompaniesProvider');
  }
  return context;
}
