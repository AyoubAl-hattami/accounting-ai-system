/**
 * Shared API base client.
 *
 * All feature API modules should import the axios instance from here
 * rather than from `src/api/client` directly.  This indirection allows
 * the transport layer to be swapped or mocked without touching feature code.
 */
export { default as apiClient } from '../../api/client';
export type { PaginatedResponse } from '../../api/types';
