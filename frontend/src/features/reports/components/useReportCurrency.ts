import { useEffect, useState } from 'react';
import apiClient from '../../../api/client';

interface ReportCurrencies {
  base_currency: string;
  currencies: string[];
}

/**
 * The currencies a company's reports can be run in, and which one is chosen.
 *
 * Every report totals one currency at a time: a company that keeps riyal and
 * dollar accounts has two trial balances, never one that adds them. This asks
 * the server which currencies exist and starts on the company's own.
 *
 * `currency` stays null until the user picks one, and a null currency means
 * "the company's own" to every report endpoint. It is deliberately NOT set to
 * the base currency once the list loads: that would change a dependency of
 * every report fetch and load the same report twice, the double fetch [D5]
 * removed from the assistant. `selected` is what the picker displays.
 */
export function useReportCurrency(companyId: number | null) {
  const [available, setAvailable] = useState<string[]>([]);
  const [base, setBase] = useState<string | null>(null);
  const [currency, setCurrency] = useState<string | null>(null);

  useEffect(() => {
    setAvailable([]);
    setBase(null);
    setCurrency(null);
    if (!companyId) return;

    let cancelled = false;
    apiClient
      .get<ReportCurrencies>(`/reports/currencies?company_id=${companyId}`)
      .then((response) => {
        if (cancelled) return;
        setAvailable(response.data.currencies);
        setBase(response.data.base_currency);
      })
      .catch(() => {
        // Not fatal: every report already defaults to the company's own
        // currency when none is named, so the page still shows correct figures.
        // Only the choice between currencies is lost.
        if (!cancelled) setAvailable([]);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  return {
    /** What to send to a report: null until the user chooses. */
    currency,
    setCurrency,
    /** What the picker shows: the choice, or the company's own before one. */
    selected: currency ?? base,
    base,
    available,
    // A single-currency company has nothing to choose between, so the picker
    // stays out of its toolbar entirely.
    hasChoice: available.length > 1,
  };
}
