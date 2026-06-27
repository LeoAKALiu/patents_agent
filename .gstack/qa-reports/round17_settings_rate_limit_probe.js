const fs = require("fs");
const http = require("http");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const providerPort = 8767;
const providerUrl = `http://127.0.0.1:${providerPort}/v1`;
const fakeKey = "qa-rate-limit-key-do-not-use";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round17");
const statePath = path.resolve(".gstack/qa-reports/round17-settings-rate-limit-state.json");

fs.mkdirSync(outDir, { recursive: true });

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function visibleInputs(page) {
  return page.evaluate(() => {
    function isVisible(el) {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    }
    return Array.from(document.querySelectorAll("input, textarea, select"))
      .filter(isVisible)
      .map((el, index) => ({
        index,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute("type"),
        value: el.value,
        placeholder: el.getAttribute("placeholder") || "",
        label:
          el.closest("label")?.innerText?.trim() ||
          document.querySelector(`label[for="${el.id}"]`)?.innerText?.trim() ||
          "",
      }));
  });
}

async function domState(page, label) {
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
      bodyTextSample: document.body.innerText.slice(0, 2200),
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button]"))
        .filter(isVisible)
        .map((el) => ({
          text: (el.innerText || el.getAttribute("aria-label") || "").trim(),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        })),
      visibleInputs: Array.from(document.querySelectorAll("input, textarea, select"))
        .filter(isVisible)
        .map((el) => ({
          type: el.getAttribute("type"),
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

async function fillSettingsInputs(page) {
  const inputs = page.locator("input:visible");
  const count = await inputs.count();
  if (count < 4) {
    throw new Error(`Expected at least four visible settings inputs, found ${count}`);
  }

  await inputs.nth(0).fill("qa-rate-limit");
  await inputs.nth(1).fill(providerUrl);
  await inputs.nth(2).fill("qa-rate-limit-model");
  await inputs.nth(3).fill(fakeKey);
}

function createRateLimitProvider(events) {
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      events.providerRequests.push({
        method: req.method,
        url: req.url,
        headers: {
          authorization: req.headers.authorization ? "[REDACTED]" : undefined,
          contentType: req.headers["content-type"],
        },
        bodyLength: Buffer.concat(chunks).length,
      });
      res.writeHead(429, {
        "content-type": "application/json",
        "retry-after": "30",
      });
      res.end(
        JSON.stringify({
          error: {
            message: "QA mock rate limit exceeded",
            type: "rate_limit_error",
            code: "rate_limit_exceeded",
          },
        })
      );
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(providerPort, "127.0.0.1", () => resolve(server));
  });
}

(async () => {
  const events = { console: [], pageErrors: [], requestFailures: [], appRequests: [], providerRequests: [] };
  const providerServer = await createRateLimitProvider(events);
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
    page.on("response", async (response) => {
      const url = response.url();
      if (url.includes("/api/desktop-config")) {
        events.appRequests.push({ url, status: response.status(), method: response.request().method() });
      }
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "设置" }).first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: screenshotPath("settings-initial"), fullPage: true });
    const initial = await domState(page, "initial");

    await fillSettingsInputs(page);
    await page.screenshot({ path: screenshotPath("settings-filled-fake-rate-limit"), fullPage: true });
    const filled = await domState(page, "filled");

    await page.getByRole("button", { name: "保存" }).click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath("settings-after-save-rate-limit"), fullPage: true });
    const afterSave = await domState(page, "after-save");

    await page.getByRole("button", { name: "测试连通" }).click();
    await page
      .waitForFunction(
        () => {
          const body = document.body.innerText || "";
          const buttons = Array.from(document.querySelectorAll("button"));
          const testButton = buttons.find((button) => (button.innerText || "").trim() === "测试连通");
          return (
            (testButton && !testButton.disabled) ||
            /RateLimit|rate limit|rate_limit|429|限流|频率|稍后|重试|连接|失败|成功|Error/i.test(body)
          );
        },
        null,
        { timeout: 75000 }
      )
      .catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: screenshotPath("settings-after-rate-limit-test"), fullPage: true });
    const afterTest = await domState(page, "after-test");

    const clearButton = page.getByRole("button", { name: "清除密钥" });
    if (await clearButton.isVisible().catch(() => false) && await clearButton.isEnabled().catch(() => false)) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }
    await page.screenshot({ path: screenshotPath("settings-after-clear-rate-limit"), fullPage: true });
    const afterClear = await domState(page, "after-clear");

    const leakedFakeKey = [initial, filled, afterSave, afterTest, afterClear]
      .filter((state) => state.label !== "filled")
      .some((state) => state.bodyText.includes(fakeKey));

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      providerUrl,
      events,
      screenshots: {
        initial: screenshotPath("settings-initial"),
        filled: screenshotPath("settings-filled-fake-rate-limit"),
        afterSave: screenshotPath("settings-after-save-rate-limit"),
        afterTest: screenshotPath("settings-after-rate-limit-test"),
        afterClear: screenshotPath("settings-after-clear-rate-limit"),
      },
      states: { initial, filled, afterSave, afterTest, afterClear },
      assertions: {
        providerReceivedRequest: events.providerRequests.length > 0,
        afterTestShowsRateLimit: /rate limit|429|RateLimit|rate_limit|限流|频率|稍后|重试/i.test(afterTest.bodyText),
        afterTestShowsRawProviderJson: afterTest.bodyText.includes("QA mock rate limit exceeded") || afterTest.bodyText.includes("rate_limit_error"),
        afterTestShowsRawSdkError: /RateLimitError|InternalServerError|APIConnectionError|Error code: 429/i.test(afterTest.bodyText),
        fakeKeyLeakedOutsideInputState: leakedFakeKey,
        afterClearUnconfigured: afterClear.bodyText.includes("尚未配置 API Key") || afterClear.bodyText.includes("（未配置）"),
      },
    };

    fs.writeFileSync(statePath, JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);
  } finally {
    await browser.close().catch(() => {});
    await new Promise((resolve) => providerServer.close(resolve));
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
