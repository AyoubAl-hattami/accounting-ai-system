import { useState, useEffect, useMemo } from 'react';
import { Plus, Search, Users, UserCheck, Building2, FileText } from 'lucide-react';
import PageLayout from '../../components/layout/PageLayout';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type { Partner, PaginatedResponse, CompanyUserRole } from '../../api/types';
import NewPartnerModal from './NewPartnerModal';
import PartnerStatementModal from './PartnerStatementModal';

type TabType = 'customers' | 'vendors' | 'all';

export default function PartnersPage() {
  const { t } = useI18n();

  return (
    <PageLayout
      pageTitle={t.partnersPage.pageTitle}
      pageSubtitle={t.partnersPage.pageSubtitle}
      activePath="/partners"
    >
      {({ selectedCompanyId, companiesLoading, userRole }) => (
        <PartnersContent
          companyId={selectedCompanyId}
          companiesLoading={companiesLoading}
          userRole={userRole}
        />
      )}
    </PageLayout>
  );
}

interface PartnersContentProps {
  companyId: number | null;
  companiesLoading: boolean;
  userRole: CompanyUserRole | null;
}

function PartnersContent({ companyId, companiesLoading }: PartnersContentProps) {
  const { t } = useI18n();

  const [partners, setPartners] = useState<Partner[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<TabType>('customers');
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [statementPartner, setStatementPartner] = useState<Partner | null>(null);

  const fetchPartners = async () => {
    if (!companyId) return;
    setLoading(true);
    try {
      const res = await apiClient.get<PaginatedResponse<Partner>>(
        `/partners?company_id=${companyId}&limit=500`
      );
      setPartners(res.data.items);
    } catch {
      setPartners([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPartners();
  }, [companyId]);

  const filteredPartners = useMemo(() => {
    return partners.filter((p) => {
      if (activeTab === 'customers' && !p.is_customer) return false;
      if (activeTab === 'vendors' && !p.is_vendor) return false;

      if (search.trim()) {
        const query = search.toLowerCase();
        const matchName = p.name.toLowerCase().includes(query);
        const matchCode = p.code.toLowerCase().includes(query);
        const matchEmail = p.email?.toLowerCase().includes(query) ?? false;
        const matchPhone = p.phone?.toLowerCase().includes(query) ?? false;
        return matchName || matchCode || matchEmail || matchPhone;
      }
      return true;
    });
  }, [partners, activeTab, search]);

  if (companiesLoading) {
    return <div className="p-8 text-center text-sm text-neutral-500">{t.common.loading}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Page Header Actions */}
      <div className="flex justify-end">
        <button
          onClick={() => setIsNewModalOpen(true)}
          className="btn btn-primary inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          <span>{t.partnersPage.addPartner}</span>
        </button>
      </div>

      {/* Toolbar: Tabs & Search */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white dark:bg-neutral-950 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm">
        {/* Tabs */}
        <div className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-900 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('customers')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'customers'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <UserCheck className="h-3.5 w-3.5" />
              {t.partnersPage.tabCustomers}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('vendors')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'vendors'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5" />
              {t.partnersPage.tabVendors}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
              activeTab === 'all'
                ? 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              {t.partnersPage.tabAll}
            </span>
          </button>
        </div>

        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t.partnersPage.searchPlaceholder}
            className="input pl-9 w-full text-sm"
          />
        </div>
      </div>

      {/* Partners Table */}
      <div className="bg-white dark:bg-neutral-950 rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-neutral-500">
            {t.common.loading}
          </div>
        ) : filteredPartners.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="h-10 w-10 mx-auto text-neutral-300 dark:text-neutral-700 mb-3" />
            <h3 className="text-base font-semibold text-neutral-900 dark:text-white">
              {t.partnersPage.noPartnersTitle}
            </h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1 max-w-sm mx-auto">
              {t.partnersPage.noPartnersDescription}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50 text-neutral-500 font-medium">
                  <th className="py-3 px-4">{t.partnersPage.code}</th>
                  <th className="py-3 px-4">{t.partnersPage.name}</th>
                  <th className="py-3 px-4">{t.partnersPage.type}</th>
                  <th className="py-3 px-4">{t.partnersPage.currency}</th>
                  <th className="py-3 px-4">{t.partnersPage.contact}</th>
                  <th className="py-3 px-4">{t.partnersPage.taxId}</th>
                  <th className="py-3 px-4 text-center">{t.partnersPage.status}</th>
                  <th className="py-3 px-4 text-right">{t.common.actions}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                {filteredPartners.map((partner) => (
                  <tr
                    key={partner.id}
                    className="hover:bg-neutral-50/50 dark:hover:bg-neutral-900/50 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono text-xs font-semibold text-neutral-600 dark:text-neutral-300">
                      {partner.code}
                    </td>
                    <td className="py-3 px-4 font-medium text-neutral-900 dark:text-white">
                      {partner.name}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        {partner.is_customer && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                            {t.partnersPage.tabCustomers}
                          </span>
                        )}
                        {partner.is_vendor && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                            {t.partnersPage.tabVendors}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs font-semibold">
                      {partner.currency}
                    </td>
                    <td className="py-3 px-4 text-neutral-600 dark:text-neutral-400 text-xs">
                      <div>{partner.email || '—'}</div>
                      <div className="text-neutral-400">{partner.phone || ''}</div>
                    </td>
                    <td className="py-3 px-4 text-xs font-mono text-neutral-500">
                      {partner.tax_id || '—'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          partner.is_active
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-400'
                        }`}
                      >
                        {partner.is_active
                          ? t.partnersPage.active
                          : t.partnersPage.inactive}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => setStatementPartner(partner)}
                        className="btn btn-secondary text-xs py-1 px-2.5 inline-flex items-center gap-1 hover:border-primary/50"
                        title={t.partnersPage.viewStatement}
                      >
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        <span>{t.partnersPage.viewStatement}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {companyId && (
        <NewPartnerModal
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          companyId={companyId}
          defaultType={
            activeTab === 'customers'
              ? 'customer'
              : activeTab === 'vendors'
              ? 'vendor'
              : 'both'
          }
          onCreated={() => fetchPartners()}
        />
      )}

      {companyId && statementPartner && (
        <PartnerStatementModal
          isOpen={Boolean(statementPartner)}
          onClose={() => setStatementPartner(null)}
          companyId={companyId}
          partner={statementPartner}
        />
      )}
    </div>
  );
}
