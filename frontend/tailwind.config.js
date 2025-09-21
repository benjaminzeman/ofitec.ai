/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Design System Colors from ESTRATEGIA_VISUAL.md
        primary: {
          DEFAULT: '#84CC16', // Lime accent
          50: '#F7FEE7',
          100: '#ECFCCB',
          500: '#84CC16',
          600: '#65A30D',
          700: '#4D7C0F',
        },
        background: {
          DEFAULT: '#000000', // Dark mode primary
          secondary: '#0A0A0A',
          card: '#111111',
          light: '#FFFFFF',
          'light-secondary': '#F8F9FA',
        },
        border: {
          DEFAULT: '#333333',
          light: '#E5E7EB',
        },
        text: {
          primary: '#FFFFFF',
          secondary: '#B3B3B3',
          tertiary: '#666666',
          'light-primary': '#111827',
          'light-secondary': '#6B7280',
          'light-tertiary': '#9CA3AF',
        },
        header: {
          DEFAULT: '#1A1A1A',
          light: '#F3F4F6',
        },
        warn: '#F59E0B',
        danger: '#EF4444',
      },
      borderRadius: {
        card: '12px', // Consistent card radius
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        // No shadows in design system - keep minimal
        none: 'none',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
