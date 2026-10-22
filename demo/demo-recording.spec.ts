// Records the product demo on the live site with captions; writes artifacts/audio/timeline.json for voice mixing.
// The agent wait (about a minute of real LLM + Qloo calls) is marked with __cut_start/__cut_end and removed in post.
import { test, expect, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const narration: Record<string, { text: string; hold: number }> = JSON.parse(
  fs.readFileSync(path.join(here, "narration.json"), "utf8"),
);
const OUT = path.join(here, "..", "artifacts");
const AUDIO = path.join(OUT, "audio");
const durations: Record<string, number> = fs.existsSync(path.join(AUDIO, "durations.json"))
  ? JSON.parse(fs.readFileSync(path.join(AUDIO, "durations.json"), "utf8"))
  : {};
const timeline: { key: string; t: number }[] = [];
let t0 = Date.now();
const mark = (key: string) => timeline.push({ key, t: (Date.now() - t0) / 1000 });

async function caption(page: Page, text: string) {
  await page.evaluate((t) => {
    let el = document.getElementById("ts-caption");
    if (!el) {
      el = document.createElement("div");
      el.id = "ts-caption";
      el.style.cssText =
        "position:fixed;left:0;right:0;bottom:0;padding:14px 32px;background:rgba(28,25,23,.92);color:#fff;font:600 20px system-ui;text-align:center;z-index:9999";
      document.body.appendChild(el);
    }
    el.textContent = t;
    document.body.style.paddingBottom = "120px";
  }, text);
}

async function say(page: Page, key: string) {
  const { text } = narration[key];
  // hold at least as long as the spoken line (+0.6 s) so audio never overlaps the next beat
  const hold = Math.max(narration[key].hold, Math.round((durations[key] ?? 0) * 1000) + 600);
  mark(key);
  await caption(page, text);
  await page.waitForTimeout(hold);
}

async function scrollTo(page: Page, text: string | RegExp) {
  await page.getByText(text).first().evaluate((e) => e.scrollIntoView({ behavior: "smooth", block: "center" }));
  await page.waitForTimeout(900);
}

test("TasteShift demo", async ({ browser, baseURL }) => {
  fs.mkdirSync(AUDIO, { recursive: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: path.join(OUT, "pw-video"), size: { width: 1280, height: 720 } },
  });
  const page = await ctx.newPage();
  t0 = Date.now();

  await page.goto(baseURL!);
  await expect(page.getByText("Anime Music Festival").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/QLOO EVIDENCE/i).first()).toBeVisible({ timeout: 30_000 });
  await say(page, "culture");
  await scrollTo(page, /QLOO EVIDENCE/i);
  await say(page, "evidence");
  await scrollTo(page, /QLOO ON VS OFF/i);
  await say(page, "onoff");

  await page.getByRole("button", { name: "Decision audit" }).first().click();
  await page.waitForTimeout(800);
  await say(page, "audit");
  await page.getByRole("button", { name: "Close" }).click();

  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await page.getByRole("button", { name: "Plans & what-if" }).click();
  await page.waitForTimeout(1500);
  await page.getByText("Afternoon rain").click();
  await page.waitForTimeout(1200);
  await say(page, "plans");

  await page.getByRole("button", { name: "Live ops (simulated)" }).click();
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: "Simulate sales" }).click();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Recommend restock" }).click();
  await page.waitForTimeout(1200);
  await say(page, "ops");

  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.getByRole("button", { name: "Agent (Qloo vs none)" }).click();
  await page.waitForTimeout(800);
  await say(page, "agent");

  await page.getByRole("button", { name: "Run both arms" }).click();
  await say(page, "run");
  mark("__cut_start");
  await expect(page.getByText(/Profit with Qloo/)).toBeVisible({ timeout: 300_000 });
  await caption(page, "≈ 1 minute later — real Qloo and LLM calls");
  await page.waitForTimeout(300);
  mark("__cut_end");
  await page.waitForTimeout(1500);

  await say(page, "tools");
  await scrollTo(page, /SKUs backed by a Qloo citation/);
  await say(page, "citations");
  await scrollTo(page, /WITHOUT QLOO/i);
  await say(page, "without");
  await scrollTo(page, /Profit with Qloo/);
  await say(page, "result");
  await say(page, "close");

  const video = page.video()!;
  await ctx.close();
  await video.saveAs(path.join(OUT, "tasteshift-demo.webm"));
  fs.writeFileSync(path.join(AUDIO, "timeline.json"), JSON.stringify(timeline, null, 1));
});
