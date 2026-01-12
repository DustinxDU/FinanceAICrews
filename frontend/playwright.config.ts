import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.PLAYWRIGHT_PORT || 3000);
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${port}`;
const publicApiUrl = process.env.PLAYWRIGHT_PUBLIC_API_URL;
const publicWsUrl = process.env.PLAYWRIGHT_PUBLIC_WS_URL;
const reuseExistingServer =
  (process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER || "").toLowerCase() !== "false" &&
  !process.env.CI;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: publicApiUrl
      ? `NEXT_PUBLIC_API_URL=${publicApiUrl} ${publicWsUrl ? `NEXT_PUBLIC_WS_URL=${publicWsUrl} ` : ""}npm run dev -- -p ${port}`
      : `npm run dev -- -p ${port}`,
    url: baseURL,
    reuseExistingServer,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
