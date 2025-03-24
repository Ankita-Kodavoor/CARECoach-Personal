// tailwind.config.js
module.exports = {
    content: [
      "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          amber: {
            200: '#f8ff9b',
            400: '#f2a03b',
          },
        },
        keyframes: {
          fadeIn: {
            '0%': { opacity: 0, transform: 'translateY(10px)' },
            '100%': { opacity: 1, transform: 'translateY(0)' }
          },
          bounce: {
            '0%, 100%': { transform: 'translateY(0)' },
            '50%': { transform: 'translateY(-8px)' },
          }
        },
        animation: {
          fadeIn: 'fadeIn 0.3s ease-out',
          bounce: 'bounce 1.5s infinite ease-in-out'
        }
      }
    },
    plugins: [],
  }

