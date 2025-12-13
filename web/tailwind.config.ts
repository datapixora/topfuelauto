import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/app/**/*.{js,ts,jsx,tsx}',
    './src/components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0f172a',
          accent: '#0ea5e9',
          gold: '#fbbf24',
        },
      },
    },
  },
  plugins: [],
}
export default config