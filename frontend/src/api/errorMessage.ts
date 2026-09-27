/* Turn whatever the API returned into something a person can read.
 *
 * FastAPI answers with three different shapes under `detail`, and only the
 * first is a string:
 *
 *   401  "Invalid email or password"
 *   422  [{ loc: [...], msg: "value is not a valid email address", ... }, ...]
 *   403  { code: "PASSWORD_CHANGE_REQUIRED", message: "You must change ..." }
 *
 * Handing the second or third straight to React is not a cosmetic mistake: a
 * component that renders `{error}` throws "Objects are not valid as a React
 * child", which unmounts the whole tree. A mistyped email on the login form
 * turned the page white that way.
 *
 * Most call sites already guard with `typeof detail === 'string'` and fall back
 * to their own wording, which is safe but discards what the server said. This
 * keeps the message.
 */

type Detail =
  | string
  | { msg?: unknown; message?: unknown }
  | Array<{ msg?: unknown; message?: unknown }>
  | undefined;

function readable(entry: { msg?: unknown; message?: unknown }): string | null {
  if (typeof entry?.msg === 'string') return entry.msg;
  if (typeof entry?.message === 'string') return entry.message;
  return null;
}

/**
 * The server's explanation, or `fallback` when there is nothing readable.
 *
 * `fallback` is required: a caller that has no wording of its own would
 * otherwise show an empty alert, which is the blank-screen problem again in a
 * quieter form.
 */
export function errorMessage(error: unknown, fallback: string): string {
  const detail = (
    error as { response?: { data?: { detail?: Detail } } } | null
  )?.response?.data?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    // A 422 can name several fields at once; all of them are worth showing.
    const messages = detail
      .map(readable)
      .filter((message): message is string => Boolean(message));
    if (messages.length) {
      return messages.join('. ');
    }
  }

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const message = readable(detail);
    if (message) {
      return message;
    }
  }

  return fallback;
}
