const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const appUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round35-project-search");
const statePath = path.join(outDir, "round35-project-search-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  appUrl,
  apiBase,
  seedPrefix: `Round35 项目列表 ${Date.now()}`,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    apiResponses: [],
  },
  seededProjects: [],
  actions: [],
  evidence: [],
  assertions: {},
};

function shotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function fetchJson(pathname, options = {}) {
  const response = await fetch(`${apiBase}${pathname}`, {
    headers: { "content-type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    // Keep text bodies as-is.
  }
  state.events.apiResponses.push({
    method: options.method || "GET",
    path: pathname,
    status: response.status,
    bodySample: typeof body === "string" ? body.slice(0, 240) : JSON.stringify(body).slice(0, 240),
  });
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function seedProjects() {
  const names = [
    `${state.seedPrefix} Alpha 光伏支架`,
    `${state.seedPrefix} Beta 医疗导管`,
    `${state.seedPrefix} Gamma 智能仓储`,
    `${state.seedPrefix} Delta 长文本筛选验证`,
    `${state.seedPrefix} Epsilon 实用新型结构`,
    `${state.seedPrefix} Zeta 搜索入口验证`,
  ];
  for (const [index, name] of names.entries()) {
    const project = await fetchJson("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name,
        draft_text: `Round35 project-list search discovery seed ${index + 1}`,
        patent_type: index === 4 ? "utility_model" : "invention",
      }),
    });
    state.seededProjects.push(project);
  }
}

async function clickLastVisible(locator, label) {
  const count = await locator.count().catch(() => 0);
  for (let i = count - 1; i >= 0; i -= 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.click();
      state.actions.push({ label, ok: true });
      return true;
    }
  }
  state.actions.push({ label, ok: false, reason: "no visible control" });
  return false;
}

async function collectMetrics(page, label) {
  return page.evaluate(({ metricLabel, seedPrefix }) => {
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
        style.visibility !== "hidden" &&
        style.opacity !== "0"
      );
    }

    function labelFor(el) {
      const id = el.getAttribute("id");
      const explicitLabel = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
      const wrappingLabel = el.closest("label");
      return (
        explicitLabel?.innerText?.trim() ||
        wrappingLabel?.innerText?.trim() ||
        el.getAttribute("aria-label") ||
        el.getAttribute("placeholder") ||
        ""
      ).replace(/\s+/g, " ").slice(0, 180);
    }

    const bodyText = document.body.innerText || "";
    const inputs = Array.from(document.querySelectorAll("input, textarea, [contenteditable='true']"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type"),
          role: el.getAttribute("role"),
          label: labelFor(el),
          placeholder: el.getAttribute("placeholder") || "",
          value: (el.value || el.innerText || "").slice(0, 120),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      });

    const selects = Array.from(document.querySelectorAll("select"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          label: labelFor(el),
          value: el.value,
          options: Array.from(el.options).map((option) => option.textContent.trim()).slice(0, 20),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      });

    const buttons = Array.from(document.querySelectorAll("button,[role=button],a"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 180),
          ariaLabel: el.getAttribute("aria-label"),
          disabled: Boolean(el.disabled || el.getAttribute("aria-disabled") === "true"),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      })
      .filter((entry) => entry.text || entry.ariaLabel);

    const searchCandidates = [
      ...inputs.filter((entry) =>
        /搜索|查找|检索|search|query/i.test(`${entry.label} ${entry.placeholder} ${entry.role}`),
      ),
      ...buttons.filter((entry) => /搜索|查找|检索|search|query/i.test(`${entry.text} ${entry.ariaLabel || ""}`)),
    ];
    const filterCandidates = buttons.filter((entry) =>
      /全部项目|已有初稿|仅有想法|实用新型|筛选|filter/i.test(`${entry.text} ${entry.ariaLabel || ""}`),
    );

    const seededProjectNames = bodyText
      .split(/\n+/)
      .filter((line) => line.includes(seedPrefix))
      .map((line) => line.trim())
      .slice(0, 30);

    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      hasPageHorizontalOverflow:
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > window.innerWidth + 2,
      bodyTextSample: bodyText.replace(/\s+/g, " ").trim().slice(0, 1600),
      inputs,
      selects,
      buttons,
      searchCandidates,
      filterCandidates,
      seededProjectNames,
    };
  }, { metricLabel: label, seedPrefix: state.seedPrefix });
}

async function snapshot(page, name) {
  await page.screenshot({ path: shotPath(name), fullPage: true });
  const evidence = {
    name,
    screenshot: shotPath(name),
    metrics: await collectMetrics(page, name),
  };
  state.evidence.push(evidence);
  return evidence;
}

async function waitForSeededProjectsLoaded(page) {
  await page.waitForFunction(
    (prefix) => {
      const text = document.body.innerText || "";
      const optionText = Array.from(document.querySelectorAll("select option"))
        .map((option) => option.textContent || "")
        .join("\n");
      return text.includes(prefix) || optionText.includes(prefix);
    },
    state.seedPrefix,
    { timeout: 15000 },
  );
}

async function openProjectsPage(page, label) {
  await waitForSeededProjectsLoaded(page);
  const navButton = page.locator("button").filter({ hasText: /^项目$/ }).first();
  await navButton.click();
  state.actions.push({ label, ok: true });
  await page.waitForFunction(
    () => {
      const text = document.body.innerText || "";
      return /全部项目|实用新型|选择项目|删除项目/.test(text);
    },
    { timeout: 15000 },
  );
  await page.waitForTimeout(500);
}

(async () => {
  await seedProjects();

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });

  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      state.events.console.push({ type: message.type(), text: message.text() });
    }
  });
  page.on("pageerror", (error) => state.events.pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
    });
  });

  try {
    await page.goto(appUrl, { waitUntil: "domcontentloaded" });
    await waitForSeededProjectsLoaded(page);
    await page.waitForTimeout(500);
    await snapshot(page, "01-start-desktop");

    await openProjectsPage(page, "open projects desktop");
    await snapshot(page, "02-projects-desktop");

    const searchLikeInput = page.locator("input[placeholder*='搜索'], input[aria-label*='搜索'], input[placeholder*='search' i], input[aria-label*='search' i]");
    const searchLikeInputCount = await searchLikeInput.count().catch(() => 0);
    if (searchLikeInputCount > 0) {
      const first = searchLikeInput.first();
      if (await first.isVisible().catch(() => false)) {
        await first.fill("Beta");
        state.actions.push({ label: "fill visible search-like input", ok: true });
        await page.waitForTimeout(500);
        await snapshot(page, "03-projects-after-search-beta-desktop");
      }
    } else {
      state.actions.push({ label: "observe search-like input absence", ok: true, reason: "no visible search-like input" });
    }

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(700);
    await snapshot(page, "04-projects-mobile");
  } catch (error) {
    state.error = { message: error.message, stack: error.stack };
    await snapshot(page, "99-error").catch(() => {});
  } finally {
    state.assertions = {
      seededProjectCount: state.seededProjects.length,
      actionFailures: state.actions.filter((action) => !action.ok),
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      evidenceWithPageHorizontalOverflow: state.evidence
        .filter((entry) => entry.metrics.hasPageHorizontalOverflow)
        .map((entry) => entry.name),
      projectPageEvidence: state.evidence
        .filter((entry) => entry.name.includes("projects"))
        .map((entry) => ({
          name: entry.name,
          inputs: entry.metrics.inputs,
          selects: entry.metrics.selects,
          searchCandidates: entry.metrics.searchCandidates,
          filterCandidates: entry.metrics.filterCandidates,
          seededProjectNames: entry.metrics.seededProjectNames,
        })),
      hasVisibleSearchCandidate: state.evidence.some((entry) =>
        entry.metrics.searchCandidates.some((candidate) => candidate.tag === "input" || candidate.text || candidate.label),
      ),
      hasVisibleSearchInput: state.evidence.some((entry) =>
        entry.metrics.inputs.some((input) => /搜索|查找|检索|search|query/i.test(`${input.label} ${input.placeholder}`)),
      ),
    };
    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify({
      statePath,
      seededProjectCount: state.assertions.seededProjectCount,
      actionFailures: state.assertions.actionFailures.length,
      pageErrors: state.assertions.pageErrors,
      requestFailures: state.assertions.requestFailures,
      consoleErrors: state.assertions.consoleErrors,
      evidenceWithPageHorizontalOverflow: state.assertions.evidenceWithPageHorizontalOverflow,
      hasVisibleSearchCandidate: state.assertions.hasVisibleSearchCandidate,
      hasVisibleSearchInput: state.assertions.hasVisibleSearchInput,
      projectPageEvidence: state.assertions.projectPageEvidence.map((entry) => ({
        name: entry.name,
        inputCount: entry.inputs.length,
        selectCount: entry.selects.length,
        searchCandidateCount: entry.searchCandidates.length,
        filterCandidateCount: entry.filterCandidates.length,
        seededProjectNameCount: entry.seededProjectNames.length,
      })),
      error: state.error?.message || null,
    }, null, 2));
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
