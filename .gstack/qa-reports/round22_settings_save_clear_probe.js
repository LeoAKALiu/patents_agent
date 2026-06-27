const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBaseUrl = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round22");
const statePath = path.resolve(".gstack/qa-reports/round22-settings-save-clear-state.json");
const fakeKey = `qa-settings-secret-round22-${Date.now()}`;
const settingsPayload = {
  provider: "qa-settings-save-clear",
  baseUrl: "http://127.0.0.1:65534/v1",
  model: "qa-settings-model",
  apiKey: fakeKey,
};

fs.mkdirSync(outDir, { recursive: true });

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function collectDomState(page, label) {
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

    return {
      label: stateLabel,
      url: location.href,
      bodyText: document.body.innerText,
      bodyTextSample: document.body.innerText.slice(0, 2600),
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button]"))
        .filter(isVisible)
        .map((el) => ({
          text: (el.innerText || el.getAttribute("aria-label") || "").trim(),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        })),
      visibleInputs: Array.from(document.querySelectorAll("input, textarea, select"))
        .filter(isVisible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          value: el.value,
          placeholder: el.getAttribute("placeholder") || "",
          label:
            el.closest("label")?.innerText?.trim() ||
            document.querySelector(`label[for="${el.id}"]`)?.innerText?.trim() ||
            "",
        })),
    };
  }, label);
}

async function fetchDesktopConfig(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/desktop-config");
    const text = await response.text();
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      json = null;
    }
    return { status: response.status, text, json };
  });
}

async function fillSettingsInputs(page) {
  const inputs = page.locator("input:visible");
  const count = await inputs.count();
  if (count < 4) {
    throw new Error(`Expected at least four visible settings inputs, found ${count}`);
  }
  await inputs.nth(0).fill(settingsPayload.provider);
  await inputs.nth(1).fill(settingsPayload.baseUrl);
  await inputs.nth(2).fill(settingsPayload.model);
  await inputs.nth(3).fill(settingsPayload.apiKey);
}

async function waitForButtonEnabled(page, name, timeout = 10000) {
  const button = page.getByRole("button", { name }).first();
  await page.waitForFunction(
    (buttonText) => {
      const target = Array.from(document.querySelectorAll("button")).find(
        (candidate) => (candidate.innerText || "").trim() === buttonText
      );
      return target && !target.disabled && target.getAttribute("aria-disabled") !== "true";
    },
    name,
    { timeout }
  );
  return button;
}

(async () => {
  const events = { console: [], pageErrors: [], requestFailures: [], appRequests: [] };
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("console", (msg) => events.console.push({ type: msg.type(), text: msg.text() }));
    page.on("pageerror", (err) => events.pageErrors.push({ message: err.message, stack: err.stack }));
    page.on("requestfailed", (request) => {
      events.requestFailures.push({ method: request.method(), url: request.url(), failure: request.failure() });
    });
    page.on("response", (response) => {
      const url = response.url();
      if (url.includes("/api/desktop-config")) {
        events.appRequests.push({ url, status: response.status(), method: response.request().method() });
      }
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "设置" }).first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: screenshotPath("01-settings-initial"), fullPage: true });
    const initial = await collectDomState(page, "initial");
    const initialConfig = await fetchDesktopConfig(page);

    await fillSettingsInputs(page);
    await page.screenshot({ path: screenshotPath("02-settings-filled"), fullPage: true });
    const filled = await collectDomState(page, "filled");

    await page.getByRole("button", { name: "保存" }).first().click();
    await page.waitForTimeout(1200);
    await waitForButtonEnabled(page, "保存").catch(() => {});
    await page.screenshot({ path: screenshotPath("03-settings-after-save"), fullPage: true });
    const afterSave = await collectDomState(page, "after-save");
    const afterSaveConfig = await fetchDesktopConfig(page);

    const clearButton = page.getByRole("button", { name: "清除密钥" }).first();
    const clearVisibleBefore = await clearButton.isVisible().catch(() => false);
    if (clearVisibleBefore) {
      await clearButton.click();
      await page.waitForTimeout(1200);
    }
    await page.screenshot({ path: screenshotPath("04-settings-after-clear"), fullPage: true });
    const afterClear = await collectDomState(page, "after-clear");
    const afterClearConfig = await fetchDesktopConfig(page);

    const visibleInputValuesAfterSave = afterSave.visibleInputs.map((input) => input.value).filter(Boolean);
    const visibleInputValuesAfterClear = afterClear.visibleInputs.map((input) => input.value).filter(Boolean);
    const afterSaveText = `${afterSave.bodyText}\n${afterSaveConfig.text}`;
    const afterClearText = `${afterClear.bodyText}\n${afterClearConfig.text}`;

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      apiBaseUrl,
      settingsPayload: { ...settingsPayload, apiKey: "[REDACTED]" },
      events,
      screenshots: {
        initial: screenshotPath("01-settings-initial"),
        filled: screenshotPath("02-settings-filled"),
        afterSave: screenshotPath("03-settings-after-save"),
        afterClear: screenshotPath("04-settings-after-clear"),
      },
      states: { initial, filled, afterSave, afterClear },
      configs: {
        initial: initialConfig,
        afterSave: afterSaveConfig,
        afterClear: afterClearConfig,
      },
      assertions: {
        saveRequestSucceeded: events.appRequests.some(
          (request) => request.method !== "GET" && request.status >= 200 && request.status < 300
        ),
        clearButtonVisibleBeforeClear: clearVisibleBefore,
        afterSaveShowsConfiguredKey:
          /已配置|密钥指纹|API Key.+配置|key.+configured/i.test(afterSave.bodyText) &&
          !/尚未配置 API Key|未配置 API Key/.test(afterSave.bodyText),
        afterSaveBodyLeaksKey: afterSave.bodyText.includes(fakeKey),
        afterSaveInputLeaksKey: visibleInputValuesAfterSave.includes(fakeKey),
        afterSaveApiLeaksKey: afterSaveConfig.text.includes(fakeKey),
        afterClearBodyLeaksKey: afterClear.bodyText.includes(fakeKey),
        afterClearInputLeaksKey: visibleInputValuesAfterClear.includes(fakeKey),
        afterClearApiLeaksKey: afterClearConfig.text.includes(fakeKey),
        afterClearUnconfigured:
          /尚未配置 API Key|未配置 API Key|API Key.+未配置/.test(afterClear.bodyText) ||
          afterClearConfig.text.includes('"api_key_configured":false'),
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
