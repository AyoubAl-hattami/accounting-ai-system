import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SubscriptionStatusBadge from '../../features/subscriptions/SubscriptionStatusBadge';
import { I18nProvider } from '../../i18n';
import { en } from '../../i18n/translations';
import type { SubscriptionStatus } from '../../api/types';

const STATUSES: SubscriptionStatus[] = ['trial', 'active', 'past_due', 'suspended', 'cancelled'];

const renderBadge = (status: SubscriptionStatus) =>
  render(
    <I18nProvider>
      <SubscriptionStatusBadge status={status} />
    </I18nProvider>,
  );

describe('SubscriptionStatusBadge', () => {
  it('renders each status with its translated label and tone', () => {
    const tones: Record<SubscriptionStatus, string> = {
      trial: 'tone-primary',
      active: 'tone-success',
      past_due: 'tone-warning',
      suspended: 'tone-danger',
      cancelled: 'tone-neutral',
    };

    for (const status of STATUSES) {
      const { unmount } = renderBadge(status);
      const badge = screen.getByText(en.subscriptionStatus[status]);
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass(tones[status]);
      unmount();
    }
  });
});
