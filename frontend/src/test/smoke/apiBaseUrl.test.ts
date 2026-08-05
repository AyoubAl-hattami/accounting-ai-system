import { describe, expect, it } from 'vitest';

import { DEFAULT_API_BASE_URL, resolveApiBaseUrl } from '../../api/baseUrl';

describe('resolveApiBaseUrl', () => {
  it('falls back to the local backend when unset', () => {
    expect(resolveApiBaseUrl(undefined)).toBe(DEFAULT_API_BASE_URL);
    expect(resolveApiBaseUrl('')).toBe(DEFAULT_API_BASE_URL);
    expect(resolveApiBaseUrl('   ')).toBe(DEFAULT_API_BASE_URL);
  });

  it('keeps a relative base so the public demo stays on one origin', () => {
    expect(resolveApiBaseUrl('/api')).toBe('/api');
  });

  it('keeps an absolute base for normal local development', () => {
    expect(resolveApiBaseUrl('http://127.0.0.1:8010')).toBe('http://127.0.0.1:8010');
  });

  it('strips trailing slashes so callers can concatenate leading-slash paths', () => {
    expect(resolveApiBaseUrl('/api/')).toBe('/api');
    expect(resolveApiBaseUrl('http://127.0.0.1:8010/')).toBe('http://127.0.0.1:8010');
  });
});
