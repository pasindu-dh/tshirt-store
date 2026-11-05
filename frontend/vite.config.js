import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(() => {
  if (process.env.VERCEL && !process.env.VITE_API_URL) {
    throw new Error(
      'VITE_API_URL must be set in the Vercel project environment before building.'
    )
  }

  return {
    plugins: [
      tailwindcss(),
      react()
    ],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.js',
      include: ['src/**/*.test.{js,jsx}'],
    },
  }
})
