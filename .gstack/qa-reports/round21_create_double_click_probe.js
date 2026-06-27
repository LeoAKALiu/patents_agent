const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round21");
fs.mkdirSync(screenshotDir, { recursive: true });

const now = Date.now();
const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  projectName: `Round21 慢创建双击项目 ${now}`,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    projectRequests: [],
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
      text: (button.innerText || button.textContent || "").trim().replace(/\s+/g, " ").slice(0, 180),
      disabled: button.disabled,
      ariaDisabled: button.getAttribute("aria-disabled"),
      className: button.className,
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

async function projectsApi(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/projects");
    return response.json();
  });
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
    if (response.url().includes("/api/projects")) {
      state.events.projectResponses.push({
        url: response.url(),
        status: response.status(),
        method: response.request().method(),
      });
    }
  });

  await page.route("**/api/projects", async (route, request) => {
    if (request.method() === "POST") {
      state.events.projectRequests.push({
        url: request.url(),
        method: request.method(),
        postData: request.postData(),
        ts: Date.now(),
      });
      await new Promise((resolve) => setTimeout(resolve, 1800));
    }
    await route.continue();
  });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await waitForIdle(page);
  await evidence(page, "01-load-app");

  await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).click();
  await waitForIdle(page);
  await page.getByLabel("项目名称").fill(state.projectName);
  await page.getByLabel("一句话想法").fill("一种用于验证慢网络下项目创建按钮重复点击不会产生重复项目的专利撰写辅助流程。");
  await evidence(page, "02-filled-project-form");

  const submitButton = page.getByRole("button", { name: "创建并继续" });
  const responsePromise = page.waitForResponse((response) => response.url().endsWith("/api/projects") && response.request().method() === "POST", { timeout: 15000 });
  await submitButton.click();
  await page.waitForTimeout(80);
  const afterFirstClickMetrics = await evidence(page, "03-after-first-click-before-response");

  let secondClickError = null;
  try {
    await submitButton.click({ timeout: 700 });
  } catch (error) {
    secondClickError = { name: error.name, message: error.message };
  }
  state.secondClickError = secondClickError;
  await evidence(page, "04-after-second-click-attempt");

  const response = await responsePromise;
  state.assertions.firstCreateResponseStatus = response.status();
  await page.waitForTimeout(1800);
  await evidence(page, "05-after-create-response");

  const projects = await projectsApi(page);
  state.projectsAfter = projects;
  const matchingProjects = projects.projects.filter((project) => project.name === state.projectName);
  const postRequests = state.events.projectRequests.filter((entry) => entry.method === "POST");
  const postResponses = state.events.projectResponses.filter((entry) => entry.method === "POST");
  const createButtonAfterFirstClick = afterFirstClickMetrics.visibleButtons.find((button) => button.text.includes("创建并继续") || button.text.includes("填写并创建项目"));

  state.assertions.postRequestCount = postRequests.length;
  state.assertions.postResponseCount = postResponses.length;
  state.assertions.matchingProjectCount = matchingProjects.length;
  state.assertions.onlyOneCreatePost = postRequests.length === 1;
  state.assertions.onlyOneMatchingProject = matchingProjects.length === 1;
  state.assertions.submitDisabledAfterFirstClick = createButtonAfterFirstClick ? Boolean(createButtonAfterFirstClick.disabled || createButtonAfterFirstClick.ariaDisabled === "true") : null;
  state.assertions.secondClickBlockedOrIgnored = postRequests.length === 1;
  state.assertions.pageErrors = state.events.pageErrors.length;
  state.assertions.requestFailures = state.events.requestFailures.length;
  state.assertions.consoleErrors = state.events.console.filter((entry) => entry.type === "error").length;

  await browser.close();
  fs.writeFileSync(path.join(outDir, "round21-create-double-click-state.json"), JSON.stringify(state, null, 2));
  console.log(JSON.stringify(state.assertions, null, 2));
}

main().catch(async (error) => {
  state.fatal = { message: error.message, stack: error.stack };
  fs.writeFileSync(path.join(outDir, "round21-create-double-click-state.json"), JSON.stringify(state, null, 2));
  console.error(error);
  process.exit(1);
});
