/**
 * AccountTypeBadge — entity-layer presentational component.
 *
 * Lives in entities/account/ so that report pages and journal pages can render
 * account-type labels without creating cross-feature imports.
 */
import { useI18n } from '../../i18n';

interface AccountTypeBadgeProps {
  type: string;
}

// The letter mark keeps the type distinguishable without relying on colour.
// It stays Latin on purpose: it is a shape to recognise, not a word to read,
// and the five Arabic names do not start with five different letters.
const typeTones: Record<string, { tone: string; mark: string }> = {
  asset: { tone: 'tone-info', mark: 'A' },
  liability: { tone: 'tone-warning', mark: 'L' },
  equity: { tone: 'tone-violet', mark: 'E' },
  income: { tone: 'tone-success', mark: 'I' },
  expense: { tone: 'tone-rose', mark: 'X' },
};

export function AccountTypeBadge({ type }: AccountTypeBadgeProps) {
  const { t } = useI18n();
  const { tone, mark } = typeTones[type] ?? { tone: 'tone-neutral', mark: '?' };

  const labels: Record<string, string> = {
    asset: t.accountsPage.typeAsset,
    liability: t.accountsPage.typeLiability,
    equity: t.accountsPage.typeEquity,
    income: t.accountsPage.typeIncome,
    expense: t.accountsPage.typeExpense,
  };

  return (
    <span className={`badge badge-uppercase ${tone}`}>
      <span aria-hidden className="font-bold opacity-70">
        {mark}
      </span>
      {/* An unknown type falls back to the raw value rather than an empty badge:
          a new account_type added on the server should still be readable here. */}
      {labels[type] ?? type}
    </span>
  );
}
