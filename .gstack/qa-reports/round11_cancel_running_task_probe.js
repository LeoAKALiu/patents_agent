const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const apiBase = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round11-cancel-running-task-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

async function fillFirstVisible(locators, value, label) {
  for (const locator of locators) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < count; i += 1) {
      const candidate = locator.nth(i);
      if (await candidate.isVisible().catch(() => false)) {
        await candidate.fill(value);
        return;
      }
    }
  }
  throw new Error(`Could not find visible field for ${label}`);
}

async function clickLastVisible(locator, label, options = {}) {
  const count = await locator.count();
  for (let i = count - 1; i >= 0; i -= 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.click(options);
      return;
    }
  }
  throw new Error(`Could not find visible control for ${label}`);
}

async function bodyText(page) {
  return page.locator("body").innerText();
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  const consoleMessages = [];
  const failedRequests = [];
  const mutatingRequests = [];

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("requestfailed", (request) => {
    failedRequests.push({
      url: request.url(),
      method: request.method(),
      failure: request.failure()?.errorText || "unknown",
    });
  });
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutatingRequests.push({ method: request.method(), url: request.url(), ts: Date.now() });
    }
  });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  await clickLastVisible(
    page.getByRole("button", { name: /从技术想法撰写发明专利/ }),
    "invention idea entry",
  );
  await page.waitForTimeout(300);

  const projectName = `Round11 取消运行项目 ${Date.now()}`;
  const idea =
    "一种面向专利撰写工作台的运行控制系统，能够在用户误触或发现输入错误时取消正在进行的发明点提炼任务，并保持项目状态可恢复。";

  await fillFirstVisible(
    [page.getByLabel("项目名称", { exact: true }), page.locator("input:not([type='hidden'])")],
    projectName,
    "project name",
  );
  await fillFirstVisible(
    [page.getByLabel("一句话想法", { exact: true }), page.locator("textarea")],
    idea,
    "idea",
  );

  await page.screenshot({
    path: path.join(screenshotDir, "round11-create-before.png"),
    fullPage: true,
  });

  await clickLastVisible(page.getByRole("button", { name: "创建并继续" }), "create project");
  await page.waitForFunction(
    () => document.body.innerText.includes("提炼发明点") && document.body.innerText.includes("当前步骤"),
    null,
    { timeout: 10000 },
  );

  await page.screenshot({
    path: path.join(screenshotDir, "round11-before-run.png"),
    fullPage: true,
  });

  await clickLastVisible(page.locator("button").filter({ hasText: /^提炼发明点$/ }), "start invention point extraction");
  await page.waitForFunction(
    () => document.body.innerText.includes("正在提炼发明点") || document.body.innerText.includes("发明点提炼运行中"),
    null,
    { timeout: 10000 },
  );
  const cancelWaitStartedAt = Date.now();
  let cancelReadyMs = null;
  let cancelWaitError = null;
  try {
    await page.getByRole("button", { name: /取消运行/ }).last().waitFor({ state: "visible", timeout: 12000 });
    cancelReadyMs = Date.now() - cancelWaitStartedAt;
  } catch (error) {
    cancelWaitError = error.message;
  }

  await page.screenshot({
    path: path.join(screenshotDir, "round11-running-before-cancel.png"),
    fullPage: true,
  });
  const runningText = await bodyText(page);

  const cancelButtonsBefore = await page.getByRole("button", { name: /取消运行/ }).count();
  let cancelClickError = null;
  try {
    await clickLastVisible(page.getByRole("button", { name: /取消运行/ }), "cancel run");
  } catch (error) {
    cancelClickError = error.message;
  }
  await page.waitForTimeout(9000);

  await page.screenshot({
    path: path.join(screenshotDir, "round11-after-cancel.png"),
    fullPage: true,
  });
  const afterCancelText = await bodyText(page);
  const cancelButtonsAfter = await page.getByRole("button", { name: /取消运行/ }).count();
  const startButtonAfter = await page.locator("button").filter({ hasText: /^提炼发明点$/ }).last().evaluate(
    (element) => ({
      text: element.innerText,
      disabled: element.disabled || element.getAttribute("aria-disabled") === "true",
    }),
  ).catch(() => null);

  const projectsResponse = await fetch(`${apiBase}/api/projects`);
  const projectsPayload = await projectsResponse.json();
  const projects = Array.isArray(projectsPayload) ? projectsPayload : projectsPayload.projects || [];
  const project = projects.find((item) => item.name === projectName) || null;

  let disclosuresState = null;
  let patentPointsState = null;
  if (project) {
    const disclosuresResponse = await fetch(`${apiBase}/api/projects/${project.id}/disclosures`);
    disclosuresState = {
      status: disclosuresResponse.status,
      body: await disclosuresResponse.text(),
    };
    const pointsResponse = await fetch(`${apiBase}/api/projects/${project.id}/patent-points`);
    patentPointsState = {
      status: pointsResponse.status,
      body: await pointsResponse.text(),
    };
  }

  const state = {
    projectName,
    projectId: project?.id || null,
    cancelReadyMs,
    cancelWaitError,
    cancelButtonsBefore,
    cancelClickError,
    cancelButtonsAfter,
    startButtonAfter,
    mutatingRequests,
    runningText,
    afterCancelText,
    disclosuresState,
    patentPointsState,
    failedRequests,
    consoleMessages,
    screenshots: [
      "screenshots/round11-create-before.png",
      "screenshots/round11-before-run.png",
      "screenshots/round11-running-before-cancel.png",
      "screenshots/round11-after-cancel.png",
    ],
  };

  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
  console.log(JSON.stringify({
    statePath,
    projectId: state.projectId,
    cancelButtonsBefore,
    cancelClickError,
    cancelButtonsAfter,
    startButtonAfter,
    mutatingRequestCount: mutatingRequests.length,
    failedRequests: failedRequests.length,
    consoleMessages: consoleMessages.length,
  }, null, 2));

  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
