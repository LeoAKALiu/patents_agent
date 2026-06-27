const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round18");
const fixtureDir = path.resolve(".gstack/qa-reports/fixtures");
const statePath = path.resolve(".gstack/qa-reports/round18-long-material-detail-state.json");
const fixturePath = path.join(fixtureDir, "round18-long-chinese-material.md");

fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(fixtureDir, { recursive: true });

const repeatedChinese =
  "本段用于验证专利交底材料详情区对超长中文技术文本的换行滚动和层级展示能力系统需要在材料摘要问题清单技术效果实施例和风险提示之间保持可读性不能让正文挤压按钮不能产生横向滚动也不能遮挡上传控件";
const longParagraphs = Array.from({ length: 36 }, (_, index) => {
  const prefix = `### 第 ${index + 1} 组技术论证\n`;
  return (
    prefix +
    `${repeatedChinese.repeat(6)}。\n\n` +
    `- 技术问题：${repeatedChinese.repeat(2)}。\n` +
    `- 技术方案：${repeatedChinese.repeat(3)}。\n` +
    `- 技术效果：${repeatedChinese.repeat(2)}。\n`
  );
}).join("\n\n");

fs.writeFileSync(
  fixturePath,
  `# Round18 长中文补充材料\n\n${longParagraphs}\n\n## 结论\n${repeatedChinese.repeat(8)}。\n`,
  "utf8"
);

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function domMetrics(page, label) {
  return page.evaluate((stateLabel) => {
    function isVisible(el) {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.bottom > 0 &&
        rect.right > 0 &&
        rect.top < window.innerHeight &&
        rect.left < window.innerWidth &&
        style.display !== "none" &&
        style.visibility !== "hidden"
      );
    }
    const offenders = Array.from(document.querySelectorAll("body *"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 140),
          className: String(el.className || "").slice(0, 140),
          left: rect.left,
          right: rect.right,
          width: rect.width,
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
          overflowX: getComputedStyle(el).overflowX,
        };
      })
      .filter((entry) => entry.right > window.innerWidth + 2 || entry.left < -2 || entry.scrollWidth > entry.clientWidth + 2)
      .slice(0, 40);

    return {
      label: stateLabel,
      url: location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      bodyScrollWidth: document.body.scrollWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      hasHorizontalOverflow:
        document.documentElement.scrollWidth > window.innerWidth + 2 || document.body.scrollWidth > window.innerWidth + 2,
      scrollY: window.scrollY,
      bodyTextLength: document.body.innerText.length,
      bodyTextSample: document.body.innerText.slice(0, 2400),
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button],summary"))
        .filter(isVisible)
        .map((el) => ({
          text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 160),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        })),
      offenders,
    };
  }, label);
}

async function firstVisibleByText(page, text) {
  const loc = page.getByText(text, { exact: true });
  const count = await loc.count();
  for (let i = 0; i < count; i += 1) {
    const item = loc.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  const fuzzy = page.getByText(text);
  const fuzzyCount = await fuzzy.count();
  for (let i = 0; i < fuzzyCount; i += 1) {
    const item = fuzzy.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function createProject(page, evidence) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);
  evidence.push({ step: "load-app", screenshot: screenshotPath("01-load-app"), metrics: await domMetrics(page, "load-app") });
  await page.screenshot({ path: screenshotPath("01-load-app"), fullPage: true });

  await page.getByText("从技术想法撰写发明专利").click();
  await page.waitForTimeout(600);
  await page.locator("input:visible").first().fill(`Round18 长中文材料 ${Date.now()}`);
  await page
    .locator("textarea:visible")
    .first()
    .fill("一种用于验证专利材料详情区长中文文本展示的测试项目，重点观察上传材料详情、移动端宽度、正文滚动和操作按钮可达性。");
  await page.screenshot({ path: screenshotPath("02-filled-project-form"), fullPage: true });
  evidence.push({ step: "filled-project-form", screenshot: screenshotPath("02-filled-project-form"), metrics: await domMetrics(page, "filled-project-form") });

  await page.getByRole("button", { name: /创建并继续/ }).click();
  await page.waitForFunction(() => document.body.innerText.includes("查看前置材料详情"), null, { timeout: 15000 });
  await page.screenshot({ path: screenshotPath("03-project-created"), fullPage: true });
  evidence.push({ step: "project-created", screenshot: screenshotPath("03-project-created"), metrics: await domMetrics(page, "project-created") });
}

async function uploadLongMaterial(page, evidence) {
  const fileInput = page.locator('input[type="file"]:visible').first();
  await fileInput.setInputFiles(fixturePath);
  await page.waitForTimeout(3500);
  await page.screenshot({ path: screenshotPath("04-after-upload"), fullPage: true });
  evidence.push({ step: "after-upload", screenshot: screenshotPath("04-after-upload"), metrics: await domMetrics(page, "after-upload") });

  const detailButton = await firstVisibleByText(page, "查看前置材料详情");
  if (!detailButton) throw new Error("Could not find 查看前置材料详情 after upload.");
  await detailButton.scrollIntoViewIfNeeded();
  await detailButton.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: screenshotPath("05-material-detail-desktop-top"), fullPage: true });
  evidence.push({
    step: "material-detail-desktop-top",
    screenshot: screenshotPath("05-material-detail-desktop-top"),
    metrics: await domMetrics(page, "material-detail-desktop-top"),
  });

  await page.mouse.wheel(0, 1800);
  await page.waitForTimeout(500);
  await page.screenshot({ path: screenshotPath("06-material-detail-desktop-scrolled"), fullPage: true });
  evidence.push({
    step: "material-detail-desktop-scrolled",
    screenshot: screenshotPath("06-material-detail-desktop-scrolled"),
    metrics: await domMetrics(page, "material-detail-desktop-scrolled"),
  });
}

async function mobileCheck(page, evidence) {
  await page.setViewportSize({ width: 390, height: 1100 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: screenshotPath("07-material-detail-mobile"), fullPage: true });
  evidence.push({ step: "material-detail-mobile", screenshot: screenshotPath("07-material-detail-mobile"), metrics: await domMetrics(page, "material-detail-mobile") });

  await page.mouse.wheel(0, 1800);
  await page.waitForTimeout(500);
  await page.screenshot({ path: screenshotPath("08-material-detail-mobile-scrolled"), fullPage: true });
  evidence.push({
    step: "material-detail-mobile-scrolled",
    screenshot: screenshotPath("08-material-detail-mobile-scrolled"),
    metrics: await domMetrics(page, "material-detail-mobile-scrolled"),
  });
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const events = { console: [], pageErrors: [], requestFailures: [], materialResponses: [] };
  page.on("console", (msg) => events.console.push({ type: msg.type(), text: msg.text() }));
  page.on("pageerror", (err) => events.pageErrors.push({ message: err.message, stack: err.stack }));
  page.on("requestfailed", (request) => events.requestFailures.push({ method: request.method(), url: request.url(), failure: request.failure() }));
  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("/materials")) {
      events.materialResponses.push({ url, status: response.status(), method: response.request().method() });
    }
  });

  const evidence = [];
  try {
    await createProject(page, evidence);
    await uploadLongMaterial(page, evidence);
    await mobileCheck(page, evidence);

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      fixturePath,
      fixtureBytes: fs.statSync(fixturePath).size,
      events,
      evidence,
      assertions: {
        uploadPosted: events.materialResponses.some((entry) => entry.method === "POST" && entry.status >= 200 && entry.status < 300),
        materialTextPresent: evidence.some((entry) => entry.metrics.bodyTextSample.includes("Round18 长中文补充材料")),
        desktopOverflow: evidence
          .filter((entry) => entry.step.includes("desktop"))
          .some((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.offenders.length > 0),
        mobileOverflow: evidence
          .filter((entry) => entry.step.includes("mobile"))
          .some((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.offenders.length > 0),
        pageErrors: events.pageErrors.length,
        requestFailures: events.requestFailures.length,
        consoleErrors: events.console.filter((entry) => entry.type === "error").length,
      },
    };
    fs.writeFileSync(statePath, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
