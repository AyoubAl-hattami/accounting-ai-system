import { describe, expect, it } from 'vitest';
import { defaultAuthenticatedRoute } from '../../auth/defaultRoute';
import { isPlatformPage } from '../../auth/permissions';

describe('platform session routing', () => {
  it('lands platform administrators on the platform dashboard', () => {
    expect(defaultAuthenticatedRoute({ is_superuser: true })).toBe('/platform/dashboard');
  });

  it('keeps tenant users on the company dashboard', () => {
    expect(defaultAuthenticatedRoute({ is_superuser: false })).toBe('/dashboard');
  });

  it('registers the platform dashboard as platform-only', () => {
    expect(isPlatformPage('/platform/dashboard')).toBe(true);
  });
});
