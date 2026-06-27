const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBaseUrl = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round24");
const statePath = path.resolve(".gstack/qa-reports/round24-projects-stress-state.json");

fs.mkdirSync(outDir, { recursive: true });

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { status: response.status, text, json };
}

async function createProject(index, suffix) {
  const isUtility = index % 4 === 0;
  const longSegment =
    index % 5 === 0
      ? "超长项目名称连续无空格技术识别码LONGPROJECTNAMEWITHOUTBREAKPOINT".repeat(3)
      : "";
  return fetchJson(`${apiBaseUrl}/api/projects`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name: `Round24 项目 ${String(index).padStart(2, "0")} ${longSegment} ${suffix}`.trim(),
      draft_text: `用于验证 30 个历史项目列表、筛选、移动端按钮边界和当前项目选择的一段技术想法 ${index}。`,
      patent_type: isUtility ? "utility_model" : "invention",
    }),
  });
}

async function collectUiState(page, label) {
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

    function rectOf(el) {
      const rect = el.getBoundingClientRect();
      return {
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    }

    const visibleButtons = Array.from(document.querySelectorAll("button,[role=button]"))
      .filter(isVisible)
      .map((el) => ({
        text: (el.innerText || el.getAttribute("aria-label") || "").trim(),
        disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        rect: rectOf(el),
      }));
    const actionButtons = visibleButtons.filter((button) => /选择项目|删除项目|当前项目/.test(button.text));
    const filterButtons = visibleButtons.filter((button) =>
      /全部项目|已有初稿|仅有想法|实用新型/.test(button.text)
    );
    const viewportWidth = window.innerWidth;
    const overflowingElements = Array.from(document.querySelectorAll("body *"))
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        return rect.right > viewportWidth + 1 || rect.left < -1;
      })
      .slice(0, 30)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 160),
        rect: rectOf(el),
        className: typeof el.className === "string" ? el.className : "",
      }));

    return {
      label: stateLabel,
      url: location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      bodyText: document.body.innerText,
      bodyTextSample: document.body.innerText.slice(0, 3000),
      documentWidth: document.documentElement.scrollWidth,
      hasHorizontalOverflow: document.documentElement.scrollWidth > viewportWidth + 1,
      visibleButtons,
      actionButtons,
      filterButtons,
      overflowingElements,
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

function allWithinViewport(items, viewportWidth) {
  return items.every((item) => item.rect.left >= -1 && item.rect.right <= viewportWidth + 1);
}

(async () => {
  const suffix = Date.now();
  const events = { console: [], pageErrors: [], requestFailures: [], projectResponses: [] };
  const createdProjects = [];

  for (let index = 1; index <= 30; index += 1) {
    const result = await createProject(index, suffix);
    if (result.status < 200 || result.status >= 300) {
      throw new Error(`Project seed failed for ${index}: ${result.status} ${result.text}`);
    }
    createdProjects.push(result.json);
  }

  const projectsAfterSeed = await fetchJson(`${apiBaseUrl}/api/projects`);

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
      if (response.url().includes("/api/projects")) {
        events.projectResponses.push({ method: response.request().method(), url: response.url(), status: response.status() });
      }
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "项目" }).first().click();
    await page.waitForTimeout(1200);
    await page.screenshot({ path: screenshotPath("01-projects-many-desktop"), fullPage: true });
    const desktopMany = await collectUiState(page, "desktop-many");

    const utilityFilter = page.getByRole("button", { name: /实用新型\s+7/ }).first();
    if (await utilityFilter.isVisible().catch(() => false)) {
      await utilityFilter.click();
      await page.waitForTimeout(700);
    }
    await page.screenshot({ path: screenshotPath("02-projects-utility-filter-desktop"), fullPage: true });
    const desktopUtilityFilter = await collectUiState(page, "desktop-utility-filter");

    const targetProject = createdProjects[11];
    const selector = page.locator(`select:has(option[value="${targetProject.id}"])`).first();
    if (await selector.isVisible().catch(() => false)) {
      await selector.selectOption(targetProject.id);
      await page.waitForTimeout(900);
    }
    await page.screenshot({ path: screenshotPath("03-projects-after-top-select-desktop"), fullPage: true });
    const desktopAfterTopSelect = await collectUiState(page, "desktop-after-top-select");

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(900);
    await page.screenshot({ path: screenshotPath("04-projects-many-mobile"), fullPage: true });
    const mobileMany = await collectUiState(page, "mobile-many");

    const mobileSelectProject = page.getByRole("button", { name: /选择项目/ }).first();
    const mobileSelectVisible = await mobileSelectProject.isVisible().catch(() => false);
    if (mobileSelectVisible) {
      await mobileSelectProject.click();
      await page.waitForTimeout(900);
    }
    await page.screenshot({ path: screenshotPath("05-projects-mobile-after-select"), fullPage: true });
    const mobileAfterSelect = await collectUiState(page, "mobile-after-select");

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      apiBaseUrl,
      seed: {
        suffix,
        projectCount: createdProjects.length,
        utilityCount: createdProjects.filter((project) => project.patent_type === "utility_model").length,
        targetProject: { id: targetProject.id, name: targetProject.name },
      },
      events,
      screenshots: {
        desktopMany: screenshotPath("01-projects-many-desktop"),
        desktopUtilityFilter: screenshotPath("02-projects-utility-filter-desktop"),
        desktopAfterTopSelect: screenshotPath("03-projects-after-top-select-desktop"),
        mobileMany: screenshotPath("04-projects-many-mobile"),
        mobileAfterSelect: screenshotPath("05-projects-mobile-after-select"),
      },
      api: { projectsAfterSeed },
      states: {
        desktopMany,
        desktopUtilityFilter,
        desktopAfterTopSelect,
        mobileMany,
        mobileAfterSelect,
      },
      assertions: {
        seededThirtyProjects: createdProjects.length === 30,
        apiShowsThirtyProjects:
          projectsAfterSeed.status === 200 &&
          Array.isArray(projectsAfterSeed.json?.projects) &&
          projectsAfterSeed.json.projects.length === 30,
        desktopShowsThirtyProjects: /全部项目\s*30/.test(desktopMany.bodyText),
        desktopShowsSevenUtilityModels: /实用新型\s*7/.test(desktopMany.bodyText),
        desktopUtilityFilterApplied:
          /实用新型\s*7/.test(desktopUtilityFilter.bodyText) &&
          desktopUtilityFilter.bodyText.includes("Round24 项目 04"),
        topSelectorCanChooseProject:
          desktopAfterTopSelect.bodyText.includes(targetProject.name) ||
          desktopAfterTopSelect.visibleSelects.some((select) => select.value === targetProject.id),
        desktopNoHorizontalOverflow: !desktopMany.hasHorizontalOverflow,
        mobileNoDocumentHorizontalOverflow: !mobileMany.hasHorizontalOverflow && !mobileAfterSelect.hasHorizontalOverflow,
        mobileFilterChipsWithinViewport: allWithinViewport(mobileMany.filterButtons, 390),
        mobileActionButtonsWithinViewport: allWithinViewport(mobileMany.actionButtons, 390),
        mobileAfterSelectElementsWithinViewport:
          allWithinViewport(mobileAfterSelect.filterButtons, 390) &&
          allWithinViewport(mobileAfterSelect.actionButtons, 390),
        mobileSelectButtonVisibleBeforeClick: mobileSelectVisible,
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
