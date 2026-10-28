import { defineConfig, devices } from '@playwright/test'

// Browser tests; run with bin/e2e, which builds the frontend and prepares the agweather2_e2e database
const port = 8200

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://localhost:${port}`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'phone', use: { ...devices['Pixel 7'], colorScheme: 'dark' } },
  ],
  webServer: {
    command: `uv run uvicorn --app-dir app config.asgi:application --lifespan off --port ${port}`,
    url: `http://localhost:${port}/up`,
    env: {
      DJANGO_ENV: 'test',
      VITE_DEV_MODE: '0',
      DATABASE_URL: process.env.E2E_DATABASE_URL!,
      DATA_DIR: `${process.cwd()}/tmp/e2e-data`, // an empty archive, so health doesn't depend on local data
    },
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
