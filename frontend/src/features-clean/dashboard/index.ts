/**
 * Dashboard feature (clean architecture pilot).
 *
 * Not wired into app routes until baseline parity is verified.
 */
export { useDashboardData } from './useDashboardData';
export { fetchDashboardSnapshot } from './api';
export type { DashboardSnapshot } from './api';
