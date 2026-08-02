import { BookOpenCheck, Calculator, Eye, ScrollText, ShieldCheck, Stamp } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { CompanyUserRole } from '../../api/types';
import { useI18n } from '../../i18n';

interface CompanyUserRoleBadgeProps {
  role: CompanyUserRole;
}

// Each role carries an icon so it stays distinguishable without colour vision.
const roleTones: Record<CompanyUserRole, { tone: string; icon: LucideIcon }> = {
  admin: { tone: 'tone-rose', icon: ShieldCheck },
  accountant: { tone: 'tone-info', icon: Calculator },
  reviewer: { tone: 'tone-violet', icon: BookOpenCheck },
  approver: { tone: 'tone-success', icon: Stamp },
  auditor: { tone: 'tone-warning', icon: ScrollText },
  viewer: { tone: 'tone-neutral', icon: Eye },
};

export default function CompanyUserRoleBadge({ role }: CompanyUserRoleBadgeProps) {
  const { t } = useI18n();
  const { tone, icon: Icon } = roleTones[role] ?? { tone: 'tone-neutral', icon: Eye };
  const label = t.companyUsersPage.roles[role] ?? role;

  return (
    <span className={`badge ${tone}`}>
      <Icon aria-hidden className="h-3 w-3" />
      {label}
    </span>
  );
}
