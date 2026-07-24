const { defineConfig } = require('@playwright/test')
const path = require('path')

const root = path.resolve(__dirname, '..')
const e2eDb = path.join(root, 'backend', 'tests', '.tmp', 'e2e-library.db')
const python = path.join(root, 'backend', '.venv', 'Scripts', 'python.exe')
const backendPort = 8001
const frontendPort = 5174

const startBackend = [
  `Remove-Item -Path '${e2eDb}' -Force -ErrorAction SilentlyContinue`,
  `& '${python}' -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --app-dir backend`,
].join('; ')

module.exports = defineConfig({
  testDir: './specs',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: `powershell -NoProfile -Command "${startBackend}"`,
      cwd: root,
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        ...process.env,
        APP_ENV: 'test',
        TEST_MODE: 'true',
        SCAN_ON_STARTUP: 'true',
        TEST_DB_PATH: e2eDb,
      },
    },
    {
      command: `npm run dev -- --port ${frontendPort}`,
      cwd: path.join(root, 'frontend'),
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 120000,
      env: {
        ...process.env,
        VITE_PORT: String(frontendPort),
        VITE_API_PROXY: `http://127.0.0.1:${backendPort}`,
      },
    },
  ],
})
