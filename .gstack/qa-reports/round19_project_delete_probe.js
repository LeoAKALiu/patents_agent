const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round19");
fs.mkdirSync(screenshotDir, { recursive: true });

const now = Date.now();
const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    dialogs: [],
    projectResponses: [],
  },
  evidence: [],
  assertions: {},
};

function shotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function collectMetrics(page, label) {
  return page.evaluate((metricLabel) => {
    const body = document.body;
    const doc = document.documentElement;
    const buttons = Array.from(document.querySelectorAll("button")).map((button) => ({
      text: (button.innerText || button.textContent || "").trim().replace(/\s+/g, " ").slice(0, 140),
      disabled: button.disabled,
      ariaDisabled: button.getAttribute("aria-disabled"),
    }));
    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: innerWidth, height: innerHeight },
      bodyScrollWidth: body ? body.scrollWidth : 0,
      documentScrollWidth: doc ? doc.scrollWidth : 0,
      innerWidth,
      hasHorizontalOverflow: Math.max(body ? body.scrollWidth : 0, doc ? doc.scrollWidth : 0) > innerWidth + 1,
      bodyTextLength: body ? body.innerText.length : 0,
      bodyTextSample: body ? body.innerText.slice(0, 5000) : "",
      visibleButtons: buttons,
    };
  }, label);
}

async function evidence(page, step, options = {}) {
  const file = shotPath(step);
  await page.screenshot({ path: file, fullPage: options.fullPage !== false });
  const metrics = await collectMetrics(page, step);
  state.evidence.push({ step, screenshot: file, metrics });
  return metrics;
}

async function waitForIdle(page) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForTimeout(350);
}

async function clickText(page, text) {
  const locator = page.getByText(text, { exact: true }).first();
  await locator.waitFor({ state: "visible", timeout: 10000 });
  await locator.click();
}

async function createProject(page, name, idea) {
  await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).click();
  await waitForIdle(page);
  await page.getByLabel("项目名称").fill(name);
  await page.getByLabel("一句话想法").fill(idea);
  await evidence(page, `project-form-${name.includes("保留") ? "keep" : "delete"}`);
  await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api/projects") && response.request().method() === "POST", { timeout: 15000 }),
    page.getByRole("button", { name: "创建并继续" }).click(),
  ]);
  await page.waitForTimeout(900);
  await evidence(page, `project-created-${name.includes("保留") ? "keep" : "delete"}`);
}

function projectDeleteButton(page, projectName) {
  const projectContainer = page
    .locator("article, li, section, div")
    .filter({ hasText: projectName })
    .filter({ has: page.getByRole("button", { name: /删除/ }) })
    .last();
  return projectContainer.getByRole("button", { name: /删除/ }).first();
}

async function clickAndHandleDialog(page, locator, action) {
  const dialogPromise = new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), 5000);
    page.once("dialog", async (dialog) => {
      clearTimeout(timer);
      const info = {
        type: dialog.type(),
        message: dialog.message(),
        action,
      };
      state.events.dialogs.push(info);
      if (action === "accept") {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
      resolve(info);
    });
  });
  await locator.evaluate((element) => element.click());
  return dialogPromise;
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });

  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  page.on("console", (message) => {
    state.events.console.push({ type: message.type(), text: message.text().slice(0, 1000) });
  });
  page.on("pageerror", (error) => {
    state.events.pageErrors.push({ message: error.message, stack: error.stack });
  });
  page.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      url: request.url(),
      method: request.method(),
      failure: request.failure() && request.failure().errorText,
    });
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/projects")) {
      state.events.projectResponses.push({
        url,
        status: response.status(),
        method: response.request().method(),
      });
    }
  });
  const keepName = `Round19 保留项目 ${now}`;
  const deleteName = `Round19 待删除当前项目 ${now}`;
  const idea = "一种用于测试项目删除状态一致性的专利撰写辅助方案，包含项目选择、删除确认、取消恢复和列表刷新。";

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await waitForIdle(page);
  await evidence(page, "01-load-app");

  await createProject(page, keepName, idea);
  await page.getByRole("button", { name: "返回三选一" }).click();
  await waitForIdle(page);
  await createProject(page, deleteName, idea);

  await clickText(page, "项目");
  await waitForIdle(page);
  await evidence(page, "02-project-list-before-delete");

  const before = await page.evaluate(async () => {
    const res = await fetch("/api/projects");
    return res.json();
  });
  state.apiBeforeDelete = before;

  await page.getByText(deleteName, { exact: false }).first().waitFor({ state: "visible", timeout: 10000 });

  const targetedDeleteButton = projectDeleteButton(page, deleteName);
  const deleteButtonCount = await page.getByRole("button", { name: /删除/ }).count();
  state.assertions.deleteButtonCount = deleteButtonCount;
  if (deleteButtonCount < 1) {
    throw new Error("No visible delete button found on project list");
  }

  const cancelDialog = await clickAndHandleDialog(page, targetedDeleteButton, "dismiss");
  await waitForIdle(page);
  await evidence(page, "03-after-first-delete-click");

  state.assertions.cancelDialogShown = Boolean(cancelDialog);
  await evidence(page, "04-after-cancel-delete");

  const afterCancel = await page.evaluate(async () => {
    const res = await fetch("/api/projects");
    return res.json();
  });
  state.apiAfterCancel = afterCancel;

  await evidence(page, "05-before-confirm-delete");
  const deleteResponsePromise = page
    .waitForResponse((response) => response.url().includes("/api/projects/") && response.request().method() === "DELETE", { timeout: 10000 })
    .catch(() => null);
  const confirmDialog = await clickAndHandleDialog(page, projectDeleteButton(page, deleteName), "accept");
  const deleteResponse = await deleteResponsePromise;
  state.assertions.confirmDialogShown = Boolean(confirmDialog);
  state.assertions.deleteResponseStatus = deleteResponse ? deleteResponse.status() : null;
  await page.waitForTimeout(5000);
  await evidence(page, "06-after-confirm-delete");

  const afterConfirm = await page.evaluate(async () => {
    const res = await fetch("/api/projects");
    return res.json();
  });
  state.apiAfterConfirm = afterConfirm;

  const finalText = await page.locator("body").innerText();
  state.assertions.keepPresentAfterConfirm = finalText.includes(keepName);
  state.assertions.deletedAbsentAfterConfirm = !finalText.includes(deleteName);
  state.assertions.cancelPreservedBoth = JSON.stringify(afterCancel).includes(keepName) && JSON.stringify(afterCancel).includes(deleteName);
  state.assertions.apiDeletedAbsentAfterConfirm = !JSON.stringify(afterConfirm).includes(deleteName);
  state.assertions.apiKeepPresentAfterConfirm = JSON.stringify(afterConfirm).includes(keepName);
  state.assertions.pageErrors = state.events.pageErrors.length;
  state.assertions.requestFailures = state.events.requestFailures.length;
  state.assertions.consoleErrors = state.events.console.filter((entry) => entry.type === "error").length;

  await browser.close();
  fs.writeFileSync(path.join(outDir, "round19-project-delete-state.json"), JSON.stringify(state, null, 2));
  console.log(JSON.stringify(state.assertions, null, 2));
}

main().catch((error) => {
  state.fatal = { message: error.message, stack: error.stack };
  fs.writeFileSync(path.join(outDir, "round19-project-delete-state.json"), JSON.stringify(state, null, 2));
  console.error(error);
  process.exit(1);
});
