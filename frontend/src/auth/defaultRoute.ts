import type { User } from './AuthContext';

export function defaultAuthenticatedRoute(user: Pick<User, 'is_superuser'>): string {
  return user.is_superuser ? '/platform/dashboard' : '/dashboard';
}
