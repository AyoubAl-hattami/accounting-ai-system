import { describe, it, expect } from 'vitest';
import { buildHandoverMessage } from '../../features/onboarding/handoverMessage';
import { ar, en } from '../../i18n/translations';

const INPUT = {
  companyName: 'Northwind Trading',
  adminEmail: 'admin@northwind.test',
  temporaryPassword: 'Sw1ftPelican42',
  expiresAt: '2026-09-30T23:59:59Z',
};

describe('client handover message', () => {
  // The English text is the contract the backend also implements, so it is
  // asserted line for line rather than by substring.
  it('renders the agreed English message', () => {
    expect(buildHandoverMessage(en.clientOnboarding, INPUT)).toBe(
      [
        'Hello,',
        '',
        'Your accounting system access has been created.',
        '',
        'Login URL: [add your domain here]',
        'Company: Northwind Trading',
        'Admin email: admin@northwind.test',
        'Temporary password: Sw1ftPelican42',
        'Subscription valid until: 2026-09-30',
        '',
        'Please log in and change your password immediately. You can then invite '
          + 'your team members from Company Users.',
      ].join('\n'),
    );
  });

  it('renders the agreed Arabic message', () => {
    const message = buildHandoverMessage(ar.clientOnboarding, INPUT);
    expect(message).toContain('مرحبًا،');
    expect(message).toContain('تم إنشاء حساب شركتكم في نظام المحاسبة.');
    expect(message).toContain('رابط الدخول: [ضع رابط الموقع هنا]');
    expect(message).toContain('كلمة المرور المؤقتة: Sw1ftPelican42');
    expect(message).toContain('الاشتراك صالح حتى: 2026-09-30');
    expect(message).toContain('يرجى تسجيل الدخول وتغيير كلمة المرور مباشرة.');
  });

  // A reused account keeps its own credentials, so there is no password to hand
  // over and the message must not pretend otherwise.
  it('omits the password line when an existing account was reused', () => {
    const message = buildHandoverMessage(en.clientOnboarding, {
      ...INPUT,
      temporaryPassword: null,
    });
    expect(message).not.toContain('Temporary password');
    expect(message).toContain('Please log in with your existing password.');
  });

  it('names the missing expiry instead of printing an empty date', () => {
    const message = buildHandoverMessage(en.clientOnboarding, {
      ...INPUT,
      expiresAt: null,
    });
    expect(message).toContain('Subscription valid until: No expiry date');
  });
});
