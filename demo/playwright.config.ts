import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "demo-recording.spec.ts",
  timeout: 420_000,
  workers: 1,
  reporter: "list",
  outputDir: "../artifacts/pw",
  use: { baseURL: process.env.BASE_URL ?? "https://demo.jxdtw.com/tasteshift/" },
});
