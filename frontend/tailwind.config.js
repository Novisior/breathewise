/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#f6f4ee',
        ink: { DEFAULT: '#1d2b2a', soft: '#4b5b59', faint: '#7a8987' },
        brand: { DEFAULT: '#0f766e', dark: '#0b5a54', tint: '#dff1ee' },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Noto Sans', 'Noto Sans Devanagari', 'sans-serif'],
      },
      boxShadow: { card: '0 1px 2px rgba(29,43,42,.06), 0 8px 24px -12px rgba(29,43,42,.18)' },
    },
  },
  plugins: [],
}
