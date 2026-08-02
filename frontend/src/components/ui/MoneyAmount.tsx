import { formatSignedMoney, getAmountTone, parseAmount } from '../../lib/format';

interface MoneyAmountProps {
  /** Decimal strings straight from the API are accepted and parsed. */
  value: string | number | null | undefined;
  /** Prefix positives with "+". Suits net movements; a balance reads better bare. */
  showPlus?: boolean;
  /** Render null/undefined as a muted dash rather than 0.00. */
  dashWhenEmpty?: boolean;
  /** Abbreviate to "1.2K" / "3.5M" where the space is tight, as on dashboard cards. */
  compact?: boolean;
  className?: string;
}

/**
 * A figure whose sign carries meaning: green above zero, red below, muted at
 * zero. Use it for balances, movements, differences and bottom lines — never
 * for debit or credit columns, which are positive magnitudes by convention and
 * would be misread as gains and losses if they were coloured this way.
 */
export default function MoneyAmount({
  value,
  showPlus = false,
  dashWhenEmpty = false,
  compact = false,
  className = '',
}: MoneyAmountProps) {
  if (dashWhenEmpty && (value == null || value === '')) {
    return <span className={`amount-zero ${className}`}>—</span>;
  }

  const amount = parseAmount(value);
  const tone = getAmountTone(amount);

  return (
    <span className={`amount-${tone} ${className}`} data-amount-tone={tone}>
      {formatSignedMoney(amount, showPlus, compact)}
    </span>
  );
}
