const { createRequire } = require("module");
const fs = require("fs");
const path = require("path");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const apiBase = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8000";
const screenshotDir = path.resolve(__dirname, "screenshots");
const statePath = path.resolve(__dirname, "round15-project-create-validation-state.json");

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

async function findLastVisible(locator, label) {
  const count = await locator.count();
  for (let i = count - 1; i >= 0; i -= 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      return candidate;
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

async function snapshot(page, name) {
  await page.screenshot({
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: true,
  });
  return {
    name,
    screenshot: `screenshots/${name}.png`,
    url: page.url(),
    bodyText: await page.locator("body").innerText().catch(() => ""),
    formValidity: await page.evaluate(() => {
      const controls = Array.from(document.querySelectorAll("input, textarea"));
      return controls
        .filter((control) => control.offsetParent !== null)
        .map((control) => ({
          tag: control.tagName.toLowerCase(),
          type: control.getAttribute("type"),
          label: control.labels?.[0]?.textContent?.trim() || control.getAttribute("aria-label") || "",
          valueLength: control.value.length,
          valuePreview: control.value.slice(0, 40),
          required: control.required,
          valid: control.checkValidity(),
          validationMessage: control.validationMessage,
        }));
    }).catch(() => []),
  };
}

async function openCreateForm(page) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);
  if (!(await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).last().isVisible().catch(() => false))) {
    await clickLastVisible(page.getByRole("button", { name: "开始" }), "start nav").catch(() => {});
    await page.waitForTimeout(300);
  }
  if (!(await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).last().isVisible().catch(() => false))) {
    await clickLastVisible(page.getByRole("button", { name: /返回三选一/ }), "return three choices").catch(() => {});
    await page.waitForTimeout(500);
  }
  await clickLastVisible(page.getByRole("button", { name: /从技术想法撰写发明专利/ }), "invention entry");
  await page.waitForTimeout(300);
}

async function getProjects() {
  const response = await fetch(`${apiBase}/api/projects`);
  const payload = await response.json();
  return Array.isArray(payload) ? payload : payload.projects || [];
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

  const cases = [
    {
      id: "empty",
      projectName: null,
      idea: null,
      expectProjectCreated: false,
    },
    {
      id: "both-whitespace",
      projectName: "       ",
      idea: "          ",
      expectProjectCreated: false,
    },
    {
      id: "name-whitespace",
      projectName: "       ",
      idea: "一种用于验证项目创建表单校验的有效技术想法，应该在项目名为空白时被阻止创建。",
      expectProjectCreated: false,
    },
    {
      id: "idea-whitespace",
      projectName: `Round15 空白想法项目 ${Date.now()}`,
      idea: "          ",
      expectProjectCreated: false,
    },
  ];

  const results = [];
  const errors = [];

  try {
    for (const testCase of cases) {
      const caseErrors = [];
      const beforeProjects = await getProjects();
      const beforePostCount = mutatingRequests.filter((request) => request.url.includes("/api/projects")).length;
      const states = [];

      try {
        await openCreateForm(page);
        states.push(await snapshot(page, `round15-${testCase.id}-before-submit`));

        if (testCase.projectName !== null) {
          await fillFirstVisible(
            [page.getByLabel("项目名称", { exact: true }), page.locator("input:not([type='hidden'])")],
            testCase.projectName,
            "project name",
          );
        }
        if (testCase.idea !== null) {
          await fillFirstVisible(
            [page.getByLabel("一句话想法", { exact: true }), page.locator("textarea")],
            testCase.idea,
            "idea",
          );
        }
        states.push(await snapshot(page, `round15-${testCase.id}-filled`));

        const createButton = await findLastVisible(page.getByRole("button", { name: "创建并继续" }), "create project");
        const createButtonDisabled = await createButton.isDisabled().catch(() => null);
        let clickAttempted = false;
        let clickError = null;

        if (!createButtonDisabled) {
          clickAttempted = true;
          await createButton.click({ timeout: 5000 }).catch((error) => {
            clickError = error.message;
          });
          await page.waitForTimeout(1200);
        }

        states.push({
          ...(await snapshot(page, `round15-${testCase.id}-after-submit`)),
          createButtonDisabled,
          clickAttempted,
          clickError,
        });
      } catch (error) {
        caseErrors.push({ message: error.message, stack: error.stack });
        states.push(await snapshot(page, `round15-${testCase.id}-case-error`).catch(() => ({
          name: `round15-${testCase.id}-case-error`,
          screenshot: null,
          url: page.url(),
        })));
      }

      const afterProjects = await getProjects();
      const afterPostCount = mutatingRequests.filter((request) => request.url.includes("/api/projects")).length;
      const newProjects = afterProjects.filter(
        (project) => !beforeProjects.some((existing) => existing.id === project.id),
      );

      results.push({
        id: testCase.id,
        input: {
          projectNameLength: testCase.projectName?.length ?? 0,
          projectNameTrimLength: testCase.projectName?.trim().length ?? 0,
          ideaLength: testCase.idea?.length ?? 0,
          ideaTrimLength: testCase.idea?.trim().length ?? 0,
        },
        expectedProjectCreated: testCase.expectProjectCreated,
        postRequestsDuringCase: afterPostCount - beforePostCount,
        newProjects,
        caseErrors,
        states,
      });
    }
  } catch (error) {
    errors.push({ message: error.message, stack: error.stack });
    results.push({
      id: "probe-error",
      states: [await snapshot(page, "round15-probe-error").catch(() => ({
        name: "round15-probe-error",
        screenshot: null,
        url: page.url(),
      }))],
    });
  } finally {
    const state = {
      results,
      projects: await getProjects().catch((error) => ({ error: error.message })),
      mutatingRequests,
      failedRequests,
      consoleMessages,
      pageErrors,
      errors,
    };
    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);

    console.log(JSON.stringify({
      statePath,
      resultCount: results.length,
      createdProjectCount: Array.isArray(state.projects) ? state.projects.length : null,
      casesCreatingProjects: results
        .filter((result) => Array.isArray(result.newProjects) && result.newProjects.length > 0)
        .map((result) => result.id),
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
