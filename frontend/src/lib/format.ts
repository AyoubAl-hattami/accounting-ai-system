/**
 * Format a number as full currency (e.g. "1,234.56").
 * Used in tables and detail views where exact values matter.
 */
export function formatCurrency(n: number): string {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Format a signed figure using the accounting convention: negatives are wrapped
 * in parentheses instead of taking a minus prefix, so columns stay aligned and
 * losses stay unambiguous once the report is printed in black and white.
 */
export function formatSignedCurrency(n: number): string {
  return n < 0 ? `(${formatCurrency(Math.abs(n))})` : formatCurrency(n);
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
