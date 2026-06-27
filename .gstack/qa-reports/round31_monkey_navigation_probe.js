const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round31");
const statePath = path.join(outDir, "round31-monkey-navigation-state.json");
fs.mkdirSync(screenshotDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  projectName: `Round31 用户猴子导航 ${Date.now()}`,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    responses: [],
  },
  evidence: [],
  actions: [],
  assertions: {},
};

function shotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function collectMetrics(page, label) {
  return page.evaluate((metricLabel) => {
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
        style.visibility !== "hidden" &&
        style.opacity !== "0"
      );
    }

    const controls = Array.from(document.querySelectorAll("button,[role=button],a,select,input,textarea,summary"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "").trim().replace(/\s+/g, " ").slice(0, 160),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
          left: Math.round(rect.left),
          top: Math.round(rect.top),
          right: Math.round(rect.right),
          bottom: Math.round(rect.bottom),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      });

    const overflowers = Array.from(document.querySelectorAll("body *"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 140),
          className: String(el.className || "").slice(0, 140),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          scrollWidth: el.scrollWidth,
          clientWidth: el.clientWidth,
        };
      })
      .filter((entry) => entry.right > window.innerWidth + 2 || entry.left < -2 || entry.scrollWidth > entry.clientWidth + 2)
      .slice(0, 30);

    const bodyText = document.body.innerText || "";
    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: innerWidth, height: innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      hasHorizontalOverflow:
        document.documentElement.scrollWidth > innerWidth + 2 || document.body.scrollWidth > innerWidth + 2,
      bodyTextLength: bodyText.length,
      bodyTextSample: bodyText.slice(0, 4000),
      controls,
      controlsBelow44px: controls
        .filter((control) => ["button", "a", "select", "input", "textarea"].includes(control.tag) && control.height > 0 && control.height < 44)
        .slice(0, 40),
      overflowers,
    };
  }, label);
}

async function evidence(page, step) {
  const screenshot = shotPath(step);
  await page.screenshot({ path: screenshot, fullPage: true });
  const metrics = await collectMetrics(page, step);
  state.evidence.push({ step, screenshot, metrics });
  return metrics;
}

async function action(label, fn) {
  try {
    await fn();
    state.actions.push({ label, ok: true });
  } catch (error) {
    state.actions.push({ label, ok: false, message: error.message });
  }
}

async function waitForIdle(page) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForTimeout(700);
}

async function clickFirst(page, matcher, label = String(matcher)) {
  const locator = typeof matcher === "string" ? page.getByText(matcher) : page.getByRole("button", { name: matcher });
  const count = await locator.count();
  for (let i = 0; i < count; i += 1) {
    const item = locator.nth(i);
    if (await item.isVisible().catch(() => false)) {
      await item.scrollIntoViewIfNeeded();
      await item.click({ timeout: 5000 });
      await page.waitForTimeout(650);
      return true;
    }
  }
  throw new Error(`No visible target for ${label}`);
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  page.on("console", (message) => {
    state.events.console.push({ type: message.type(), text: message.text().slice(0, 1200) });
  });
  page.on("pageerror", (error) => {
    state.events.pageErrors.push({ message: error.message, stack: error.stack });
  });
  page.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure() && request.failure().errorText,
    });
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/")) {
      state.events.responses.push({ method: response.request().method(), url, status: response.status() });
    }
  });

  try {
    await action("open app", async () => {
      await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
      await waitForIdle(page);
    });
    await evidence(page, "01-home-desktop");

    await action("open projects empty state", async () => {
      await page.getByRole("button", { name: "项目" }).first().click();
      await waitForIdle(page);
    });
    await evidence(page, "02-projects-empty-desktop");

    await action("open settings page", async () => {
      await page.getByRole("button", { name: "设置" }).first().click();
      await waitForIdle(page);
    });
    await evidence(page, "03-settings-desktop");

    await action("rapid refresh status on settings", async () => {
      for (let i = 0; i < 3; i += 1) {
        await page.getByRole("button", { name: /刷新运行状态/ }).first().click();
        await page.waitForTimeout(250);
      }
      await page.waitForTimeout(1000);
    });
    await evidence(page, "04-after-rapid-refresh-status");

    await action("return start and choose invention", async () => {
      await page.getByRole("button", { name: "开始" }).first().click();
      await waitForIdle(page);
      await clickFirst(page, /从技术想法撰写发明专利/, "invention entry");
    });
    await evidence(page, "05-create-form-empty");

    await action("fill and create project", async () => {
      await page.getByRole("textbox", { name: "项目名称", exact: true }).fill(state.projectName);
      await page
        .getByRole("textbox", { name: "一句话想法", exact: true })
        .fill("一种用于模拟新手用户随机点击导航、设置、项目和专家工具入口时，系统仍能保持状态清晰且无横向溢出的测试项目。");
      await Promise.all([
        page.waitForResponse((response) => response.url().includes("/api/projects") && response.request().method() === "POST", { timeout: 15000 }),
        page.getByRole("button", { name: /创建并继续/ }).click(),
      ]);
      await page.waitForTimeout(1400);
    });
    await evidence(page, "06-after-project-create");

    await action("open expert tools", async () => {
      await clickFirst(page, "专家工具", "expert tools");
      await page.waitForTimeout(900);
    });
    await evidence(page, "07-expert-tools-open");

    await action("open material detail and return", async () => {
      const opened = await clickFirst(page, "查看前置材料详情", "material detail").catch(() => false);
      if (opened) {
        await page.waitForTimeout(700);
      }
    });
    await evidence(page, "08-material-detail-empty");

    await action("mobile viewport current workflow", async () => {
      await page.setViewportSize({ width: 390, height: 1100 });
      await page.waitForTimeout(900);
    });
    await evidence(page, "09-mobile-current-workflow");

    await action("mobile settings then projects then start", async () => {
      await page.getByRole("button", { name: "设置" }).first().click();
      await page.waitForTimeout(700);
      await evidence(page, "10-mobile-settings");
      await page.getByRole("button", { name: "项目" }).first().click();
      await page.waitForTimeout(700);
      await evidence(page, "11-mobile-projects");
      await page.getByRole("button", { name: "开始" }).first().click();
      await page.waitForTimeout(700);
    });
    await evidence(page, "12-mobile-start-after-navigation");

    const desktopEvidence = state.evidence.filter((entry) => entry.metrics.viewport.width >= 1000);
    const mobileEvidence = state.evidence.filter((entry) => entry.metrics.viewport.width < 600);
    const visibleErrorText = state.evidence
      .map((entry) => entry.metrics.bodyTextSample)
      .filter((text) => /请求失败|Failed|Error|错误|异常/.test(text));

    state.assertions = {
      actionFailures: state.actions.filter((entry) => !entry.ok).length,
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      desktopHorizontalOverflow: desktopEvidence.some((entry) => entry.metrics.hasHorizontalOverflow),
      mobileHorizontalOverflow: mobileEvidence.some((entry) => entry.metrics.hasHorizontalOverflow),
      mobileControlsBelow44Count: mobileEvidence.reduce((sum, entry) => sum + entry.metrics.controlsBelow44px.length, 0),
      visibleErrorTextCount: visibleErrorText.length,
      projectNameVisibleAfterCreate: state.evidence.some((entry) => entry.metrics.bodyTextSample.includes(state.projectName)),
      settingsReached: state.evidence.some((entry) => entry.step.includes("settings") && /API Key|Provider|Base URL|模型/.test(entry.metrics.bodyTextSample)),
      projectsReached: state.evidence.some((entry) => entry.step.includes("projects") && /项目/.test(entry.metrics.bodyTextSample)),
      expertToolsReached: state.evidence.some((entry) => entry.step.includes("expert-tools") && /专家工具|前置材料|护城河/.test(entry.metrics.bodyTextSample)),
      noNewBugCandidate:
        state.actions.filter((entry) => !entry.ok).length === 0 &&
        state.events.pageErrors.length === 0 &&
        state.events.requestFailures.length === 0 &&
        state.events.console.filter((entry) => entry.type === "error").length === 0 &&
        !desktopEvidence.some((entry) => entry.metrics.hasHorizontalOverflow) &&
        !mobileEvidence.some((entry) => entry.metrics.hasHorizontalOverflow) &&
        visibleErrorText.length === 0,
    };

    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify(state.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);
  } finally {
    await browser.close().catch(() => {});
  }
}

main().catch((error) => {
  state.fatal = { message: error.message, stack: error.stack };
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
  console.error(error);
  process.exit(1);
});
