/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class', // or 'media' or 'class'
  content: [
    '../src/**/*.html',
    '../src/**/*.py',
  ],
  theme: {
    extend: {},
    screens: {
      'xs': '320px',
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

