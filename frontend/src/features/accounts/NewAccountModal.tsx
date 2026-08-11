import { useId, useState } from 'react';
import { Landmark, Loader2, Wallet, Banknote } from 'lucide-react';
import Modal from '../../components/ui/Modal';
import { useI18n } from '../../i18n';
import type { Account, AccountSubtype, CreateAccountInput } from '../../entities/account';

const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'income', 'expense'] as const;

const SUBTYPES: AccountSubtype[] = [
  'bank',
  'cash',
  'e_wallet',
  'receivable',
  'payable',
  'revenue',
  'expense',
  'other',
];

interface FormState {
  code: string;
  name: string;
  accountType: string;
  subtype: AccountSubtype | '';
  parentId: string;
  description: string;
}

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  accountType: 'asset',
  subtype: '',
  parentId: '',
  description: '',
};

interface NewAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: Account[];
  onCreate: (input: CreateAccountInput) => Promise<Account>;
  onCreated: () => void;
}

export default function NewAccountModal({
  isOpen,
  onClose,
  accounts,
  onCreate,
  onCreated,
}: NewAccountModalProps) {
  const { t } = useI18n();
  const codeId = useId();
  const nameId = useId();
  const typeId = useId();
  const subtypeId = useId();
  const parentId = useId();
  const descriptionId = useId();

  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const subtypeLabels: Record<AccountSubtype, string> = {
    bank: t.accountsPage.subtypeBank,
    cash: t.accountsPage.subtypeCash,
    e_wallet: t.accountsPage.subtypeEWallet,
    receivable: t.accountsPage.subtypeReceivable,
    payable: t.accountsPage.subtypePayable,
    revenue: t.accountsPage.subtypeRevenue,
    expense: t.accountsPage.subtypeExpense,
    other: t.accountsPage.subtypeOther,
  };

  // Quick templates are pure form prefills — they create an ordinary account
  // through the same endpoint as a fully hand-typed one.
  const quickTemplates: { key: AccountSubtype; label: string; icon: typeof Landmark }[] = [
    { key: 'bank', label: t.accountsPage.templateBank, icon: Landmark },
    { key: 'cash', label: t.accountsPage.templateCashBox, icon: Banknote },
    { key: 'e_wallet', label: t.accountsPage.templateEWallet, icon: Wallet },
  ];

  const applyTemplate = (subtype: AccountSubtype) => {
    setForm((current) => ({
      ...current,
      accountType: 'asset',
      subtype,
      name: current.name || subtypeLabels[subtype],
    }));
  };

  const closeAndReset = () => {
    setForm(EMPTY_FORM);
    setError(null);
    onClose();
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);

    try {
      await onCreate({
        code: form.code.trim(),
        name: form.name.trim(),
        account_type: form.accountType,
        account_subtype: form.subtype || null,
        parent_id: form.parentId ? Number(form.parentId) : null,
        description: form.description.trim() || null,
      });
      setForm(EMPTY_FORM);
      onCreated();
      onClose();
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const canSubmit = form.code.trim().length > 0 && form.name.trim().length > 0 && !isSaving;

  return (
    <Modal
      isOpen={isOpen}
      onClose={closeAndReset}
      title={t.accountsPage.addAccountTitle}
      description={t.accountsPage.addAccountDescription}
      size="md"
      busy={isSaving}
      error={error}
      footer={
        <>
          <button
            type="button"
            onClick={closeAndReset}
            disabled={isSaving}
            className="btn btn-ghost btn-sm"
          >
            {t.common.cancel}
          </button>
          <button
            type="submit"
            form="new-account-form"
            disabled={!canSubmit}
            className="btn btn-primary btn-sm"
          >
            {isSaving && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />}
            {isSaving ? t.accountsPage.creating : t.accountsPage.createAccount}
          </button>
        </>
      }
    >
      <form id="new-account-form" onSubmit={handleSubmit} className="space-y-4">
        <fieldset>
          <legend className="field-label">{t.accountsPage.quickTemplates}</legend>
          <div className="flex flex-wrap gap-2">
            {quickTemplates.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => applyTemplate(key)}
                className="btn btn-secondary btn-sm"
              >
                <Icon aria-hidden className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-subtle-foreground">
            {t.accountsPage.quickTemplatesHelp}
          </p>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor={codeId} className="field-label">
              {t.accountsPage.code}
            </label>
            <input
              id={codeId}
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder={t.accountsPage.codePlaceholder}
              maxLength={50}
              required
              className="input"
            />
            <p className="mt-1.5 text-xs text-subtle-foreground">{t.accountsPage.codeHelp}</p>
          </div>

          <div>
            <label htmlFor={nameId} className="field-label">
              {t.accountsPage.name}
            </label>
            <input
              id={nameId}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder={t.accountsPage.namePlaceholder}
              maxLength={255}
              required
              className="input"
            />
          </div>

          <div>
            <label htmlFor={typeId} className="field-label">
              {t.accountsPage.type}
            </label>
            <select
              id={typeId}
              value={form.accountType}
              onChange={(e) => setForm({ ...form, accountType: e.target.value })}
              className="select"
            >
              {ACCOUNT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-subtle-foreground">{t.accountsPage.typeHelp}</p>
          </div>

          <div>
            <label htmlFor={subtypeId} className="field-label">
              {t.accountsPage.subtype}
            </label>
            <select
              id={subtypeId}
              value={form.subtype}
              onChange={(e) =>
                setForm({ ...form, subtype: e.target.value as AccountSubtype | '' })
              }
              className="select"
            >
              <option value="">{t.accountsPage.subtypeNone}</option>
              {SUBTYPES.map((subtype) => (
                <option key={subtype} value={subtype}>
                  {subtypeLabels[subtype]}
                </option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-subtle-foreground">{t.accountsPage.subtypeHelp}</p>
          </div>
        </div>

        <div>
          <label htmlFor={parentId} className="field-label">
            {t.accountsPage.parentAccount}
          </label>
          <select
            id={parentId}
            value={form.parentId}
            onChange={(e) => setForm({ ...form, parentId: e.target.value })}
            className="select"
          >
            <option value="">{t.accountsPage.parentNone}</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} — {account.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor={descriptionId} className="field-label">
            {t.common.description}
          </label>
          <input
            id={descriptionId}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input"
          />
        </div>
      </form>
    </Modal>
  );
}
