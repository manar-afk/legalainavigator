/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        legalNavy: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          500: '#334e68',
          800: '#102a43',
          900: '#0b1d30',
        },
        legalGold: {
          500: '#b7791f',
          600: '#975a16',
        }
      },
    },
  },
  plugins: [],
};
