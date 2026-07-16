/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        couch: {
          black: '#141414',
          red: '#DC6602',
          'red-dark': '#BA5402',
          'red-light': '#E87A22',
          gray: '#2f2f2f',
        },
      },
    },
  },
  plugins: [],
}
