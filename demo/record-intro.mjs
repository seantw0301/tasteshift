// Records the silent 30-second opening: node demo/record-intro.mjs  ->  artifacts/intro-raw.webm
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(here, "..", "artifacts");
const LENGTH = 30.5; // seconds of animation
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: path.join(OUT, "pw-intro"), size: { width: 1280, height: 720 } },
});
const page = await ctx.newPage();
const tLoad = Date.now();
await page.goto("file://" + path.join(here, "intro", "intro.html"));
await page.waitForFunction("window.__started === true");
const lead = (await page.evaluate("window.__t0") - tLoad) / 1000;
await page.waitForTimeout(LENGTH * 1000);
const video = page.video();
await ctx.close();
await video.saveAs(path.join(OUT, "intro-raw.webm"));
await browser.close();
fs.writeFileSync(path.join(OUT, "intro-lead.txt"), String(Math.max(lead, 0)));
console.log(`intro recorded, animation starts ${lead.toFixed(2)}s into the file`);
