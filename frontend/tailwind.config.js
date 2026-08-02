/** @type {import('tailwindcss').Config} */

/**
 * Every colour in this config resolves to a CSS variable defined in
 * src/styles/globals.css. Light and dark palettes are declared there once,
 * so no component needs a `dark:` variant to stay readable.
 */
const tokens = {
  transparent: 'transparent',
  current: 'currentColor',
  white: '#ffffff',
  black: '#000000',

  background: 'var(--background)',
  surface: {
    DEFAULT: 'var(--surface)',
    muted: 'var(--surface-muted)',
    raised: 'var(--surface-raised)',
    overlay: 'var(--surface-overlay)',
    sunken: 'var(--surface-sunken)',
  },
  backdrop: 'var(--backdrop)',

  foreground: 'var(--foreground)',
  'muted-foreground': 'var(--muted-foreground)',
  'subtle-foreground': 'var(--subtle-foreground)',
  inverse: 'var(--inverse)',

  border: {
    DEFAULT: 'var(--border)',
    subtle: 'var(--border-subtle)',
    strong: 'var(--border-strong)',
  },
  ring: 'var(--ring)',
  'ring-soft': 'var(--ring-soft)',
  'ring-danger': 'var(--ring-danger)',

  primary: {
    DEFAULT: 'var(--primary)',
    solid: 'var(--primary-solid)',
    'solid-hover': 'var(--primary-solid-hover)',
    foreground: 'var(--primary-foreground)',
    soft: 'var(--primary-soft)',
    'soft-hover': 'var(--primary-soft-hover)',
    border: 'var(--primary-border)',
  },
  secondary: {
    DEFAULT: 'var(--secondary)',
    hover: 'var(--secondary-hover)',
    foreground: 'var(--secondary-foreground)',
  },

  success: {
    DEFAULT: 'var(--success)',
    solid: 'var(--success-solid)',
    soft: 'var(--success-soft)',
    border: 'var(--success-border)',
  },
  warning: {
    DEFAULT: 'var(--warning)',
    solid: 'var(--warning-solid)',
    soft: 'var(--warning-soft)',
    border: 'var(--warning-border)',
  },
  danger: {
    DEFAULT: 'var(--danger)',
    solid: 'var(--danger-solid)',
    'solid-hover': 'var(--danger-solid-hover)',
    soft: 'var(--danger-soft)',
    border: 'var(--danger-border)',
  },
  info: {
    DEFAULT: 'var(--info)',
    solid: 'var(--info-solid)',
    soft: 'var(--info-soft)',
    border: 'var(--info-border)',
  },
  violet: {
    DEFAULT: 'var(--violet)',
    soft: 'var(--violet-soft)',
    border: 'var(--violet-border)',
  },
  rose: {
    DEFAULT: 'var(--rose)',
    soft: 'var(--rose-soft)',
    border: 'var(--rose-border)',
  },
  teal: {
    DEFAULT: 'var(--teal)',
    soft: 'var(--teal-soft)',
    border: 'var(--teal-border)',
  },
  neutral: {
    DEFAULT: 'var(--neutral)',
    soft: 'var(--neutral-soft)',
    border: 'var(--neutral-border)',
  },

  // Accounting semantics — used for figures, not chrome.
  debit: 'var(--debit)',
  credit: 'var(--credit)',
  positive: 'var(--positive)',
  negative: 'var(--negative)',

  // Report / chart series.
  'chart-1': 'var(--chart-1)',
  'chart-2': 'var(--chart-2)',
  'chart-3': 'var(--chart-3)',
  'chart-4': 'var(--chart-4)',
  'chart-5': 'var(--chart-5)',
  'chart-grid': 'var(--chart-grid)',

  // Depth layer — frosted chrome and the primary glow halo.
  glass: 'var(--glass)',
  'glass-border': 'var(--glass-border)',
  'primary-glow': 'var(--primary-glow)',
};

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // Tone classes are composed at runtime (`tone-${tone}`), which the content
  // scanner cannot see, so they must be pinned explicitly.
  safelist: [
    'tone-neutral',
    'tone-primary',
    'tone-success',
    'tone-warning',
    'tone-danger',
    'tone-info',
    'tone-violet',
    'tone-rose',
    'tone-teal',
  ],
  theme: {
    colors: tokens,
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      borderColor: {
        DEFAULT: 'var(--border)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        card: 'var(--shadow-card)',
        floating: 'var(--shadow-floating)',
        glow: 'var(--shadow-glow)',
        none: 'none',
      },
      backgroundImage: {
        'gradient-app': 'var(--gradient-app)',
        'gradient-primary': 'var(--gradient-primary)',
        'gradient-brand': 'var(--gradient-brand)',
        'gradient-card': 'var(--gradient-card)',
        'gradient-nav-active': 'var(--gradient-nav-active)',
      },
      // The motion scale. Keyframes and the `animate-*` utilities that use
      // them live in globals.css, next to the duration/easing tokens.
      transitionDuration: {
        fast: 'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
      },
      transitionTimingFunction: {
        standard: 'var(--ease-standard)',
        emphasized: 'var(--ease-emphasized)',
      },
    },
  },
  plugins: [],
};
