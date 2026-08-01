/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        // ── Foundation palette (keep for one-off overrides and legacy) ────────
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        surface: {
          900: '#0a0a0f',
          800: '#0f0f17',
          700: '#14141f',
          600: '#1a1a28',
          500: '#22222f',
        },

        // ── Semantic tokens (resolve to CSS variables) ─────────────────────
        // Surfaces
        page:             'var(--color-page)',
        'surface-subtle':   'var(--color-surface-subtle)',
        'surface-elevated': 'var(--color-surface-elevated)',
        'surface-overlay':  'var(--color-surface-overlay)',

        // Content
        content:           'var(--color-content)',
        'content-secondary': 'var(--color-content-secondary)',
        'content-muted':     'var(--color-content-muted)',
        'content-inverse':   'var(--color-content-inverse)',

        // Borders
        border:       'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',
        focus:        'var(--color-focus)',

        // Accent
        accent:        'var(--color-accent)',
        'accent-hover':  'var(--color-accent-hover)',
        'accent-subtle': 'var(--color-accent-subtle)',
        'on-accent':     'var(--color-on-accent)',

        // Status
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger:  'var(--color-danger)',
        info:    'var(--color-info)',

        // Accounting
        debit:   'var(--color-debit)',
        credit:  'var(--color-credit)',
        balance: 'var(--color-balance)',
      },
      // Override surface to also include the semantic 'surface' token
      // (surface-800 stays as foundation; `surface` alone → CSS var)
      backgroundColor: ({ theme }) => ({
        surface: 'var(--color-surface)',
      }),
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      borderRadius: {
        semantic: 'var(--radius-md)',
      },
    },
  },
  plugins: [],
}
