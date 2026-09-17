import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AccountTypeBadge } from '../../entities/account';
import { I18nProvider } from '../../i18n';
import { en, ar } from '../../i18n/translations';

/* The badge used to print the API's own word -- "asset", "liability" -- so an
 * Arabic page showed Arabic subtypes in one column and English types in the
 * next. It reads from the catalogue now, which is why these assert the label
 * rather than the value. */

function renderBadge(type: string) {
  return render(
    <I18nProvider>
      <AccountTypeBadge type={type} />
    </I18nProvider>,
  );
}

describe('AccountTypeBadge', () => {
  it.each([
    ['asset', en.accountsPage.typeAsset],
    ['liability', en.accountsPage.typeLiability],
    ['equity', en.accountsPage.typeEquity],
    ['income', en.accountsPage.typeIncome],
    ['expense', en.accountsPage.typeExpense],
  ])('names the %s type in words, not in the API value', (type, label) => {
    renderBadge(type);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it('has an Arabic name for every type it can render', () => {
    // The gap this closes: a missing Arabic string would silently fall back to
    // the raw value and put English back in the column.
    for (const key of [
      'typeAsset',
      'typeLiability',
      'typeEquity',
      'typeIncome',
      'typeExpense',
    ] as const) {
      expect(ar.accountsPage[key]).toBeTruthy();
      expect(ar.accountsPage[key]).not.toBe(en.accountsPage[key]);
    }
  });

  it('falls back to the raw value for a type it does not know', () => {
    // A new account_type added on the server should stay readable rather than
    // rendering an empty badge.
    renderBadge('unknown');
    expect(screen.getByText('unknown')).toBeInTheDocument();
  });
});
