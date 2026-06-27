const fs = require("fs");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(`${process.cwd()}/frontend/package.json`);
const { chromium } = requireFromFrontend("playwright");

function apiPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

async function screenshotText(page, name) {
  await page.screenshot({ path: `.gstack/qa-reports/screenshots/${name}.png`, fullPage: true });
  return page.locator("body").innerText();
}

(async () => {
  const consoleErrors = [];
  const pageErrors = [];
  const responses = [];
  const requestsFailed = [];
  const projectPosts = [];

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", async (response) => {
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

  await page.route("**/api/projects", async (route, request) => {
    if (request.method() === "POST") {
      projectPosts.push({
        time: Date.now(),
        postData: request.postData(),
      });
      await new Promise((resolve) => setTimeout(resolve, 900));
    }
    await route.continue();
  });

  await page.goto("http://127.0.0.1:5174/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  await page.getByText("从技术想法撰写发明专利").first().click();
  await page.waitForTimeout(1000);

  await page.getByLabel("项目名称").fill("Round9 双击创建项目");
  await page.getByLabel("一句话想法").fill(
    "一种用于验证创建项目按钮重复点击防护的本地 QA 技术方案，关注慢网络下是否重复提交。",
  );
  const beforeSubmitText = await screenshotText(page, "round9-duplicate-create-before-submit");

  const submitButton = page.getByRole("button", { name: "创建并继续" });
  const beforeDisabled = await submitButton.isDisabled();
  await submitButton.click();
  await page.waitForTimeout(60);
  const duringDisabled = await submitButton.isDisabled().catch(() => null);
  await submitButton.click({ force: true }).catch((error) => {
    consoleErrors.push(`Second click failed: ${error.message}`);
  });
  const duringSubmitText = await screenshotText(page, "round9-duplicate-create-during-submit");

  await page.waitForTimeout(2200);
  const afterSubmitText = await screenshotText(page, "round9-duplicate-create-after-submit");
  const projects = await page.evaluate(async () => {
    const response = await fetch("/api/projects");
    const data = await response.json();
    return data.projects.map((project) => ({
      id: project.id,
      name: project.name,
      patent_type: project.patent_type,
      created_at: project.created_at,
      updated_at: project.updated_at,
    }));
  });

  const matchingProjects = projects.filter((project) => project.name === "Round9 双击创建项目");
  const selectorOptions = await page
    .locator("select")
    .first()
    .evaluate((select) =>
      Array.from(select.options).map((option) => ({
        value: option.value,
        text: option.textContent,
        selected: option.selected,
      })),
    );

  await browser.close();

  fs.writeFileSync(
    ".gstack/qa-reports/round9-duplicate-create-state.json",
    JSON.stringify(
      {
        consoleErrors,
        pageErrors,
        responses,
        requestsFailed,
        projectPosts,
        beforeDisabled,
        duringDisabled,
        projects,
        matchingProjects,
        selectorOptions,
        beforeSubmitText,
        duringSubmitText,
        afterSubmitText,
      },
      null,
      2,
    ),
  );
})().catch((error) => {
  fs.writeFileSync(
    ".gstack/qa-reports/round9-duplicate-create-state.json",
    JSON.stringify({ fatal: error.message, stack: error.stack }, null, 2),
  );
  process.exit(1);
});
