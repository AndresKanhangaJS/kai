import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Vitest (M02 E2.2): testes de unidade/componentes em src/, sem rede (testing.md).
  // Os E2E (e2e/) são do Playwright e ficam de fora.
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
