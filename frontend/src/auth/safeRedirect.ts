/**
 * A `?redirect=` value is attacker-supplied: anyone can send a victim a login
 * link carrying one. Only same-origin paths are honoured.
 *
 * `startsWith('/')` alone is not the check. `//evil.tld` is a protocol-relative
 * URL and navigates off-origin, and browsers normalise the backslash in
 * `/\evil.tld` to a second slash, so both are rejected too.
 */
export function safeRedirectTarget(raw: string | null): string | null {
  if (!raw) return null;
  if (!raw.startsWith('/')) return null;
  // Reject //host and /\host, which both leave this origin.
  if (raw.startsWith('//') || raw.startsWith('/\\')) return null;
  return raw;
}
