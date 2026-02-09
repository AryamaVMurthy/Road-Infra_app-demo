const path = require("path");

/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: path.join(__dirname, "frontend/tests"),
  timeout: 60000,
  workers: 1,
  webServer: [
    {
      command:
        "bash -lc 'source .venv/bin/activate && PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000'",
      url: "http://127.0.0.1:8000",
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: "npm --prefix frontend run dev -- --host 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011",
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
  use: {
    baseURL: "http://localhost:3011",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "frontend/playwright-report" }],
  ],
};
