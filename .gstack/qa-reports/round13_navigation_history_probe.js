const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const apiBase = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round13-navigation-history-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

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

async function snapshotState(page, name) {
  await page.screenshot({
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: true,
  });
  const html = await page.locator("html").evaluate((node) => node.outerHTML.slice(0, 4000)).catch(() => "");
  return {
    name,
    url: page.url(),
    historyLength: await page.evaluate(() => window.history.length).catch(() => null),
    bodyText: await page.locator("body").innerText().catch(() => ""),
    htmlSnippet: html,
    screenshot: `screenshots/${name}.png`,
  };
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  const consoleMessages = [];
  const failedRequests = [];
  const pageErrors = [];
  const mutatingRequests = [];

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("requestfailed", (request) => {
    failedRequests.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
    });
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      mutatingRequests.push({ method: request.method(), url: request.url(), ts: Date.now() });
    }
  });

  const states = [];
  const errors = [];
  let projectName = null;
  let createdProject = null;

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    states.push(await snapshotState(page, "round13-start-page"));

    await clickLastVisible(page.getByRole("button", { name: /从技术想法撰写发明专利/ }), "invention entry");
    await page.waitForTimeout(300);
    states.push(await snapshotState(page, "round13-create-form"));

    projectName = `Round13 导航返回项目 ${Date.now()}`;
    const idea =
      "一种面向单页专利撰写应用的导航状态保持方法，在用户使用浏览器返回、前进或应用内返回入口时保持当前项目上下文清晰。";
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
    await clickLastVisible(page.getByRole("button", { name: "创建并继续" }), "create project");
    await page.waitForFunction(
      (name) => document.body.innerText.includes(name) && document.body.innerText.includes("提炼发明点"),
      projectName,
      { timeout: 10000 },
    );
    await page.waitForTimeout(500);
    states.push(await snapshotState(page, "round13-after-create"));

    await clickLastVisible(page.getByRole("button", { name: "项目" }), "project nav");
    await page.waitForTimeout(700);
    states.push(await snapshotState(page, "round13-projects-page"));

    const beforeBackUrl = page.url();
    const backResult = await page.goBack({ waitUntil: "domcontentloaded", timeout: 5000 }).catch((error) => ({
      error: error.message,
    }));
    await page.waitForTimeout(1000);
    states.push({
      ...(await snapshotState(page, "round13-after-browser-back")),
      backResult:
        backResult && typeof backResult.status === "function" ? { status: backResult.status(), url: backResult.url() } : backResult,
      beforeBackUrl,
    });

    const beforeForwardUrl = page.url();
    const forwardResult = await page.goForward({ waitUntil: "domcontentloaded", timeout: 5000 }).catch((error) => ({
      error: error.message,
    }));
    await page
      .waitForFunction(
        (name) => {
          const body = document.body.innerText || "";
          return body.includes(name) || !body.includes("正在刷新工作台");
        },
        projectName,
        { timeout: 8000 },
      )
      .catch(() => {});
    await page.waitForTimeout(500);
    states.push({
      ...(await snapshotState(page, "round13-after-browser-forward")),
      forwardResult:
        forwardResult && typeof forwardResult.status === "function"
          ? { status: forwardResult.status(), url: forwardResult.url() }
          : forwardResult,
      beforeForwardUrl,
    });

    try {
      await clickLastVisible(page.getByRole("button", { name: "开始" }), "start nav");
      await page.waitForTimeout(500);
      await clickLastVisible(page.getByRole("button", { name: /返回三选一/ }), "return three choices");
      await page.waitForTimeout(500);
      states.push(await snapshotState(page, "round13-after-return-three-choices"));
    } catch (error) {
      errors.push({ phase: "return-three-choices", message: error.message });
      states.push({
        ...(await snapshotState(page, "round13-return-three-choices-unavailable")),
        returnThreeChoicesError: error.message,
      });
    }
  } catch (error) {
    errors.push({ phase: "main-flow", message: error.message, stack: error.stack });
    states.push(await snapshotState(page, "round13-main-flow-error").catch(() => ({
      name: "round13-main-flow-error",
      url: page.url(),
      screenshot: null,
    })));
  } finally {
    if (projectName) {
      const projectsResponse = await fetch(`${apiBase}/api/projects`).catch((error) => ({ error }));
      if (projectsResponse && !projectsResponse.error) {
        const projectsPayload = await projectsResponse.json();
        const projects = Array.isArray(projectsPayload) ? projectsPayload : projectsPayload.projects || [];
        createdProject = projects.find((project) => project.name === projectName) || null;
      } else if (projectsResponse?.error) {
        errors.push({ phase: "fetch-projects", message: projectsResponse.error.message });
      }
    }

    const afterBack = states.find((state) => state.name === "round13-after-browser-back");
    const afterForward = states.find((state) => state.name === "round13-after-browser-forward");
    const assertions = {
      createdProjectFound: Boolean(createdProject?.id),
      backDidNotLeaveApp: Boolean(afterBack && afterBack.url !== "about:blank" && afterBack.bodyText.trim().length > 0),
      forwardDidNotLoseProject: Boolean(afterForward && projectName && afterForward.bodyText.includes(projectName)),
      returnThreeChoicesAvailable: !errors.some((error) => error.phase === "return-three-choices"),
      noPageErrors: pageErrors.length === 0,
    };
    const state = {
      projectName,
      createdProject,
      states,
      mutatingRequests,
      failedRequests,
      consoleMessages,
      pageErrors,
      errors,
      assertions,
    };
    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify({
      statePath,
      projectId: createdProject?.id || null,
      stateCount: states.length,
      mutatingRequestCount: mutatingRequests.length,
      failedRequests: failedRequests.length,
      consoleMessages: consoleMessages.length,
      pageErrors: pageErrors.length,
      errorCount: errors.length,
      finalUrl: page.url(),
      assertions,
      finalHistoryLength: await page.evaluate(() => window.history.length).catch(() => null),
    }, null, 2));

    await browser.close();
    if (!Object.values(assertions).every(Boolean)) {
      process.exit(1);
    }
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
