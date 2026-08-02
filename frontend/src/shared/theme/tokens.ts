/**
 * Semantic design tokens for the accounting AI system.
 *
 * CSS variables are the authoritative source for runtime colors.
 * This file exposes TypeScript constants for consumers (charts, canvas,
 * SVG) that cannot consume CSS variables directly.
 *
 * Light/dark switching is handled by redefining CSS variables on `html.light`.
 * JavaScript consumers must read `getComputedStyle` if they need the live value.
 */

// ── Foundation palette literals (do not use in components) ─────────────────

const _brand = {
  400: '#818cf8',
  500: '#6366f1',
  600: '#4f46e5',
  700: '#4338ca',
} as const;

const _surface = {
  900: '#0a0a0f',
  800: '#0f0f17',
  700: '#14141f',
  600: '#1a1a28',
  500: '#22222f',
} as const;

// ── Semantic token constants (dark-mode defaults) ───────────────────────────
// These values must stay in sync with the CSS variables in globals.css.
// When a light-mode override is added to CSS, add a parallel entry here.

export const tokens = {
  /** Page / outermost background */
  colorPage: _surface[900],
  /** Default card / panel surface */
  colorSurface: _surface[800],
  /** Subtle inset surface */
  colorSurfaceSubtle: _surface[700],
  /** Elevated modal / popover surface */
  colorSurfaceElevated: _surface[600],
  /** Overlay / deepest surface */
  colorSurfaceOverlay: _surface[500],

  /** Primary body text */
  colorContent: '#f3f4f6',
  /** Secondary text */
  colorContentSecondary: '#9ca3af',
  /** Muted / placeholder text */
  colorContentMuted: '#6b7280',
  /** Text on accent background */
  colorContentInverse: _surface[900],

  /** Default border */
  colorBorder: 'rgba(255,255,255,0.08)',
  /** Subtle separator */
  colorBorderSubtle: 'rgba(255,255,255,0.04)',
  /** Keyboard focus ring */
  colorFocus: _brand[500],

  /** Primary interactive color */
  colorAccent: _brand[600],
  /** Hovered primary interactive */
  colorAccentHover: _brand[700],
  /** Tinted accent background */
  colorAccentSubtle: 'rgba(99,102,241,0.12)',
  /** Text/icon on accent fill */
  colorOnAccent: '#ffffff',

  /** Status */
  colorSuccess: '#22c55e',
  colorWarning: '#f59e0b',
  colorDanger:  '#ef4444',
  colorInfo:    '#3b82f6',

  /** Accounting */
  colorDebit:   '#60a5fa',
  colorCredit:  '#34d399',
  colorBalance: '#a78bfa',
} as const;

// ── Chart theme ─────────────────────────────────────────────────────────────

export const chartTheme = {
  /** Ordered categorical series (use in sequence for multi-series charts) */
  series: [
    _brand[400],       // violet
    '#34d399',         // emerald (credit)
    '#f59e0b',         // amber
    '#60a5fa',         // blue (debit)
    '#f87171',         // red
    '#a78bfa',         // violet-400
    '#fbbf24',         // yellow
    '#4ade80',         // green
  ],

  /** Revenue vs expense */
  revenue: '#34d399',
  expense: '#f87171',

  /** Asset / liability / equity */
  asset:   '#60a5fa',
  liability: '#f87171',
  equity:  '#a78bfa',

  /** Debit / credit */
  debit:   tokens.colorDebit,
  credit:  tokens.colorCredit,

  /** Grid and axis */
  grid:    'rgba(255,255,255,0.06)',
  axis:    'rgba(255,255,255,0.30)',

  /** Tooltip */
  tooltipBackground: _surface[600],
  tooltipBorder:     'rgba(255,255,255,0.08)',
  tooltipText:       '#f3f4f6',

  /** Labels */
  label:   '#9ca3af',
} as const;

export type ChartTheme = typeof chartTheme;
export type Tokens = typeof tokens;
