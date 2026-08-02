import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AccountTypeBadge } from '../../entities/account';

describe('AccountTypeBadge', () => {
  it.each(['asset', 'liability', 'equity', 'income', 'expense'])(
    'renders %s type',
    (type) => {
      render(<AccountTypeBadge type={type} />);
      expect(screen.getByText(type)).toBeInTheDocument();
    },
  );

  it('renders unknown type without crashing', () => {
    render(<AccountTypeBadge type="unknown" />);
    expect(screen.getByText('unknown')).toBeInTheDocument();
  });
});
