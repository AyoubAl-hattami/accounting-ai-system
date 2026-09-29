import { useState, useEffect, useMemo } from 'react';
import {
  Calendar,
  Clock,
  Coins,
  FileText,
  Filter,
  RefreshCw,
  Search,
  Users,
} from 'lucide-react';
import PageLayout from '../../../components/layout/PageLayout';
import { useI18n } from '../../../i18n';
import apiClient from '../../../api/client';
import type {
  AgingReportResponse,
  CompanyUserRole,
  Partner,
  PaginatedResponse,
} from '../../../api/types';

type AgingReportType = 'ar' | 'ap';

export default function AgingReportsPage() {
  const { t } = useI18n();

  return (
    <PageLayout
      pageTitle={t.agingReports.pageTitle}
      pageSubtitle={t.agingReports.pageSubtitle}
      activePath="/reports/aging"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <AgingReportsContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface AgingReportsContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function AgingReportsContent({ companyId, companiesLoading }: AgingReportsContentProps) {
  const { t, language } = useI18n();

  const [reportType, setReportType] = useState<AgingReportType>('ar');
  const [asOfDate, setAsOfDate] = useState<string>(() => new Date().toISOString().split('T')[0]);
  const [currencies, setCurrencies] = useState<string[]>([]);
  const [selectedCurrency, setSelectedCurrency] = useState<string>('');
  const [partners, setPartners] = useState<Partner[]>([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState<string>('');
  const [search, setSearch] = useState('');

  const [reportData, setReportData] = useState<AgingReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch company currencies
  useEffect(() => {
    if (!companyId) return;
    const fetchCurrencies = async () => {
      try {
        const res = await apiClient.get<{ base_currency: string; currencies: string[] }>(
          `/reports/currencies?company_id=${companyId}`
        );
        const list = res.data.currencies || [res.data.base_currency];
        setCurrencies(list);
        if (!selectedCurrency || !list.includes(selectedCurrency)) {
          setSelectedCurrency(res.data.base_currency || list[0] || 'USD');
        }
      } catch {
        setCurrencies(['USD']);
        setSelectedCurrency('USD');
      }
    };
    fetchCurrencies();
  }, [companyId]);

  // Fetch partners for filter
  useEffect(() => {
    if (!companyId) return;
    const fetchPartners = async () => {
      try {
        const res = await apiClient.get<PaginatedResponse<Partner>>(
          `/partners?company_id=${companyId}&limit=500`
        );
        setPartners(res.data.items || []);
      } catch {
        setPartners([]);
      }
    };
    fetchPartners();
  }, [companyId]);

  // Fetch Aging Report data
  const fetchReport = async () => {
    if (!companyId || !selectedCurrency) return;
    setLoading(true);
    setError(null);
    try {
      const endpoint = reportType === 'ar' ? '/reports/ar-aging' : '/reports/ap-aging';
      let url = `${endpoint}?company_id=${companyId}&currency=${selectedCurrency}&as_of_date=${asOfDate}`;
      if (selectedPartnerId) {
        url += `&partner_id=${selectedPartnerId}`;
      }
      const res = await apiClient.get<AgingReportResponse>(url);
      setReportData(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t.common.somethingWentWrong);
      setReportData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [companyId, reportType, asOfDate, selectedCurrency, selectedPartnerId]);

  // Filter partners based on current tab
  const relevantPartners = useMemo(() => {
    return partners.filter((p) => (reportType === 'ar' ? p.is_customer : p.is_vendor));
  }, [partners, reportType]);

  // Filter items by search input
  const filteredItems = useMemo(() => {
    if (!reportData?.items) return [];
    if (!search.trim()) return reportData.items;
    const q = search.toLowerCase();
    return reportData.items.filter(
      (item) =>
        item.partner_name.toLowerCase().includes(q) ||
        item.partner_code.toLowerCase().includes(q) ||
        item.invoice_no.toLowerCase().includes(q)
    );
  }, [reportData?.items, search]);

  const formatAmount = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat(language === 'ar' ? 'ar-SA' : 'en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num || 0);
  };

  const getBucketBadgeClass = (bucket: string) => {
    switch (bucket) {
      case 'current':
        return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800';
      case '1-30':
        return 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border-blue-200 dark:border-blue-800';
      case '31-60':
        return 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200 dark:border-amber-800';
      case '61-90':
        return 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400 border-orange-200 dark:border-orange-800';
      case '91-120':
        return 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border-rose-200 dark:border-rose-800';
      case '120+':
      default:
        return 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border-red-300 dark:border-red-800 font-bold';
    }
  };

  const getBucketLabel = (bucket: string) => {
    switch (bucket) {
      case 'current':
        return t.agingReports.currentBucket;
      case '1-30':
        return t.agingReports.days1_30Bucket;
      case '31-60':
        return t.agingReports.days31_60Bucket;
      case '61-90':
        return t.agingReports.days61_90Bucket;
      case '91-120':
        return t.agingReports.days91_120Bucket;
      case '120+':
      default:
        return t.agingReports.days120PlusBucket;
    }
  };

  if (companiesLoading) {
    return <div className="p-8 text-center text-sm text-neutral-500">{t.common.loading}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Top Controls: Tabs & Date & Currency */}
      <div className="flex flex-col gap-4 bg-white dark:bg-neutral-950 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Tabs: AR vs AP */}
          <div className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-900 p-1 rounded-lg">
            <button
              onClick={() => {
                setReportType('ar');
                setSelectedPartnerId('');
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-md transition-colors ${
                reportType === 'ar'
                  ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-sm'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
              }`}
            >
              <span className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                {t.agingReports.tabAr}
              </span>
            </button>
            <button
              onClick={() => {
                setReportType('ap');
                setSelectedPartnerId('');
              }}
              className={`px-4 py-2 text-xs font-semibold rounded-md transition-colors ${
                reportType === 'ap'
                  ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-sm'
                  : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
              }`}
            >
              <span className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                {t.agingReports.tabAp}
              </span>
            </button>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => fetchReport()}
            disabled={loading}
            className="btn btn-secondary inline-flex items-center gap-2 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{t.common.refresh}</span>
          </button>
        </div>

        {/* Filter Row: As of Date, Currency, Partner, Search */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-neutral-100 dark:border-neutral-800">
          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                {t.agingReports.asOfDate}
              </span>
            </label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="input w-full text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1.5">
                <Coins className="h-3.5 w-3.5" />
                {t.agingReports.currency}
              </span>
            </label>
            <select
              value={selectedCurrency}
              onChange={(e) => setSelectedCurrency(e.target.value)}
              className="input w-full text-xs"
            >
              {currencies.map((curr) => (
                <option key={curr} value={curr}>
                  {curr}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1.5">
                <Filter className="h-3.5 w-3.5" />
                {t.agingReports.partner}
              </span>
            </label>
            <select
              value={selectedPartnerId}
              onChange={(e) => setSelectedPartnerId(e.target.value)}
              className="input w-full text-xs"
            >
              <option value="">{t.agingReports.allPartners}</option>
              {relevantPartners.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-1">
              <span className="inline-flex items-center gap-1.5">
                <Search className="h-3.5 w-3.5" />
                {t.common.search}
              </span>
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t.agingReports.searchPlaceholder}
              className="input w-full text-xs"
            />
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {reportData?.totals && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summaryCurrent}</span>
            <div className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_current)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summary1_30}</span>
            <div className="text-base font-bold text-blue-600 dark:text-blue-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_1_30)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summary31_60}</span>
            <div className="text-base font-bold text-amber-600 dark:text-amber-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_31_60)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summary61_90}</span>
            <div className="text-base font-bold text-orange-600 dark:text-orange-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_61_90)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summary91_120}</span>
            <div className="text-base font-bold text-rose-600 dark:text-rose-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_91_120)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
            <span className="text-xs font-medium text-neutral-500">{t.agingReports.summary120Plus}</span>
            <div className="text-base font-bold text-red-600 dark:text-red-400 mt-1 font-mono">
              {formatAmount(reportData.totals.total_120_plus)}
            </div>
          </div>

          <div className="bg-white dark:bg-neutral-950 p-3 rounded-xl border-2 border-primary/40 dark:border-primary/50 shadow-sm bg-primary/5">
            <span className="text-xs font-semibold text-primary">{t.agingReports.summaryTotalOutstanding}</span>
            <div className="text-base font-extrabold text-primary mt-1 font-mono">
              {formatAmount(reportData.totals.total_outstanding)} {selectedCurrency}
            </div>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white dark:bg-neutral-950 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-neutral-500">{t.common.loading}</div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-10 w-10 mx-auto text-neutral-300 dark:text-neutral-700 mb-3" />
            <h3 className="text-base font-semibold text-neutral-900 dark:text-white">
              {t.agingReports.noInvoicesFound}
            </h3>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50 text-neutral-500 font-medium">
                  <th className="py-3 px-3">{t.agingReports.partnerCol}</th>
                  <th className="py-3 px-3">
                    {reportType === 'ar' ? t.agingReports.invoiceNoCol : t.agingReports.billNoCol}
                  </th>
                  <th className="py-3 px-3">{t.agingReports.invoiceDateCol}</th>
                  <th className="py-3 px-3">{t.agingReports.dueDateCol}</th>
                  <th className="py-3 px-3 text-right">{t.agingReports.originalAmountCol}</th>
                  <th className="py-3 px-3 text-right">{t.agingReports.paidAmountCol}</th>
                  <th className="py-3 px-3 text-right font-bold">{t.agingReports.outstandingAmountCol}</th>
                  <th className="py-3 px-3 text-center">{t.agingReports.daysOverdueCol}</th>
                  <th className="py-3 px-3 text-center">{t.agingReports.bucketCol}</th>
                  <th className="py-3 px-3 text-center">{t.agingReports.currencyCol}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {filteredItems.map((item) => (
                  <tr
                    key={item.invoice_id}
                    className="hover:bg-neutral-50/50 dark:hover:bg-neutral-900/50 transition-colors"
                  >
                    <td className="py-3 px-3 font-medium text-neutral-900 dark:text-white">
                      <div>{item.partner_name}</div>
                      <div className="text-neutral-400 font-mono text-[11px]">{item.partner_code}</div>
                    </td>
                    <td className="py-3 px-3 font-mono font-semibold text-neutral-700 dark:text-neutral-300">
                      {item.invoice_no}
                    </td>
                    <td className="py-3 px-3 text-neutral-600 dark:text-neutral-400">
                      {item.invoice_date}
                    </td>
                    <td className="py-3 px-3 text-neutral-600 dark:text-neutral-400">
                      {item.due_date}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-neutral-600 dark:text-neutral-400">
                      {formatAmount(item.original_amount)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-emerald-600 dark:text-emerald-400">
                      {formatAmount(item.paid_amount)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-neutral-900 dark:text-white">
                      {formatAmount(item.outstanding_amount)}
                    </td>
                    <td className="py-3 px-3 text-center font-mono">
                      <span
                        className={
                          item.days_overdue > 0
                            ? 'text-red-600 dark:text-red-400 font-semibold'
                            : 'text-neutral-500'
                        }
                      >
                        {item.days_overdue > 0 ? `+${item.days_overdue}` : item.days_overdue}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] border font-medium ${getBucketBadgeClass(
                          item.bucket
                        )}`}
                      >
                        {getBucketLabel(item.bucket)}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center font-mono font-semibold text-[11px]">
                      {item.currency}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
