import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';
import apiClient from '../../api/client';
import type { Partner, PartnerCreatePayload } from '../../api/types';

const CURRENCIES = ['YER', 'USD', 'SAR', 'AED', 'EUR'] as const;

interface NewPartnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  companyId: number;
  defaultType?: 'customer' | 'vendor' | 'both';
  onCreated: (partner: Partner) => void;
}

export default function NewPartnerModal({
  isOpen,
  onClose,
  companyId,
  defaultType = 'customer',
  onCreated,
}: NewPartnerModalProps) {
  const { t } = useI18n();

  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [isCustomer, setIsCustomer] = useState(defaultType === 'customer' || defaultType === 'both');
  const [isVendor, setIsVendor] = useState(defaultType === 'vendor' || defaultType === 'both');
  const [currency, setCurrency] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [taxId, setTaxId] = useState('');
  const [address, setAddress] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName('');
    setCode('');
    setIsCustomer(defaultType === 'customer' || defaultType === 'both');
    setIsVendor(defaultType === 'vendor' || defaultType === 'both');
    setCurrency('');
    setEmail('');
    setPhone('');
    setTaxId('');
    setAddress('');
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !code.trim()) return;
    if (!isCustomer && !isVendor) {
      setError('Please select at least Customer or Vendor.');
      return;
    }

    setIsSaving(true);
    setError(null);

    const payload: PartnerCreatePayload = {
      company_id: companyId,
      name: name.trim(),
      code: code.trim(),
      is_customer: isCustomer,
      is_vendor: isVendor,
      currency: currency || undefined,
      email: email.trim() || undefined,
      phone: phone.trim() || undefined,
      tax_id: taxId.trim() || undefined,
      address: address.trim() || undefined,
    };

    try {
      const res = await apiClient.post<Partner>('/partners', payload);
      onCreated(res.data);
      handleClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create partner.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={t.partnersPage.addPartner}
      description={t.partnersPage.pageSubtitle}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-md text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="field-label">{t.partnersPage.name} *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Al-Amal Trading"
              className="input w-full"
            />
          </div>

          <div>
            <label className="field-label">{t.partnersPage.code} *</label>
            <input
              type="text"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. CUST-001"
              className="input w-full uppercase"
            />
          </div>
        </div>

        <div className="flex gap-6 p-3 bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-md">
          <label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
            <input
              type="checkbox"
              checked={isCustomer}
              onChange={(e) => setIsCustomer(e.target.checked)}
              className="checkbox"
            />
            <span>{t.partnersPage.tabCustomers}</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
            <input
              type="checkbox"
              checked={isVendor}
              onChange={(e) => setIsVendor(e.target.checked)}
              className="checkbox"
            />
            <span>{t.partnersPage.tabVendors}</span>
          </label>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="field-label">{t.partnersPage.currency}</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="select w-full"
            >
              <option value="">{t.accountsPage.currencyCompanyDefault}</option>
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="field-label">{t.partnersPage.taxId}</label>
            <input
              type="text"
              value={taxId}
              onChange={(e) => setTaxId(e.target.value)}
              placeholder="e.g. 100234567"
              className="input w-full"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="field-label">{t.partnersPage.email}</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="contact@company.com"
              className="input w-full"
            />
          </div>

          <div>
            <label className="field-label">{t.partnersPage.phone}</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+967 770 000 000"
              className="input w-full"
            />
          </div>
        </div>

        <div>
          <label className="field-label">{t.partnersPage.address}</label>
          <textarea
            rows={2}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="City, Street, Building..."
            className="input w-full resize-none"
          />
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-neutral-200 dark:border-neutral-800">
          <button
            type="button"
            onClick={handleClose}
            className="btn btn-secondary"
            disabled={isSaving}
          >
            {t.common.cancel}
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="btn btn-primary min-w-[7rem]"
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t.partnersPage.creating}
              </span>
            ) : (
              t.partnersPage.createPartner
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
