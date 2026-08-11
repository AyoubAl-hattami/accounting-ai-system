import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NewAccountModal from '../../features/accounts/NewAccountModal';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import type { Account, CreateAccountInput } from '../../entities/account';

const copy = en.accountsPage;

const PARENT: Account = {
  id: 10,
  company_id: 1,
  code: '1000',
  name: 'Assets',
  account_type: 'asset',
  account_subtype: null,
  parent_id: null,
  description: null,
  is_active: true,
  is_system: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderModal(overrides: Partial<{ onCreate: (input: CreateAccountInput) => Promise<Account> }> = {}) {
  const onCreate = overrides.onCreate ?? vi.fn().mockResolvedValue(PARENT);
  const onCreated = vi.fn();
  const onClose = vi.fn();
  render(
    <I18nProvider>
      <NewAccountModal
        isOpen
        onClose={onClose}
        accounts={[PARENT]}
        onCreate={onCreate}
        onCreated={onCreated}
      />
    </I18nProvider>,
  );
  return { onCreate, onCreated, onClose };
}

const fillRequired = (code: string, name: string) => {
  fireEvent.change(screen.getByLabelText(copy.code), { target: { value: code } });
  fireEvent.change(screen.getByLabelText(copy.name), { target: { value: name } });
};

const submit = () => fireEvent.click(screen.getByRole('button', { name: copy.createAccount }));

describe('new account modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Nothing in the form assumes a country or a naming scheme.
  it('creates an account under a name the chart has never seen', async () => {
    const { onCreate, onCreated } = renderModal();

    fillRequired('1125', 'محفظة جوالي');
    fireEvent.change(screen.getByLabelText(copy.subtype), { target: { value: 'e_wallet' } });
    submit();

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(onCreate).toHaveBeenCalledWith({
      code: '1125',
      name: 'محفظة جوالي',
      account_type: 'asset',
      account_subtype: 'e_wallet',
      parent_id: null,
      description: null,
    });
    expect(onCreated).toHaveBeenCalled();
  });

  // A quick template is a shortcut for typing, not a second creation path.
  it('quick templates only prefill the form and stay editable', async () => {
    const { onCreate } = renderModal();

    fireEvent.click(screen.getByRole('button', { name: copy.templateEWallet }));

    expect(screen.getByLabelText(copy.subtype)).toHaveValue('e_wallet');
    expect(screen.getByLabelText(copy.type)).toHaveValue('asset');
    expect(screen.getByLabelText(copy.name)).toHaveValue(copy.subtypeEWallet);

    // The operator overrides every prefilled value before saving.
    fireEvent.change(screen.getByLabelText(copy.name), { target: { value: 'One Cash' } });
    fireEvent.change(screen.getByLabelText(copy.code), { target: { value: '1130' } });
    fireEvent.change(screen.getByLabelText(copy.parentAccount), { target: { value: '10' } });
    submit();

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'One Cash', code: '1130', parent_id: 10 }),
    );
  });

  it('leaves the subtype unset when nobody chooses one', async () => {
    const { onCreate } = renderModal();

    fillRequired('9000', 'Suspense');
    submit();

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ account_subtype: null, account_type: 'asset' }),
    );
  });

  it('keeps the form open and shows what the server refused', async () => {
    const onCreate = vi
      .fn()
      .mockRejectedValue(new Error("Account code '1125' already exists for this company"));
    const { onCreated } = renderModal({ onCreate });

    fillRequired('1125', 'Duplicate');
    submit();

    expect(
      await screen.findByText("Account code '1125' already exists for this company"),
    ).toBeInTheDocument();
    expect(onCreated).not.toHaveBeenCalled();
    expect(screen.getByLabelText(copy.code)).toHaveValue('1125');
  });

  it('offers every subtype, including the ones outside a bank-first chart', () => {
    renderModal();

    const options = Array.from(
      screen.getByLabelText(copy.subtype).querySelectorAll('option'),
    ).map((option) => option.textContent);

    expect(options).toEqual([
      copy.subtypeNone,
      copy.subtypeBank,
      copy.subtypeCash,
      copy.subtypeEWallet,
      copy.subtypeReceivable,
      copy.subtypePayable,
      copy.subtypeRevenue,
      copy.subtypeExpense,
      copy.subtypeOther,
    ]);
  });
});
