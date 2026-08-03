import { useCallback, useState } from 'react';
import axios from 'axios';
import apiClient from '../../api/client';
import type {
  ClientOnboardingRequest,
  ClientOnboardingResult,
  OnboardingDefaults,
} from '../../api/types';

const DEFAULTS_ENDPOINT = '/platform/onboarding/defaults';
const CLIENTS_ENDPOINT = '/platform/onboarding/clients';

/** Every failure the wizard can explain, named after its translation key. */
export type OnboardingErrorKey =
  | 'errorCompanyExists'
  | 'errorAdminEmailExists'
  | 'errorReusedPlatformAdmin'
  | 'errorReusedInactive'
  | 'errorInvalidWindow'
  | 'errorAccessDenied'
  | 'validationPasswordRequired'
  | 'validationPasswordTooWeak'
  | 'errorGeneric';

/**
 * FastAPI answers a domain refusal with a string `detail` and a request-shape
 * refusal with a list of validation objects. Both are flattened to one string
 * so a single set of matchers can classify them.
 */
function detailText(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item
          ? String((item as { msg: unknown }).msg)
          : '',
      )
      .join(' ');
  }
  return '';
}

/**
 * Matched on the wording the backend route produces. The phrases are distinct
 * enough that no matcher can claim another one's message, and anything
 * unrecognised falls through to the generic explanation rather than being
 * silently swallowed.
 */
const ERROR_MATCHERS: ReadonlyArray<readonly [RegExp, OnboardingErrorKey]> = [
  [/^A company named/i, 'errorCompanyExists'],
  [/reuse_existing_user/i, 'errorAdminEmailExists'],
  [/platform administrator cannot/i, 'errorReusedPlatformAdmin'],
  [/deactivated/i, 'errorReusedInactive'],
  [/temporary password is required/i, 'validationPasswordRequired'],
  [/already be expired/i, 'errorInvalidWindow'],
  [/password must/i, 'validationPasswordTooWeak'],
];

function classify(error: unknown): OnboardingErrorKey {
  if (!axios.isAxiosError(error)) return 'errorGeneric';

  const status = error.response?.status ?? null;
  if (status === 401 || status === 403) return 'errorAccessDenied';

  const text = detailText(
    (error.response?.data as { detail?: unknown } | undefined)?.detail,
  );
  for (const [pattern, key] of ERROR_MATCHERS) {
    if (pattern.test(text)) return key;
  }
  return 'errorGeneric';
}

export function useClientOnboarding() {
  const [defaults, setDefaults] = useState<OnboardingDefaults | null>(null);
  const [isLoadingDefaults, setIsLoadingDefaults] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorKey, setErrorKey] = useState<OnboardingErrorKey | null>(null);
  const [result, setResult] = useState<ClientOnboardingResult | null>(null);

  const fetchDefaults = useCallback(async () => {
    setIsLoadingDefaults(true);
    try {
      const response = await apiClient.get<OnboardingDefaults>(DEFAULTS_ENDPOINT);
      setDefaults(response.data);
    } catch {
      // Defaults are a convenience, not a prerequisite: the wizard ships its own
      // fallbacks so a failed lookup never blocks onboarding.
      setDefaults(null);
    } finally {
      setIsLoadingDefaults(false);
    }
  }, []);

  const onboard = useCallback(async (payload: ClientOnboardingRequest) => {
    setIsSubmitting(true);
    setErrorKey(null);
    try {
      const response = await apiClient.post<ClientOnboardingResult>(
        CLIENTS_ENDPOINT,
        payload,
      );
      setResult(response.data);
      return response.data;
    } catch (error) {
      setErrorKey(classify(error));
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  /**
   * Drops the result, and with it the one-time temporary password, so starting
   * a second onboarding cannot leak the previous client's credentials.
   */
  const reset = useCallback(() => {
    setResult(null);
    setErrorKey(null);
  }, []);

  const clearError = useCallback(() => setErrorKey(null), []);

  return {
    defaults,
    isLoadingDefaults,
    isSubmitting,
    errorKey,
    result,
    fetchDefaults,
    onboard,
    reset,
    clearError,
  };
}
