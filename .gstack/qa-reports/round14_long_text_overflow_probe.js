const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round14-long-text-overflow-state.json");

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

async function collectMetrics(page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    const body = document.body;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const overflowElements = [];

    for (const element of Array.from(document.querySelectorAll("body *"))) {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) {
        continue;
      }
      const text = (element.textContent || "").replace(/\s+/g, " ").trim();
      const horizontallyOffscreen = rect.left < -1 || rect.right > viewportWidth + 1;
      const internallyOverflowing = element.scrollWidth > element.clientWidth + 2;
      if ((horizontallyOffscreen || internallyOverflowing) && text.length > 0) {
        overflowElements.push({
          tag: element.tagName.toLowerCase(),
          role: element.getAttribute("role"),
          ariaLabel: element.getAttribute("aria-label"),
          className: typeof element.className === "string" ? element.className.slice(0, 160) : "",
          text: text.slice(0, 180),
          rect: {
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            top: Math.round(rect.top),
            height: Math.round(rect.height),
          },
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          horizontallyOffscreen,
          internallyOverflowing,
        });
      }
    }

    return {
      url: location.href,
      viewportWidth,
      viewportHeight,
      bodyScrollWidth: body.scrollWidth,
      docScrollWidth: doc.scrollWidth,
      hasPageHorizontalOverflow: Math.max(body.scrollWidth, doc.scrollWidth) > viewportWidth + 2,
      bodyText: body.innerText.slice(0, 4000),
      overflowElements: overflowElements.slice(0, 50),
    };
  });
}

async function snapshot(page, name) {
  await page.screenshot({
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: true,
  });
  return {
    name,
    screenshot: `screenshots/${name}.png`,
    metrics: await collectMetrics(page),
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

  const timestamp = Date.now();
  const longToken = "NO_BREAK_TECHNICAL_IDENTIFIER_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".repeat(10);
  const projectName = `Round14 超长名称 ${timestamp} ${longToken}`;
  const paragraph =
    "一种面向复杂专利文本的排版鲁棒性验证方法，包含长项目名称、连续技术术语、公式化变量说明、边界状态描述以及多轮用户输入恢复。";
  const idea = [
    paragraph.repeat(30),
    longToken,
    "技术效果：" + "能够在桌面和窄屏界面中保持文本可读、控件不越界、页面不出现横向滚动。".repeat(30),
  ].join("\n\n");

  const states = [];
  const errors = [];
  let createdProject = null;

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    states.push(await snapshot(page, "round14-start-desktop"));

    await clickLastVisible(page.getByRole("button", { name: /从技术想法撰写发明专利/ }), "invention entry");
    await page.waitForTimeout(300);
    await fillFirstVisible(
      [page.getByLabel("项目名称", { exact: true }), page.locator("input:not([type='hidden'])")],
      projectName,
      "project name",
    );
    await fillFirstVisible(
      [page.getByLabel("一句话想法", { exact: true }), page.locator("textarea")],
      idea,
      "long idea",
    );
    states.push(await snapshot(page, "round14-filled-long-form-desktop"));

    await clickLastVisible(page.getByRole("button", { name: "创建并继续" }), "create project");
    await page.waitForFunction(
      (name) => document.body.innerText.includes(name.slice(0, 25)) && document.body.innerText.includes("提炼发明点"),
      projectName,
      { timeout: 15000 },
    );
    await page.waitForTimeout(700);
    states.push(await snapshot(page, "round14-after-create-desktop"));

    await clickLastVisible(page.getByRole("button", { name: "项目" }), "project nav desktop");
    await page.waitForTimeout(700);
    states.push(await snapshot(page, "round14-projects-desktop"));

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(700);
    states.push(await snapshot(page, "round14-projects-mobile"));

    await clickLastVisible(page.getByRole("button", { name: "开始" }), "start nav mobile");
    await page.waitForTimeout(700);
    states.push(await snapshot(page, "round14-start-mobile-with-long-project"));

    const projectsResponse = await fetch(`${apiBase}/api/projects`);
    const projectsPayload = await projectsResponse.json();
    const projects = Array.isArray(projectsPayload) ? projectsPayload : projectsPayload.projects || [];
    createdProject = projects.find((project) => project.name === projectName) || null;
  } catch (error) {
    errors.push({ message: error.message, stack: error.stack });
    states.push(await snapshot(page, "round14-error").catch(() => ({
      name: "round14-error",
      screenshot: null,
      metrics: { url: page.url() },
    })));
  } finally {
    const state = {
      projectName,
      projectNameLength: projectName.length,
      ideaLength: idea.length,
      longTokenLength: longToken.length,
      createdProject,
      states,
      mutatingRequests,
      failedRequests,
      consoleMessages,
      pageErrors,
      errors,
    };
    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);

    console.log(JSON.stringify({
      statePath,
      projectId: createdProject?.id || null,
      projectNameLength: projectName.length,
      ideaLength: idea.length,
      stateCount: states.length,
      statesWithPageHorizontalOverflow: states
        .filter((state) => state.metrics?.hasPageHorizontalOverflow)
        .map((state) => state.name),
      mutatingRequestCount: mutatingRequests.length,
      failedRequestCount: failedRequests.length,
      consoleMessageCount: consoleMessages.length,
      pageErrorCount: pageErrors.length,
      errorCount: errors.length,
    }, null, 2));

    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
