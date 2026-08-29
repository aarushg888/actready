/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        background: 'hsl(var(--background) / <alpha-value>)',
        foreground: 'hsl(var(--foreground) / <alpha-value>)',
        muted: {
          DEFAULT: 'hsl(var(--muted) / <alpha-value>)',
          foreground: 'hsl(var(--muted-foreground) / <alpha-value>)',
        },
        border: 'hsl(var(--border) / <alpha-value>)',
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
        },
        ring: 'hsl(var(--ring) / <alpha-value>)',
        // Semantic status colors — the only "loud" colors in the app
        status: {
          satisfied: 'hsl(var(--status-satisfied) / <alpha-value>)',
          'satisfied-fg': 'hsl(var(--status-satisfied-fg) / <alpha-value>)',
          partial: 'hsl(var(--status-partial) / <alpha-value>)',
          'partial-fg': 'hsl(var(--status-partial-fg) / <alpha-value>)',
          missing: 'hsl(var(--status-missing) / <alpha-value>)',
          'missing-fg': 'hsl(var(--status-missing-fg) / <alpha-value>)',
        },
      },
      borderRadius: {
        card: '0.5rem',
        chip: '0.375rem',
      },
      fontSize: {
        '13': ['0.8125rem', { lineHeight: '1.2rem' }],
      },
      maxWidth: {
        content: '1200px',
      },
    },
  },
  plugins: [],
}
