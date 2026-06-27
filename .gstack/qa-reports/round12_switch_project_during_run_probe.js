const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round12-switch-project-during-run-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

async function createProject(name, idea) {
  const response = await fetch(`${apiBase}/api/projects`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name,
      draft_text: idea,
      patent_type: "invention",
    }),
  });
  if (!response.ok) {
    throw new Error(`create project failed ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

async function selectProject(page, projectId) {
  const select = page.locator(`select:has(option[value="${projectId}"])`).first();
  await select.waitFor({ state: "visible", timeout: 10000 });
  await select.selectOption(projectId);
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

async function fetchJson(url) {
  const response = await fetch(url);
  return {
    status: response.status,
    body: await response.text(),
  };
}

(async () => {
  const suffix = Date.now();
  const projectA = await createProject(
    `Round12 运行中切换 A ${suffix}`,
    "一种运行中项目切换保护方法，用于确保用户在发明点提炼尚未结束时切换到另一项目，不会把运行结果写入错误项目。",
  );
  const projectB = await createProject(
    `Round12 运行中切换 B ${suffix}`,
    "一种用于对照测试的第二项目，用户在第一个项目的长任务运行时切换到该项目，应保持该项目没有继承第一个项目的运行结果。",
  );

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
      method: request.method(),
      url: request.url(),
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

  await selectProject(page, projectA.id);
  await page.waitForFunction(
    (name) => document.body.innerText.includes(name) && document.body.innerText.includes("提炼发明点"),
    projectA.name,
    { timeout: 10000 },
  );
  await page.screenshot({
    path: path.join(screenshotDir, "round12-project-a-before-run.png"),
    fullPage: true,
  });

  await clickLastVisible(page.locator("button").filter({ hasText: /^提炼发明点$/ }), "start project A run");
  await page.waitForFunction(
    () => document.body.innerText.includes("取消运行") || document.body.innerText.includes("发明点提炼运行中"),
    null,
    { timeout: 10000 },
  );
  await page.waitForTimeout(500);
  const runningAText = await page.locator("body").innerText();
  await page.screenshot({
    path: path.join(screenshotDir, "round12-project-a-running.png"),
    fullPage: true,
  });

  await selectProject(page, projectB.id);
  await page.waitForFunction(
    (name) => document.body.innerText.includes(name),
    projectB.name,
    { timeout: 10000 },
  );
  await page.waitForTimeout(2500);
  const afterSwitchText = await page.locator("body").innerText();
  await page.screenshot({
    path: path.join(screenshotDir, "round12-project-b-after-switch.png"),
    fullPage: true,
  });

  const projectADisclosures = await fetchJson(`${apiBase}/api/projects/${projectA.id}/disclosures`);
  const projectBDisclosures = await fetchJson(`${apiBase}/api/projects/${projectB.id}/disclosures`);
  const projectAPoints = await fetchJson(`${apiBase}/api/projects/${projectA.id}/patent-points`);
  const projectBPoints = await fetchJson(`${apiBase}/api/projects/${projectB.id}/patent-points`);

  const selectValues = await page.locator("select").evaluateAll((selects) =>
    selects.map((select) => ({
      value: select.value,
      text: select.options[select.selectedIndex]?.text || "",
    })),
  );

  const state = {
    projectA,
    projectB,
    selectValues,
    mutatingRequests,
    runningAText,
    afterSwitchText,
    projectADisclosures,
    projectBDisclosures,
    projectAPoints,
    projectBPoints,
    failedRequests,
    consoleMessages,
    screenshots: [
      "screenshots/round12-project-a-before-run.png",
      "screenshots/round12-project-a-running.png",
      "screenshots/round12-project-b-after-switch.png",
    ],
  };
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
  console.log(JSON.stringify({
    statePath,
    projectA: { id: projectA.id, name: projectA.name },
    projectB: { id: projectB.id, name: projectB.name },
    mutatingRequestCount: mutatingRequests.length,
    failedRequests: failedRequests.length,
    consoleMessages: consoleMessages.length,
    selectValues,
  }, null, 2));

  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
