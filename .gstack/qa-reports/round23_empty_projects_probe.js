const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBaseUrl = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round23");
const statePath = path.resolve(".gstack/qa-reports/round23-empty-projects-state.json");

fs.mkdirSync(outDir, { recursive: true });

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function collectState(page, label) {
  return page.evaluate((stateLabel) => {
    function isVisible(el) {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        rect.bottom > 0 &&
        rect.right > 0 &&
        rect.top < window.innerHeight &&
        rect.left < window.innerWidth &&
        style.display !== "none" &&
        style.visibility !== "hidden"
      );
    }

    const overflowingElements = Array.from(document.querySelectorAll("body *"))
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        return rect.right > window.innerWidth + 1 || rect.left < -1;
      })
      .slice(0, 20)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 120),
        left: Math.round(el.getBoundingClientRect().left),
        right: Math.round(el.getBoundingClientRect().right),
        width: Math.round(el.getBoundingClientRect().width),
        className: typeof el.className === "string" ? el.className : "",
      }));

    return {
      label: stateLabel,
      url: location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      bodyText: document.body.innerText,
      bodyTextSample: document.body.innerText.slice(0, 2400),
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      hasHorizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      overflowingElements,
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button]"))
        .filter(isVisible)
        .map((el) => ({
          text: (el.innerText || el.getAttribute("aria-label") || "").trim(),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        })),
      visibleSelects: Array.from(document.querySelectorAll("select"))
        .filter(isVisible)
        .map((select) => ({
          value: select.value,
          selectedText: select.options[select.selectedIndex]?.text || "",
          optionCount: select.options.length,
        })),
    };
  }, label);
}

async function fetchJson(url) {
  const response = await fetch(url);
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { status: response.status, text, json };
}

function projectList(apiResponse) {
  if (Array.isArray(apiResponse.json)) {
    return apiResponse.json;
  }
  if (Array.isArray(apiResponse.json?.projects)) {
    return apiResponse.json.projects;
  }
  return null;
}

(async () => {
  const events = { console: [], pageErrors: [], requestFailures: [], appRequests: [] };
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("console", (msg) => events.console.push({ type: msg.type(), text: msg.text() }));
    page.on("pageerror", (err) => events.pageErrors.push({ message: err.message, stack: err.stack }));
    page.on("requestfailed", (request) => {
      events.requestFailures.push({ method: request.method(), url: request.url(), failure: request.failure() });
    });
    page.on("response", (response) => {
      const url = response.url();
      if (url.includes("/api/projects")) {
        events.appRequests.push({ url, status: response.status(), method: response.request().method() });
      }
    });

    const initialProjects = await fetchJson(`${apiBaseUrl}/api/projects`);

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath("01-home-empty-data"), fullPage: true });
    const home = await collectState(page, "home");

    await page.getByRole("button", { name: "项目" }).first().click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: screenshotPath("02-projects-empty-desktop"), fullPage: true });
    const projectsDesktop = await collectState(page, "projects-desktop");
    const projectsAfterNav = await fetchJson(`${apiBaseUrl}/api/projects`);

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(700);
    await page.screenshot({ path: screenshotPath("03-projects-empty-mobile"), fullPage: true });
    const projectsMobile = await collectState(page, "projects-mobile");

    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.waitForTimeout(500);
    await page.getByRole("button", { name: "开始" }).first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: screenshotPath("04-return-to-start"), fullPage: true });
    const afterReturnToStart = await collectState(page, "after-return-to-start");

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      apiBaseUrl,
      events,
      screenshots: {
        home: screenshotPath("01-home-empty-data"),
        projectsDesktop: screenshotPath("02-projects-empty-desktop"),
        projectsMobile: screenshotPath("03-projects-empty-mobile"),
        afterReturnToStart: screenshotPath("04-return-to-start"),
      },
      api: {
        initialProjects,
        projectsAfterNav,
      },
      states: {
        home,
        projectsDesktop,
        projectsMobile,
        afterReturnToStart,
      },
      assertions: {
        initialProjectsEmpty: initialProjects.status === 200 && projectList(initialProjects)?.length === 0,
        projectsAfterNavEmpty: projectsAfterNav.status === 200 && projectList(projectsAfterNav)?.length === 0,
        projectsPageShowsEmptyState: /暂无项目|还没有项目|没有项目|新建/.test(projectsDesktop.bodyText),
        desktopNoHorizontalOverflow: !projectsDesktop.hasHorizontalOverflow,
        mobileNoHorizontalOverflow: !projectsMobile.hasHorizontalOverflow,
        currentProjectSelectorShowsNoProject: projectsDesktop.visibleSelects.some(
          (select) => select.selectedText.includes("暂无项目") || select.value === ""
        ),
        canReturnToStart: /从技术想法撰写发明专利|撰写实用新型|导入已有稿件/.test(afterReturnToStart.bodyText),
        noProjectCreatedByViewingEmptyList:
          initialProjects.status === 200 &&
          projectsAfterNav.status === 200 &&
          projectList(initialProjects)?.length === 0 &&
          projectList(projectsAfterNav)?.length === 0,
        pageErrors: events.pageErrors.length,
        requestFailures: events.requestFailures.length,
        consoleErrors: events.console.filter((entry) => entry.type === "error").length,
      },
    };

    fs.writeFileSync(statePath, `${JSON.stringify(result, null, 2)}\n`);
    console.log(JSON.stringify(result.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
