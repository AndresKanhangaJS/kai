import { defineConfig, devices } from '@playwright/test'

// E2E (testing.md): corre contra a stack Compose descartável `kai-e2e`
// (scripts/e2e.sh). A origem tem de ser http://localhost:5173: o RP ID e as
// origens permitidas das passkeys dependem dela (apps/api/config/passkeys.php).
export default defineConfig({
  testDir: './e2e',
  // Os traces de falhas guardam os valores escritos nos formulários (códigos
  // TOTP/recuperação, sintéticos): no contentor E2E ficam em /tmp, removido no fim.
  outputDir: process.env.E2E_OUTPUT_DIR ?? 'test-results',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
