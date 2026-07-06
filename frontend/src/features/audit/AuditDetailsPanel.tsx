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

  if (!hasOld && !hasNew) {
    return (
      <div className="text-xs text-gray-500 italic py-1">
        {t.auditLogs.noDetails}
      </div>
    );
  }

  const keys = mergeKeys(oldValues, newValues);

  if (keys.length === 0) {
    return (
      <div className="text-xs text-gray-500 italic py-1">
        {t.auditLogs.noDetails}
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-xl overflow-hidden border border-white/[0.06] bg-black/[0.18]">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="border-b border-white/[0.06] bg-white/[0.02]">
            <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wider w-1/3">
              {t.auditLogs.field}
            </th>
            {hasBoth ? (
              <>
                <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wider w-1/3">
                  {t.auditLogs.before}
                </th>
                <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wider w-1/3">
                  {t.auditLogs.after}
                </th>
              </>
            ) : hasOld ? (
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wider">
                {t.auditLogs.previousValue}
              </th>
            ) : (
              <th className="py-2 px-3 text-left font-semibold text-gray-500 uppercase tracking-wider">
                {t.auditLogs.value}
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.03]">
          {keys.map((key) => {
            const changed = hasBoth && hasChanged(key, oldValues, newValues);
            const oldStr = renderValue(oldValues?.[key]);
            const newStr = renderValue(newValues?.[key]);

            return (
              <tr
                key={key}
                className={
                  changed
                    ? 'bg-indigo-500/[0.05] border-l-2 border-l-indigo-500/40'
                    : 'hover:bg-white/[0.01]'
                }
              >
                {/* Field name */}
                <td className="py-2 px-3 font-mono text-gray-400 align-top">
                  {humanizeKey(key)}
                  {changed && (
                    <span className="ml-1.5 inline-block rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-[9px] font-semibold px-1.5 py-0.5 uppercase leading-none align-middle">
                      {t.auditLogs.changed}
                    </span>
                  )}
                </td>

                {hasBoth ? (
                  <>
                    {/* Before */}
                    <td className="py-2 px-3 text-gray-400 align-top max-w-[12rem] break-all">
                      <ValueBadge value={oldStr} changed={changed} side="old" />
                    </td>
                    {/* After */}
                    <td className="py-2 px-3 text-gray-200 align-top max-w-[12rem] break-all">
                      <ValueBadge value={newStr} changed={changed} side="new" />
                    </td>
                  </>
                ) : hasOld ? (
                  <td className="py-2 px-3 text-gray-300 align-top break-all">
                    {oldStr}
                  </td>
                ) : (
                  <td className="py-2 px-3 text-gray-200 align-top break-all">
                    {newStr}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Tiny badge to style old vs new values when changed ───────────────────────
function ValueBadge({
  value,
  changed,
  side,
}: {
  value: string;
  changed: boolean;
  side: 'old' | 'new';
}) {
  if (!changed) {
    return <span className="text-gray-400">{value}</span>;
  }
  if (side === 'old') {
    return (
      <span className="inline-block rounded bg-red-500/10 border border-red-500/20 text-red-400 px-1.5 py-0.5 break-all">
        {value}
      </span>
    );
  }
  return (
    <span className="inline-block rounded bg-green-500/10 border border-green-500/20 text-green-400 px-1.5 py-0.5 break-all">
      {value}
    </span>
  );
}
