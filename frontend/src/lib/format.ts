/**
 * Format a number as full currency (e.g. "1,234.56").
 * Used in tables and detail views where exact values matter.
 */
export function formatCurrency(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Below half a cent a figure rounds to 0.00, so it is treated as zero. */
const ZERO_THRESHOLD = 0.005;

export type AmountTone = 'positive' | 'negative' | 'zero';

/**
 * Read the sign of a figure. Only apply this to values that are genuinely
 * signed — a net movement, a balance, a difference, a bottom line. Debit and
 * credit columns are conventionally positive magnitudes and carry no sign.
 */
export function getAmountTone(n: number | null | undefined): AmountTone {
  if (n == null || !Number.isFinite(n) || Math.abs(n) < ZERO_THRESHOLD) return 'zero';
  return n > 0 ? 'positive' : 'negative';
}

/**
 * Format a signed figure with an explicit sign, for on-screen reading where
 * colour and a leading +/− are quicker to scan than parentheses.
 * `showPlus` is opt-in: a balance reads better bare, a net movement does not.
 */
export function formatSignedMoney(n: number, showPlus = false, compact = false): string {
  const format = compact ? formatCompactCurrency : formatCurrency;
  const tone = getAmountTone(n);
  if (tone === 'zero') return format(0);
  const body = format(Math.abs(n));
  return tone === 'negative' ? `-${body}` : showPlus ? `+${body}` : body;
}

/** Decimal figures arrive from the API as strings; anything unparseable is 0. */
export function parseAmount(value: string | number | null | undefined): number {
  if (value == null) return 0;
  const n = typeof value === 'number' ? value : parseFloat(value);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Format a number as compact currency (e.g. "1.2K", "3.5M").
 * Used in dashboard cards and summaries where space is limited.
 */
export function formatCompactCurrency(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return formatCurrency(n);
}

/**
 * Format a date string to a short readable date.
 * Returns '—' for null, undefined, or invalid values.
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString();
}
