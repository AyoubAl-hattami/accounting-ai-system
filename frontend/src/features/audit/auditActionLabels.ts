/**
 * Audit action label utilities.
 * Kept in a separate file so AuditActionBadge.tsx only exports one component
 * (satisfies react-refresh/only-export-components lint rule).
 */

/**
 * Convert a snake_case action key to a readable i18n label.
 * Looks up the camelCase version of the key in the auditLogs translation map.
 * Falls back to Title Case splitting on underscores.
 */
export function getActionLabel(
  action: string,
  auditT: Record<string, string>
): string {
  // snake_case → camelCase
  const camelKey = action
    .toLowerCase()
    .replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());

  if (auditT[camelKey]) return auditT[camelKey];

  // Fallback: Title-case split on _ - | spaces
  return action
    .split(/[_\-\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
