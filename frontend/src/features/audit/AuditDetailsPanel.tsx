/**
 * AuditDetailsPanel
 * Renders old_values / new_values as a clean Before / After comparison table.
 * Sensitive fields are filtered out. Nested objects are handled gracefully.
 */

import { useI18n } from '../../i18n';

// ── Sensitive field names that must never be shown in UI ──────────────────────
const SENSITIVE_FIELDS = new Set([
  'password',
  'password_hash',
  'hashed_password',
  'token',
  'raw_token',
  'invite_token',
  'jwt',
  'secret',
  'api_key',
  'access_token',
  'refresh_token',
  'reset_token',
  'verification_token',
]);

// ── Render a single cell value safely ────────────────────────────────────────
function renderValue(val: unknown): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'boolean') return val ? 'true' : 'false';
  if (typeof val === 'number' || typeof val === 'string') return String(val);
  if (Array.isArray(val)) {
    if (val.length === 0) return '[]';
    return `[${val.length} item${val.length !== 1 ? 's' : ''}]`;
  }
  if (typeof val === 'object') {
    try {
      const str = JSON.stringify(val, null, 0);
      return str.length > 80 ? str.slice(0, 80) + '…' : str;
    } catch {
      return '[object]';
    }
  }
  return String(val);
}

// ── Merge keys from both objects, excluding sensitive and empty fields ────────
function mergeKeys(
  old: Record<string, unknown> | null,
  next: Record<string, unknown> | null
): string[] {
  const keys = new Set([
    ...Object.keys(old ?? {}),
    ...Object.keys(next ?? {}),
  ]);

  return Array.from(keys).filter((k) => {
    if (SENSITIVE_FIELDS.has(k.toLowerCase())) return false;
    const oldVal = old?.[k];
    const newVal = next?.[k];
    // Skip if both are null/undefined/empty-object
    if (
      (oldVal === null || oldVal === undefined) &&
      (newVal === null || newVal === undefined)
    )
      return false;
    if (
      typeof oldVal === 'object' &&
      !Array.isArray(oldVal) &&
      oldVal !== null &&
      Object.keys(oldVal as object).length === 0 &&
      (newVal === null || newVal === undefined)
    )
      return false;
    return true;
  });
}

// ── Convert snake_case key to readable label ──────────────────────────────────
function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Determine if a field changed ──────────────────────────────────────────────
function hasChanged(
  key: string,
  old: Record<string, unknown> | null,
  next: Record<string, unknown> | null
): boolean {
  if (!old || !next) return false;
  return JSON.stringify(old[key]) !== JSON.stringify(next[key]);
}

// ─────────────────────────────────────────────────────────────────────────────

interface AuditDetailsPanelProps {
  oldValues: Record<string, unknown> | null;
  newValues: Record<string, unknown> | null;
}

export default function AuditDetailsPanel({
  oldValues,
  newValues,
}: AuditDetailsPanelProps) {
  const { t } = useI18n();

  const hasBoth = !!oldValues && !!newValues;
  const hasOld = !!oldValues;
  const hasNew = !!newValues;

  const keys = hasOld || hasNew ? mergeKeys(oldValues, newValues) : [];

  if (keys.length === 0) {
    return <p className="py-1 text-xs italic text-subtle-foreground">{t.auditLogs.noDetails}</p>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border-subtle bg-surface">
      <div className="table-wrap">
        <table className="w-full border-collapse text-xs">
          <caption className="sr-only">{t.auditLogs.auditDetails}</caption>
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th scope="col" className="overline w-1/3 px-3 py-2 text-start">
                {t.auditLogs.field}
              </th>
              {hasBoth ? (
                <>
                  <th scope="col" className="overline w-1/3 px-3 py-2 text-start">
                    {t.auditLogs.before}
                  </th>
                  <th scope="col" className="overline w-1/3 px-3 py-2 text-start">
                    {t.auditLogs.after}
                  </th>
                </>
              ) : (
                <th scope="col" className="overline px-3 py-2 text-start">
                  {hasOld ? t.auditLogs.previousValue : t.auditLogs.value}
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {keys.map((key) => {
              const changed = hasBoth && hasChanged(key, oldValues, newValues);
              const oldStr = renderValue(oldValues?.[key]);
              const newStr = renderValue(newValues?.[key]);

              return (
                <tr key={key} className={changed ? 'bg-primary-soft' : undefined}>
                  <th scope="row" className="px-3 py-2 text-start align-top font-medium text-muted-foreground">
                    {humanizeKey(key)}
                    {changed && <span className="badge badge-uppercase tone-primary ms-1.5">{t.auditLogs.changed}</span>}
                  </th>

                  {hasBoth ? (
                    <>
                      <td className="max-w-[12rem] break-all px-3 py-2 align-top">
                        <ValueBadge value={oldStr} changed={changed} side="old" />
                      </td>
                      <td className="max-w-[12rem] break-all px-3 py-2 align-top">
                        <ValueBadge value={newStr} changed={changed} side="new" />
                      </td>
                    </>
                  ) : (
                    <td className="break-all px-3 py-2 align-top text-muted-foreground">
                      {hasOld ? oldStr : newStr}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * A changed pair is shown as before/after chips so the difference survives
 * greyscale printing and does not rely on colour alone.
 */
function ValueBadge({ value, changed, side }: { value: string; changed: boolean; side: 'old' | 'new' }) {
  if (!changed) {
    return <span className="text-muted-foreground">{value}</span>;
  }
  return (
    <span className={`badge ${side === 'old' ? 'tone-danger line-through' : 'tone-success'} break-all`}>
      {value}
    </span>
  );
}
