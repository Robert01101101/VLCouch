/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        couch: {
          black: '#141414',
          red: '#e50914',
          gray: '#2f2f2f',
        },
      },
    },
  },
  plugins: [],
}
