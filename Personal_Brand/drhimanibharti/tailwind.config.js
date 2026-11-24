/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0F1E36',
          800: '#1B365D', // Primary Brand Deep Clinical Navy
          700: '#234677',
          600: '#2D5894',
          100: '#E8EFF9',
          50: '#F0F5FD',
        },
        teal: {
          700: '#0B7A70',
          600: '#0D9488', // Secondary Accent Calming Teal
          500: '#14B8A6',
          100: '#CCFBF1',
          50: '#F0FDFA',
        },
        slate: {
          850: '#1E293B', // Slate Charcoal body text
          750: '#334155',
          50: '#F8FAFC',  // Warm Alabaster surface
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
