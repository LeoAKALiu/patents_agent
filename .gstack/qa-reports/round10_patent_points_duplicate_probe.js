const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round10-patent-points-duplicate-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

async function fillFirstVisible(locators, value, label) {
  for (const locator of locators) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < count; i += 1) {
      const candidate = locator.nth(i);
      if (await candidate.isVisible().catch(() => false)) {
        await candidate.fill(value);
        return label;
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
      return i;
    }
  }
  throw new Error(`Could not find visible button for ${label}`);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  const consoleMessages = [];
  const failedRequests = [];
  const pointRequests = [];
  const disclosureRequests = [];
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
    if (request.method() === "POST" && request.url().includes("/patent-points")) {
      pointRequests.push({ url: request.url(), ts: Date.now() });
    }
    if (request.method() === "POST" && request.url().includes("/disclosures")) {
      disclosureRequests.push({ url: request.url(), ts: Date.now() });
    }
  });

  await page.route("**/api/projects/**/disclosures**", async (route) => {
    if (route.request().method() === "POST") {
      await new Promise((resolve) => setTimeout(resolve, 900));
    }
    await route.continue();
  });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  await clickLastVisible(
    page.getByRole("button", { name: /从技术想法撰写发明专利/ }),
    "invention idea entry",
  );
  await page.waitForTimeout(300);

  const projectName = `Round10 提炼发明点双击项目 ${Date.now()}`;
  const idea =
    "一种面向企业专利撰写的本地化智能代理系统，通过材料解析、发明点提炼、权利要求会审和正式稿编译，减少重复撰写并保留可追溯证据。";

  await fillFirstVisible(
    [
      page.getByLabel("项目名称", { exact: true }),
      page.locator("input:not([type='hidden'])"),
    ],
    projectName,
    "project name",
  );
  await fillFirstVisible(
    [
      page.getByLabel("一句话想法", { exact: true }),
      page.locator("textarea"),
    ],
    idea,
    "idea",
  );

  await page.screenshot({
    path: path.join(screenshotDir, "round10-create-before.png"),
    fullPage: true,
  });

  await clickLastVisible(page.getByRole("button", { name: "创建并继续" }), "create project");
  await page.waitForTimeout(300);
  await page.waitForFunction(
    () => document.body.innerText.includes("提炼发明点") && document.body.innerText.includes("当前步骤"),
    null,
    { timeout: 10000 },
  );

  await page.screenshot({
    path: path.join(screenshotDir, "round10-points-before-submit.png"),
    fullPage: true,
  });

  const pointButton = page.locator("button").filter({ hasText: /^提炼发明点$/ }).last();
  const beforeDisabled = await pointButton.evaluate(
    (element) => element.disabled || element.getAttribute("aria-disabled") === "true",
  );
  const beforeButtonText = await pointButton.innerText();

  let dblclickError = null;
  try {
    await pointButton.dblclick({ delay: 20, timeout: 5000 });
  } catch (error) {
    dblclickError = error.message;
  }

  await page.waitForTimeout(120);
  const duringDisabled = await pointButton.evaluate(
    (element) => element.disabled || element.getAttribute("aria-disabled") === "true",
  ).catch(() => null);
  const duringButtonText = await pointButton.innerText().catch(() => "");
  const duringText = await page.locator("body").innerText();

  await page.screenshot({
    path: path.join(screenshotDir, "round10-points-during-submit.png"),
    fullPage: true,
  });

  await page.waitForTimeout(5000);

  const afterText = await page.locator("body").innerText();
  const afterDisabled = await pointButton.evaluate(
    (element) => element.disabled || element.getAttribute("aria-disabled") === "true",
  ).catch(() => null);
  const afterButtonText = await pointButton.innerText().catch(() => "");

  await page.screenshot({
    path: path.join(screenshotDir, "round10-points-after-submit.png"),
    fullPage: true,
  });

  const projectsResponse = await fetch(`${apiBase}/api/projects`);
  const projectsPayload = await projectsResponse.json();
  const projects = Array.isArray(projectsPayload) ? projectsPayload : projectsPayload.projects || [];
  const project = projects.find((item) => item.name === projectName) || null;
  let patentPointsState = null;
  if (project) {
    const pointsResponse = await fetch(`${apiBase}/api/projects/${project.id}/patent-points`);
    patentPointsState = {
      status: pointsResponse.status,
      body: await pointsResponse.text(),
    };
  }

  const state = {
    projectName,
    projectId: project?.id || null,
    pointRequestCount: pointRequests.length,
    pointRequests,
    disclosureRequestCount: disclosureRequests.length,
    disclosureRequests,
    mutatingRequests,
    beforeDisabled,
    beforeButtonText,
    dblclickError,
    duringDisabled,
    duringButtonText,
    afterDisabled,
    afterButtonText,
    duringText,
    afterText,
    patentPointsState,
    failedRequests,
    consoleMessages,
    screenshots: [
      "screenshots/round10-create-before.png",
      "screenshots/round10-points-before-submit.png",
      "screenshots/round10-points-during-submit.png",
      "screenshots/round10-points-after-submit.png",
    ],
  };
  fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
  console.log(JSON.stringify({
    statePath,
    projectId: state.projectId,
    pointRequestCount: state.pointRequestCount,
    disclosureRequestCount: state.disclosureRequestCount,
    duringDisabled: state.duringDisabled,
    afterDisabled: state.afterDisabled,
    failedRequests: state.failedRequests.length,
    consoleMessages: state.consoleMessages.length,
  }, null, 2));

  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
