const fs = require("fs");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(`${process.cwd()}/frontend/package.json`);
const { chromium } = requireFromFrontend("playwright");

const seeded = JSON.parse(fs.readFileSync(".gstack/qa-reports/round8-seeded-projects.json", "utf8")).projects;
const deleteTarget = seeded.find((project) => project.name.includes("Alpha")) ?? seeded[0];

function apiPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

async function snapshot(page, name) {
  await page.screenshot({ path: `.gstack/qa-reports/screenshots/${name}.png`, fullPage: true });
  return page.locator("body").innerText();
}

async function projectList(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/projects");
    const data = await response.json();
    return data.projects.map((project) => ({
      id: project.id,
      name: project.name,
      patent_type: project.patent_type,
      updated_at: project.updated_at,
    }));
  });
}

(async () => {
  const consoleErrors = [];
  const pageErrors = [];
  const responses = [];
  const requestsFailed = [];
  const dialogs = [];
  let nextDialogAction = "dismiss";

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
  page.on("dialog", async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message(), action: nextDialogAction });
    if (nextDialogAction === "accept") await dialog.accept();
    else await dialog.dismiss();
  });

  await page.goto("http://127.0.0.1:5174/", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.getByText("项目", { exact: true }).first().click();
  await page.waitForTimeout(1000);
  const initialProjectsText = await snapshot(page, "round8-projects-initial");
  const initialProjects = await projectList(page);

  await page.getByRole("button", { name: /实用新型/ }).click();
  await page.waitForTimeout(500);
  const utilityFilterText = await snapshot(page, "round8-projects-utility-filter");

  await page.getByRole("button", { name: /全部项目/ }).click();
  await page.waitForTimeout(500);

  const selector = page.locator("select").first();
  await selector.selectOption(deleteTarget.id);
  await page.waitForTimeout(1000);
  const selectedBeforeDeleteText = await snapshot(page, "round8-project-selected-before-delete");

  const deleteButtons = page.getByRole("button", { name: /^删除$/ });
  const deleteButtonCount = await deleteButtons.count();
  if (deleteButtonCount === 0) {
    throw new Error("No delete button found on project list");
  }

  nextDialogAction = "dismiss";
  await deleteButtons.first().click();
  await page.waitForTimeout(1000);
  const afterDismissText = await snapshot(page, "round8-project-delete-dismiss");
  const afterDismissProjects = await projectList(page);

  nextDialogAction = "accept";
  await deleteButtons.first().click();
  await page.waitForTimeout(1500);
  const afterAcceptText = await snapshot(page, "round8-project-delete-accept");
  const afterAcceptProjects = await projectList(page);

  const selectorOptionsAfterDelete = await page
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
    ".gstack/qa-reports/round8-project-delete-state.json",
    JSON.stringify(
      {
        deleteTarget,
        consoleErrors,
        pageErrors,
        responses,
        requestsFailed,
        dialogs,
        initialProjects,
        afterDismissProjects,
        afterAcceptProjects,
        selectorOptionsAfterDelete,
        initialProjectsText,
        utilityFilterText,
        selectedBeforeDeleteText,
        afterDismissText,
        afterAcceptText,
      },
      null,
      2,
    ),
  );
})().catch((error) => {
  fs.writeFileSync(
    ".gstack/qa-reports/round8-project-delete-state.json",
    JSON.stringify({ fatal: error.message, stack: error.stack }, null, 2),
  );
  process.exit(1);
});
