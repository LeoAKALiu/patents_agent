const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round20");
fs.mkdirSync(screenshotDir, { recursive: true });

const now = Date.now();
const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    materialResponses: [],
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
      text: (button.innerText || button.textContent || "").trim().replace(/\s+/g, " ").slice(0, 160),
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

async function evidence(page, step) {
  const file = shotPath(step);
  await page.screenshot({ path: file, fullPage: true });
  const metrics = await collectMetrics(page, step);
  state.evidence.push({ step, screenshot: file, metrics });
  return metrics;
}

async function waitForIdle(page) {
  await page.waitForLoadState("domcontentloaded").catch(() => {});
  await page.waitForTimeout(500);
}

async function currentProjectId(page) {
  const projects = await page.evaluate(async () => {
    const response = await fetch("/api/projects");
    return response.json();
  });
  const project = projects.projects.find((entry) => entry.name === state.projectName);
  if (!project) {
    throw new Error(`Created project not found in /api/projects: ${state.projectName}`);
  }
  return project.id;
}

async function materialsFor(page, projectId) {
  return page.evaluate(async (id) => {
    const response = await fetch(`/api/projects/${id}/materials`);
    return response.json();
  }, projectId);
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
    if (url.includes("/api/projects/") && url.includes("/materials")) {
      state.events.materialResponses.push({
        url,
        status: response.status(),
        method: response.request().method(),
      });
    }
  });

  state.projectName = `Round20 上传取消项目 ${now}`;
  const idea = "一种用于验证补充材料文件选择取消时不会上传、不增加材料计数的专利撰写辅助流程。";

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await waitForIdle(page);
  await evidence(page, "01-load-app");

  await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).click();
  await waitForIdle(page);
  await page.getByLabel("项目名称").fill(state.projectName);
  await page.getByLabel("一句话想法").fill(idea);
  await evidence(page, "02-filled-project-form");

  await Promise.all([
    page.waitForResponse((response) => response.url().includes("/api/projects") && response.request().method() === "POST", { timeout: 15000 }),
    page.getByRole("button", { name: "创建并继续" }).click(),
  ]);
  await page.waitForTimeout(1200);
  await evidence(page, "03-project-created");

  const projectId = await currentProjectId(page);
  state.projectId = projectId;
  state.materialsBefore = await materialsFor(page, projectId);

  const materialPostCountBefore = state.events.materialResponses.filter((entry) => entry.method === "POST").length;
  const chooserPromise = page.waitForEvent("filechooser", { timeout: 10000 });
  await page.getByRole("button", { name: /选择并上传多份报告|上传材料|选择文件/ }).first().click();
  const chooser = await chooserPromise;
  await chooser.setFiles([]);
  await page.waitForTimeout(1200);
  await evidence(page, "04-after-filechooser-cancel");

  state.materialsAfterCancel = await materialsFor(page, projectId);
  const materialPostCountAfter = state.events.materialResponses.filter((entry) => entry.method === "POST").length;
  const bodyText = await page.locator("body").innerText();

  state.assertions.projectId = projectId;
  state.assertions.materialCountBefore = state.materialsBefore.materials.length;
  state.assertions.materialCountAfterCancel = state.materialsAfterCancel.materials.length;
  state.assertions.materialPostCountBefore = materialPostCountBefore;
  state.assertions.materialPostCountAfter = materialPostCountAfter;
  state.assertions.noMaterialPostAfterCancel = materialPostCountAfter === materialPostCountBefore;
  state.assertions.noMaterialCountIncrease = state.materialsAfterCancel.materials.length === state.materialsBefore.materials.length;
  state.assertions.noUploadedMaterialText = !bodyText.includes("已上传材料") && !bodyText.includes("当前已有 1 份材料");
  state.assertions.pageErrors = state.events.pageErrors.length;
  state.assertions.requestFailures = state.events.requestFailures.length;
  state.assertions.consoleErrors = state.events.console.filter((entry) => entry.type === "error").length;

  await browser.close();
  fs.writeFileSync(path.join(outDir, "round20-upload-cancel-state.json"), JSON.stringify(state, null, 2));
  console.log(JSON.stringify(state.assertions, null, 2));
}

main().catch(async (error) => {
  state.fatal = { message: error.message, stack: error.stack };
  fs.writeFileSync(path.join(outDir, "round20-upload-cancel-state.json"), JSON.stringify(state, null, 2));
  console.error(error);
  process.exit(1);
});
