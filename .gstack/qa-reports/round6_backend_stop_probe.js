const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(`${process.cwd()}/frontend/package.json`);
const { chromium } = requireFromFrontend("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const apiBase = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8000";
const backendPid = Number.parseInt(process.env.PATENTAGENT_BACKEND_PID || "", 10);
const screenshotDir = ".gstack/qa-reports/screenshots";
const statePath = ".gstack/qa-reports/round6-backend-stop-state.json";

fs.mkdirSync(screenshotDir, { recursive: true });

function apiPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

async function clickText(page, text) {
  const exact = page.getByText(text, { exact: true }).first();
  if ((await exact.count()) > 0) {
    await exact.click();
    return true;
  }
  return false;
}

async function createProbeProject() {
  const response = await fetch(`${apiBase}/api/projects`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: `Round6 网络中断项目 ${Date.now()}`,
      draft_text: "一种用于验证后端离线状态的专利撰写工作台测试项目。",
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to create probe project: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

(async () => {
  const consoleErrors = [];
  const pageErrors = [];
  const responses = [];
  const requestsFailed = [];
  const result = {};

  if (!Number.isInteger(backendPid) || backendPid <= 0) {
    throw new Error("Set PATENTAGENT_BACKEND_PID to the backend process this probe is allowed to stop.");
  }
  const project = await createProbeProject();

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/")) {
      responses.push({
        url: apiPath(response.url()),
        status: response.status(),
        method: response.request().method(),
      });
    }
  });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/")) {
      requestsFailed.push({
        url: apiPath(request.url()),
        method: request.method(),
        failure: request.failure()?.errorText ?? "",
      });
    }
  });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  result.beforeStopText = await page.locator("body").innerText();
  await page.screenshot({ path: path.join(screenshotDir, "round6-before-backend-stop.png"), fullPage: true });

  const selectors = page.locator("select");
  for (let index = 0; index < await selectors.count(); index += 1) {
    try {
      await selectors.nth(index).selectOption(project.id);
      break;
    } catch {
      // Try the next select. The page may have more than one select.
    }
  }
  await page.waitForTimeout(1000);
  result.selectedProjectText = await page.locator("body").innerText();
  await page.screenshot({ path: path.join(screenshotDir, "round6-selected-before-stop.png"), fullPage: true });

  process.kill(backendPid, "SIGINT");
  await page.waitForTimeout(2000);

  const refreshButton = page.getByRole("button", { name: /刷新运行状态/ }).first();
  if ((await refreshButton.count()) > 0) {
    await refreshButton.click();
  }
  await page.waitForTimeout(1200);
  result.afterRefreshText = await page.locator("body").innerText();
  await page.screenshot({ path: path.join(screenshotDir, "round6-after-stop-refresh.png"), fullPage: true });

  await clickText(page, "项目");
  await page.waitForTimeout(1000);
  result.afterProjectsText = await page.locator("body").innerText();
  await page.screenshot({ path: path.join(screenshotDir, "round6-after-stop-projects.png"), fullPage: true });

  await clickText(page, "设置");
  await page.waitForTimeout(1000);
  result.afterSettingsText = await page.locator("body").innerText();
  await page.screenshot({ path: path.join(screenshotDir, "round6-after-stop-settings.png"), fullPage: true });

  await browser.close();

  const afterStopText = [
    result.afterRefreshText,
    result.afterProjectsText,
    result.afterSettingsText,
  ].join("\n");
  const assertions = {
    selectedProjectBeforeStop: Boolean(project?.name && result.selectedProjectText.includes(project.name)),
    backendOfflineVisible: /后端离线|项目列表加载失败|无法连接到 LLM 服务|操作失败|请求失败/.test(afterStopText),
    capabilitiesNotShownAvailable:
      !/基础模型\s*\n可用/.test(result.afterRefreshText)
      && !/智能体\s*\n完整会审/.test(result.afterRefreshText)
      && !/内部痕迹检查\s*\n可用/.test(result.afterRefreshText),
    projectsLoadFailureVisible: result.afterProjectsText.includes("项目列表加载失败"),
    cachedProjectMarkedStale:
      result.afterProjectsText.includes("显示上次成功加载的数据")
      && Boolean(project?.name && result.afterProjectsText.includes(project.name)),
    noPageErrors: pageErrors.length === 0,
  };

  fs.writeFileSync(
    statePath,
    JSON.stringify(
      {
        baseUrl,
        apiBase,
        backendPid,
        project,
        consoleErrors,
        pageErrors,
        responses,
        requestsFailed,
        assertions,
        ...result,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ statePath, assertions }, null, 2));
  if (!Object.values(assertions).every(Boolean)) {
    process.exit(1);
  }
})().catch(async (error) => {
  fs.writeFileSync(
    statePath,
    JSON.stringify({ fatal: error.message, stack: error.stack }, null, 2),
  );
  process.exit(1);
});
