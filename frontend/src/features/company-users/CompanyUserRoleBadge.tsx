import type { CompanyUserRole } from '../../api/types';

interface CompanyUserRoleBadgeProps {
  role: CompanyUserRole;
}

export default function CompanyUserRoleBadge({ role }: CompanyUserRoleBadgeProps) {
  let colorClass = 'bg-white/[0.04] text-gray-400 border-white/[0.06]';

  switch (role) {
    case 'admin':
      colorClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      break;
    case 'accountant':
      colorClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      break;
    case 'reviewer':
      colorClass = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      break;
    case 'approver':
      colorClass = 'bg-green-500/10 text-green-400 border-green-500/20';
      break;
    case 'auditor':
      colorClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      break;
    case 'viewer':
      colorClass = 'bg-white/[0.06] text-gray-300 border-white/[0.08]';
      break;
  }

  const label = role.charAt(0).toUpperCase() + role.slice(1);

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {label}
    </span>
  );
}
