/**
 * Company and company-user management feature (clean architecture pilot).
 *
 * Not wired into app routes until baseline parity is verified.
 */
export { useCompanies } from './useCompanies';
export {
  listCompanies,
  getCompany,
  createCompany,
  updateCompany,
  listCompanyUsers,
  updateCompanyUserRole,
  deactivateCompanyUser,
  inviteUser,
  validateInvitation,
  acceptInvitation,
  listPendingInvitations,
  cancelInvitation,
} from './api';
