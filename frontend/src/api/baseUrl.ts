/**
 * Where the frontend sends API requests.
 *
 * Two shapes are supported:
 *   - an absolute origin, e.g. `http://127.0.0.1:8010` — normal local development,
 *     where the browser talks to Uvicorn directly and CORS applies.
 *   - a relative path, e.g. `/api` — the one-link public demo, where the Vite dev
 *     server proxies `/api/*` to the backend so the browser only ever sees a
 *     single origin and no CORS entry is needed for the tunnel host.
 */

export const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8010';

/**
 * Trailing slashes are stripped because callers concatenate a leading-slash
 * path onto the result, and `/api/` + `/reports` would produce `/api//reports`.
 */
export function resolveApiBaseUrl(
  configured: string | undefined,
  production = false,
): string {
  const trimmed = configured?.trim();

  if (!trimmed) return production ? '/api' : DEFAULT_API_BASE_URL;

  const withoutTrailingSlash = trimmed.replace(/\/+$/, '');

  return withoutTrailingSlash || (production ? '/api' : DEFAULT_API_BASE_URL);
}

export const apiBaseUrl = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  import.meta.env.PROD,
);
