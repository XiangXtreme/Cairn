import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef6ff',
          100: '#d9eaff',
          200: '#bcd8ff',
          300: '#8ebcff',
          400: '#5896ff',
          500: '#326ff3',
          600: '#2454d0',
          700: '#2444a5',
          800: '#243b82',
          900: '#223564'
        }
      },
      boxShadow: {
        soft: '0 18px 55px rgba(15, 23, 42, 0.08)'
      }
    }
  },
  plugins: []
} satisfies Config;
