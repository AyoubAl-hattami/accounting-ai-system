/**
 * Fiscal period and fiscal year entity types.
 *
 * These types are used across accounts, journals, and reports.
 * Fiscal models are not yet separated in api/types.ts; they will be
 * extracted here as part of the fiscal slice migration.
 */

export interface FiscalYear {
  id: number;
  company_id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: 'open' | 'closed' | 'locked';
  created_at: string;
  updated_at: string;
}

export interface FiscalPeriod {
  id: number;
  company_id: number;
  fiscal_year_id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: 'open' | 'closed' | 'locked';
  period_number: number;
  created_at: string;
  updated_at: string;
}
