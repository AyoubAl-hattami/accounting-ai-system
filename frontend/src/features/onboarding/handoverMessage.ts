import type { Translations } from '../../i18n/types';

/**
 * The message the platform owner sends to a new client.
 *
 * The backend returns an English copy of this text so that API and CLI callers
 * get something usable without a translation table. The wizard rebuilds it here
 * instead of echoing that field, because the platform owner may be working in
 * Arabic and the client should receive the message in the language it was
 * prepared in. The English output of this builder is identical, line for line,
 * to `app/application/onboarding/handover.py`.
 */

/** `YYYY-MM-DD`, which reads the same in both languages and never ambiguates. */
export function formatHandoverDate(value: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

export interface HandoverMessageInput {
  companyName: string;
  adminEmail: string;
  /** `null` when an existing account was reused and keeps its own password. */
  temporaryPassword: string | null;
  expiresAt: string | null;
}

export function buildHandoverMessage(
  copy: Translations['clientOnboarding'],
  { companyName, adminEmail, temporaryPassword, expiresAt }: HandoverMessageInput,
): string {
  const expiry = formatHandoverDate(expiresAt) ?? copy.handoverNoExpiry;

  const lines = [
    copy.handoverGreeting,
    '',
    copy.handoverIntro,
    '',
    `${copy.handoverLoginUrl}: ${copy.handoverLoginUrlPlaceholder}`,
    `${copy.handoverCompany}: ${companyName}`,
    `${copy.handoverAdminEmail}: ${adminEmail}`,
  ];

  if (temporaryPassword) {
    lines.push(`${copy.handoverTemporaryPassword}: ${temporaryPassword}`);
  }

  lines.push(`${copy.handoverValidUntil}: ${expiry}`, '');
  lines.push(
    temporaryPassword
      ? copy.handoverInstructions
      : copy.handoverInstructionsExistingPassword,
  );

  return lines.join('\n');
}
