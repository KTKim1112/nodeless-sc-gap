import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const here = path.dirname(fileURLToPath(import.meta.url))
const backend = path.resolve(here, '..', 'backend')
// Absolute, and quoted, because the repository path contains spaces and the
// command is handed to a shell.
const python = `"${path.join(backend, '.venv', 'Scripts', 'python.exe')}"`

/**
 * End-to-end tests.
 *
 * These are the acceptance walkthrough of specs/001-jc-to-gap/quickstart.md,
 * executed rather than performed by hand. A scenario that is only ever checked
 * manually is a scenario that stops being checked.
 *
 * Both servers are started here, so `npm run test:e2e` is the whole command.
 */
export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/.artifacts',
  fullyParallel: false,          // one backend, one job store: keep it serial
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'ko-KR',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } },
    },
  ],

  webServer: [
    {
      // The interpreter is taken straight from the virtual environment, so the
      // run does not depend on which shell activated what.
      command: `${python} -m uvicorn app.main:app --port 8000 --log-level warning`,
      cwd: backend,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: true,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
