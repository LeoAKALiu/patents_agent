const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round30");
const fixtureDir = path.join(outDir, "fixtures");
const fixturePath = path.join(fixtureDir, "round30-unreadable-material.md");
const statePath = path.join(outDir, "round30-unreadable-file-state.json");
fs.mkdirSync(screenshotDir, { recursive: true });
fs.mkdirSync(fixtureDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  fixturePath,
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
      fileInputs: Array.from(document.querySelectorAll('input[type="file"]')).map((input) => ({
        visible: !!(input.offsetWidth || input.offsetHeight || input.getClientRects().length),
        value: input.value,
        files: Array.from(input.files || []).map((file) => ({ name: file.name, size: file.size, type: file.type })),
      })),
      visibleButtons: Array.from(document.querySelectorAll("button"))
        .filter((button) => {
          const rect = button.getBoundingClientRect();
          const style = getComputedStyle(button);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        })
        .map((button) => ({
          text: (button.innerText || button.textContent || "").trim().replace(/\s+/g, " ").slice(0, 160),
          disabled: button.disabled,
          ariaDisabled: button.getAttribute("aria-disabled"),
        })),
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
  await page.waitForTimeout(700);
}

async function currentProjectId(page) {
  const projects = await page.evaluate(async () => {
    const response = await fetch("/api/projects");
    return response.json();
  });
  const project = projects.projects.find((entry) => entry.name === state.projectName);
  if (!project) throw new Error(`Created project not found: ${state.projectName}`);
  return project.id;
}

async function materialsFor(page, projectId) {
  return page.evaluate(async (id) => {
    const response = await fetch(`/api/projects/${id}/materials`);
    return response.json();
  }, projectId);
}

function prepareUnreadableFixture() {
  fs.writeFileSync(
    fixturePath,
    "# Round30 unreadable material\n\nThis file is intentionally chmod 000 to simulate a local permission-denied upload selection.\n",
    "utf8"
  );
  fs.chmodSync(fixturePath, 0o000);
  const stat = fs.statSync(fixturePath);
  state.fixture = {
    path: fixturePath,
    modeOctal: `0${(stat.mode & 0o777).toString(8)}`,
    size: stat.size,
  };
}

async function main() {
  prepareUnreadableFixture();

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

  state.projectName = `Round30 无读权限材料 ${Date.now()}`;
  const idea = "一种用于验证补充材料文件无读取权限时，前端上传流程是否产生错误状态或污染材料记录的测试项目。";

  try {
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
    try {
      await chooser.setFiles(fixturePath);
      state.fileChooserSetFiles = { ok: true };
    } catch (error) {
      state.fileChooserSetFiles = {
        ok: false,
        message: error.message,
        name: error.name,
      };
    }

    await page.waitForTimeout(1200);
    await evidence(page, "04-after-unreadable-selection-attempt");

    state.materialsAfter = await materialsFor(page, projectId);
    const materialPostCountAfter = state.events.materialResponses.filter((entry) => entry.method === "POST").length;
    const bodyText = await page.locator("body").innerText();

    state.assertions = {
      projectId,
      fixtureModeOctal: state.fixture.modeOctal,
      fileChooserBlockedByLocalPermission: state.fileChooserSetFiles && state.fileChooserSetFiles.ok === false,
      fileChooserErrorMentionsAccess: /EACCES|permission|denied|not readable|open/i.test((state.fileChooserSetFiles && state.fileChooserSetFiles.message) || ""),
      materialCountBefore: state.materialsBefore.materials.length,
      materialCountAfter: state.materialsAfter.materials.length,
      materialPostCountBefore,
      materialPostCountAfter,
      noMaterialPostAfterUnreadableSelection: materialPostCountAfter === materialPostCountBefore,
      noMaterialCountIncrease: state.materialsAfter.materials.length === state.materialsBefore.materials.length,
      noSuccessText: !bodyText.includes("已上传材料") && !bodyText.includes("当前已有 1 份材料"),
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      productDidNotReceiveUnreadableFile:
        state.fileChooserSetFiles &&
        state.fileChooserSetFiles.ok === false &&
        materialPostCountAfter === materialPostCountBefore &&
        state.materialsAfter.materials.length === state.materialsBefore.materials.length,
    };
  } finally {
    await browser.close().catch(() => {});
    try {
      fs.chmodSync(fixturePath, 0o644);
    } catch (_) {
      // Keep cleanup best-effort so the state file is still written.
    }
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  }

  console.log(JSON.stringify(state.assertions, null, 2));
}

main().catch((error) => {
  state.fatal = { message: error.message, stack: error.stack };
  try {
    fs.chmodSync(fixturePath, 0o644);
  } catch (_) {}
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  console.error(error);
  process.exit(1);
});
