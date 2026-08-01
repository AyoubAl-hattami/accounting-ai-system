/**
 * Accounts feature (clean architecture pilot).
 *
 * Not wired into app routes until baseline parity is verified.
 * See features-clean/README.md for migration protocol.
 */
export { useAccounts } from './useAccounts';
export { listAccounts, seedDefaultAccounts, createAccount, updateAccount } from './api';
