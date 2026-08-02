/**
 * Account entity layer.
 *
 * Exports canonical frontend types (mirroring the backend AccountRead schema)
 * and the AccountTypeBadge presentational component.  Having the badge here
 * lets report pages and journal pages render account-type labels without
 * creating cross-feature imports inside features/.
 */
export type { Account } from '../../api/types';
export type { AccountSeedResult } from '../../api/types';
export { AccountTypeBadge } from './AccountTypeBadge';
