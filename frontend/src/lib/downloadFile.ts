import { getToken } from '../auth/token';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8010';

/**
 * Download a file from an authenticated API endpoint.
 *
 * Fetches the URL with the current bearer token, then triggers a
 * browser download from the response blob.  The filename is extracted
 * from the Content-Disposition header when available, falling back to
 * the provided default.
 */
export async function downloadFile(
  path: string,
  params: Record<string, string | number | null | undefined>,
  defaultFilename: string,
): Promise<void> {
  const token = getToken();
  if (!token) throw new Error('Not authenticated');

  // Build query string, skipping null/undefined values
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== '') {
      query.set(key, String(value));
    }
  }

  const url = `${API_BASE}${path}?${query.toString()}`;

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`Export failed (${response.status})`);
  }

  const blob = await response.blob();

  // Try to extract filename from Content-Disposition header
  let filename = defaultFilename;
  const disposition = response.headers.get('Content-Disposition');
  if (disposition) {
    const match = disposition.match(/filename="?([^";\n]+)"?/i);
    if (match) filename = match[1];
  }

  // Trigger browser download
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();

  // Cleanup
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}
