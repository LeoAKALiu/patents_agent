const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBaseUrl = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round37-external-draft-mode");
const statePath = path.join(outDir, "round37-external-draft-mode-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

function screenshotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function fetchJson(pathname, options = {}) {
  const response = await fetch(`${apiBaseUrl}${pathname}`, {
    headers: {
      "content-type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    // Keep text for failures.
  }
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function collectState(page, label) {
  return page.evaluate((stateLabel) => {
    const bodyText = document.body.innerText || "";
    const select = document.querySelector("select.project-select-control") || document.querySelector("select");
    return {
      label: stateLabel,
      url: location.href,
      bodyTextSample: bodyText.slice(0, 5000),
      hasExternalHeading: bodyText.includes("导入外部专利初稿"),
      hasSaveExternalDraft: bodyText.includes("保存外部初稿"),
      hasUploadExternalDraft: bodyText.includes("上传外部初稿"),
      hasExternalQueue: bodyText.includes("来源队列"),
      hasInventionStepPanel: bodyText.includes("确认发明点与护城河"),
      hasSupplementalUpload: bodyText.includes("上传补充材料"),
      selectedProjectText: select ? select.options[select.selectedIndex]?.text || "" : "",
      selectedProjectValue: select ? select.value : "",
    };
  }, label);
}

(async () => {
  const state = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    apiBaseUrl,
    project: null,
    events: { console: [], pageErrors: [], requestFailures: [] },
    screenshots: {},
    states: {},
    assertions: {},
  };

  const suffix = Date.now();
  state.project = await fetchJson("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: `Round37 外部稿入口保持 ${suffix}`,
      draft_text: "用于验证第三入口选择已有项目后仍保持外部初稿导入模式的一段技术想法。",
      patent_type: "invention",
    }),
  });

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("console", (message) => state.events.console.push({ type: message.type(), text: message.text() }));
    page.on("pageerror", (error) => state.events.pageErrors.push({ message: error.message, stack: error.stack }));
    page.on("requestfailed", (request) => {
      state.events.requestFailures.push({
        method: request.method(),
        url: request.url(),
        failure: request.failure() && request.failure().errorText,
      });
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: /导入已有稿件进行润色提升/ }).first().click();
    await page.waitForTimeout(900);

    state.screenshots.beforeProjectSelect = screenshotPath("01-before-project-select");
    await page.screenshot({ path: state.screenshots.beforeProjectSelect, fullPage: true });
    state.states.beforeProjectSelect = await collectState(page, "before-project-select");

    await page.locator("select.project-select-control").first().selectOption(state.project.id);
    await page.waitForTimeout(1200);

    state.screenshots.afterProjectSelect = screenshotPath("02-after-project-select");
    await page.screenshot({ path: state.screenshots.afterProjectSelect, fullPage: true });
    state.states.afterProjectSelect = await collectState(page, "after-project-select");

    state.assertions = {
      beforeShowsExternalIntake: state.states.beforeProjectSelect.hasExternalHeading,
      afterShowsExternalIntake:
        state.states.afterProjectSelect.hasExternalHeading &&
        state.states.afterProjectSelect.hasSaveExternalDraft &&
        state.states.afterProjectSelect.hasUploadExternalDraft &&
        state.states.afterProjectSelect.hasExternalQueue,
      afterKeepsSelectedProject: state.states.afterProjectSelect.selectedProjectValue === state.project.id,
      afterDoesNotJumpToInventionPanel: !state.states.afterProjectSelect.hasInventionStepPanel,
      afterDoesNotShowSupplementalUpload: !state.states.afterProjectSelect.hasSupplementalUpload,
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
    };

    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify(state.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);

    const failed = Object.entries(state.assertions).filter(([key, value]) =>
      key === "pageErrors" || key === "requestFailures" || key === "consoleErrors" ? value !== 0 : value !== true
    );
    if (failed.length > 0) {
      throw new Error(`round37 external draft mode assertions failed: ${JSON.stringify(failed)}`);
    }
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
