import { Building2, CreditCard, LayoutDashboard, UserPlus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n';

export default function PlatformTenantAccessNotice() {
  const { t } = useI18n();
  const copy = t.platformAccessNotice;

  return (
    <section className="mx-auto flex min-h-[55vh] max-w-2xl items-center justify-center py-10">
      <div className="w-full text-center">
        <span className="badge tone-info mx-auto mb-5 h-12 w-12 justify-center rounded-lg p-0">
          <Building2 aria-hidden className="h-5 w-5" />
        </span>
        <h2 className="text-xl font-semibold text-foreground">{copy.title}</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
          {copy.message}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Link to="/platform/dashboard" className="btn btn-primary">
            <LayoutDashboard aria-hidden className="h-4 w-4" />
            {t.nav.platformDashboard}
          </Link>
          <Link to="/platform/subscriptions" className="btn btn-secondary">
            <CreditCard aria-hidden className="h-4 w-4" />
            {t.nav.platformSubscriptions}
          </Link>
          <Link to="/platform/onboarding" className="btn btn-secondary">
            <UserPlus aria-hidden className="h-4 w-4" />
            {t.nav.platformOnboarding}
          </Link>
        </div>
      </div>
    </section>
  );
}
