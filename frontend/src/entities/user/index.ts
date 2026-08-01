/**
 * User and company-user entity types.
 */
export type {
  CompanyUserRole,
  CompanyUser,
  CompanyUserInvitationResponse,
  CompanyUserInvitationValidateResponse,
  CompanyUserInvitationRead,
} from '../../api/types';

export interface UserRead {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}
