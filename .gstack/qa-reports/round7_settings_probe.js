const fs = require("fs");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(`${process.cwd()}/frontend/package.json`);
const { chromium } = requireFromFrontend("playwright");

function apiPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

async function visibleText(page) {
  return page.locator("body").innerText();
}

(async () => {
  const consoleErrors = [];
  const pageErrors = [];
  const responses = [];
  const requestsFailed = [];

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", async (response) => {
    const url = response.url();
    if (url.includes("/api/") || url.includes("127.0.0.1:8766")) {
      let body = "";
      if (response.status() >= 400) {
        try {
          body = (await response.text()).slice(0, 600);
        } catch {
          body = "";
        }
      }
      responses.push({
        url: apiPath(url),
        status: response.status(),
        method: response.request().method(),
        body,
      });
    }
  });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/") || request.url().includes("127.0.0.1:8766")) {
      requestsFailed.push({
        url: apiPath(request.url()),
        method: request.method(),
        failure: request.failure()?.errorText ?? "",
      });
    }
  });

  await page.goto("http://127.0.0.1:5174/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  await page.getByText("设置", { exact: true }).first().click();
  await page.waitForTimeout(1000);
  const initialText = await visibleText(page);
  await page.screenshot({ path: ".gstack/qa-reports/screenshots/round7-settings-initial-confirmed.png", fullPage: true });

  await page.getByLabel("Provider").fill("qa-mock");
  await page.getByLabel("Base URL").fill("http://127.0.0.1:8766/v1");
  await page.getByLabel("Model").fill("qa-503-model");
  await page.getByLabel(/API Key/).fill("qa-round7-key-not-real");
  await page.screenshot({ path: ".gstack/qa-reports/screenshots/round7-settings-before-save.png", fullPage: true });

  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForTimeout(1200);
  const afterSaveText = await visibleText(page);
  await page.screenshot({ path: ".gstack/qa-reports/screenshots/round7-settings-after-save.png", fullPage: true });

  await page.getByRole("button", { name: "测试连通" }).click();
  await page.waitForTimeout(3000);
  const afterTestText = await visibleText(page);
  await page.screenshot({ path: ".gstack/qa-reports/screenshots/round7-settings-after-provider-503.png", fullPage: true });

  await page.getByRole("button", { name: "清除密钥" }).click();
  await page.waitForTimeout(1200);
  const afterClearText = await visibleText(page);
  await page.screenshot({ path: ".gstack/qa-reports/screenshots/round7-settings-after-clear-key.png", fullPage: true });

  const controls = await page.evaluate(() =>
    Array.from(document.querySelectorAll("input,textarea,select,button")).map((el, i) => ({
      i,
      tag: el.tagName,
      type: el.getAttribute("type"),
      text: (el.innerText || el.value || el.getAttribute("placeholder") || el.getAttribute("aria-label") || "").slice(0, 180),
      placeholder: el.getAttribute("placeholder"),
      disabled: el.disabled,
      labels: el.labels ? Array.from(el.labels).map((label) => label.innerText) : [],
    })),
  );

  await browser.close();

  fs.writeFileSync(
    ".gstack/qa-reports/round7-settings-state.json",
    JSON.stringify(
      {
        consoleErrors,
        pageErrors,
        responses,
        requestsFailed,
        initialText,
        afterSaveText,
        afterTestText,
        afterClearText,
        controls,
      },
      null,
      2,
    ),
  );
})().catch((error) => {
  fs.writeFileSync(
    ".gstack/qa-reports/round7-settings-state.json",
    JSON.stringify({ fatal: error.message, stack: error.stack }, null, 2),
  );
  process.exit(1);
});
