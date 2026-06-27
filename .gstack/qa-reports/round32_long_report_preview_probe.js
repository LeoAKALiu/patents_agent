const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const appUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round32");
const statePath = path.join(outDir, "round32-long-report-preview-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  appUrl,
  apiBase,
  projectName: `Round32 长报告预览 ${Date.now()}`,
  seeded: {},
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    apiResponses: [],
  },
  evidence: [],
  actions: [],
  assertions: {},
};

function screenshotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function fetchJson(pathname, options = {}) {
  const response = await fetch(`${apiBase}${pathname}`, {
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
    // Keep text body for export endpoints or non-JSON errors.
  }
  state.events.apiResponses.push({
    method: options.method || "GET",
    path: pathname,
    status: response.status,
    bodySample: typeof body === "string" ? body.slice(0, 300) : JSON.stringify(body).slice(0, 300),
  });
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function seedLongOfficialDraft() {
  const longToken = `ROUND32_NO_BREAK_TECH_${"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".repeat(18)}`;
  const longChinese =
    "本段用于验证专利正式稿报告和导出预览区域对长中文技术文本的换行滚动能力，界面应保持当前项目选择器、二级导航、报告正文和导出提示都可读。";
  const claims = [
    `1. 一种长文本报告预览测试方法，其特征在于，包括：获取目标专利文本，生成包含连续技术标识符 ${longToken} 的正式稿报告；`,
    `2. 根据权利要求1所述的方法，其中，所述连续技术标识符用于模拟客户粘贴的型号、哈希值、设备编号或未断行公式。`,
    `3. 根据权利要求1所述的方法，其中，报告正文包含 ${longChinese.repeat(12)}`,
  ].join("\n");
  const description = [
    "技术领域：" + longChinese.repeat(8),
    "背景技术：" + longChinese.repeat(12),
    `发明内容：系统需要处理 ${longToken}，并在导出预览、正式稿编译页和成熟度报告页中避免不可达横向内容。`,
    "具体实施方式：" + Array.from({ length: 18 }, (_, index) => `实施例${index + 1}：${longChinese.repeat(6)}`).join("\n"),
  ].join("\n\n");

  const project = await fetchJson("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: state.projectName,
      draft_text: "Round32 long report preview setup",
      patent_type: "invention",
    }),
  });
  const projectId = project.id;

  const source = await fetchJson(`/api/projects/${projectId}/external-drafts`, {
    method: "POST",
    body: JSON.stringify({
      source_type: "pasted_text",
      file_name: "round32-long-report.md",
      text: `# ${state.projectName}\n\n## 摘要\n${longChinese.repeat(4)}\n\n## 权利要求\n${claims}\n\n## 说明书\n${description}\n\n## 附图说明\n图1为长文本报告预览流程图。`,
    }),
  });
  const sourceId = source.id;

  const intakeRun = await fetchJson(`/api/projects/${projectId}/external-drafts/${sourceId}/intake-runs`, {
    method: "POST",
    body: "{}",
  });
  const intakeRunId = intakeRun.id;

  const confirmed = await fetchJson(`/api/projects/${projectId}/external-draft-intake-runs/${intakeRunId}/confirm`, {
    method: "POST",
    body: JSON.stringify({
      title: `${state.projectName} ${longToken}`,
      abstract: longChinese.repeat(8),
      claims,
      description,
      drawing_description: `图1为长文本报告预览流程图，图中标注 ${longToken}。`,
    }),
  });

  const readiness = await fetchJson(`/api/projects/${projectId}/filing-readiness`, {
    method: "POST",
    body: "{}",
  });
  const compile = await fetchJson(`/api/projects/${projectId}/official-compile-runs`, {
    method: "POST",
    body: "{}",
  });

  state.seeded = {
    projectId,
    sourceId,
    intakeRunId,
    readinessId: readiness.id,
    compileRunId: compile.id,
    longToken,
    longTokenLength: longToken.length,
    confirmedPackageLengths: {
      title: confirmed.parsed_package?.title?.length || 0,
      abstract: confirmed.parsed_package?.abstract?.length || 0,
      claims: confirmed.parsed_package?.claims?.length || 0,
      description: confirmed.parsed_package?.description?.length || 0,
      drawing_description: confirmed.parsed_package?.drawing_description?.length || 0,
    },
  };
}

async function collectMetrics(page, label) {
  return page.evaluate((metricLabel) => {
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

    const bodyText = document.body.innerText || "";
    const overflowers = Array.from(document.querySelectorAll("body *"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const text = (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
        return {
          tag: el.tagName.toLowerCase(),
          text: text.slice(0, 220),
          className: String(el.className || "").slice(0, 160),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          overflowX: getComputedStyle(el).overflowX,
        };
      })
      .filter((entry) => entry.text && (entry.right > window.innerWidth + 2 || entry.left < -2 || entry.scrollWidth > entry.clientWidth + 2))
      .slice(0, 80);

    const longTokenElements = Array.from(document.querySelectorAll("body *"))
      .filter((el) => (el.innerText || "").includes("ROUND32_NO_BREAK_TECH"))
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          className: String(el.className || "").slice(0, 160),
          visible: isVisible(el),
          text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 260),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          bottom: Math.round(rect.bottom),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          overflowX: getComputedStyle(el).overflowX,
          whiteSpace: getComputedStyle(el).whiteSpace,
        };
      })
      .slice(0, 40);

    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      hasHorizontalOverflow:
        document.documentElement.scrollWidth > window.innerWidth + 2 || document.body.scrollWidth > window.innerWidth + 2,
      bodyTextLength: bodyText.length,
      bodyTextSample: bodyText.slice(0, 5000),
      longTokenVisible: bodyText.includes("ROUND32_NO_BREAK_TECH"),
      longTokenElements,
      overflowers,
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button],a,summary,select"))
        .filter(isVisible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 160),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        }))
        .slice(0, 80),
    };
  }, label);
}

async function evidence(page, name) {
  const screenshot = screenshotPath(name);
  await page.screenshot({ path: screenshot, fullPage: true });
  const metrics = await collectMetrics(page, name);
  state.evidence.push({ name, screenshot, metrics });
  return metrics;
}

async function recordAction(label, fn) {
  try {
    await fn();
    state.actions.push({ label, ok: true });
  } catch (error) {
    state.actions.push({ label, ok: false, message: error.message });
  }
}

async function clickVisibleText(page, text) {
  const locator = page.getByText(text, { exact: false });
  const count = await locator.count();
  for (let i = 0; i < count; i += 1) {
    const item = locator.nth(i);
    if (await item.isVisible().catch(() => false)) {
      await item.scrollIntoViewIfNeeded().catch(() => {});
      await item.click({ timeout: 5000 });
      await page.waitForTimeout(900);
      return;
    }
  }
  throw new Error(`No visible text target: ${text}`);
}

async function clickVisibleButtonContaining(page, text) {
  const buttons = page.getByRole("button").filter({ hasText: text });
  const count = await buttons.count();
  for (let i = 0; i < count; i += 1) {
    const item = buttons.nth(i);
    if (await item.isVisible().catch(() => false)) {
      await item.scrollIntoViewIfNeeded().catch(() => {});
      await item.click({ timeout: 5000 });
      await page.waitForTimeout(1200);
      return;
    }
  }
  throw new Error(`No visible button containing: ${text}`);
}

async function selectSeededProject(page) {
  await page.waitForFunction(
    (name) => Array.from(document.querySelectorAll("select option")).some((option) => option.textContent === name),
    state.projectName,
    { timeout: 15000 },
  );
  const selects = page.locator("select");
  const count = await selects.count();
  for (let i = 0; i < count; i += 1) {
    const select = selects.nth(i);
    const hasProject = await select.evaluate((el, name) => Array.from(el.options).some((option) => option.textContent === name), state.projectName).catch(() => false);
    if (hasProject) {
      await select.selectOption({ label: state.projectName });
      await page.waitForFunction(
        (name) => document.body.innerText.includes(name) && !document.body.innerText.includes("当前项目\n未选择"),
        state.projectName,
        { timeout: 15000 },
      );
      await page.waitForTimeout(1200);
      return;
    }
  }
  throw new Error("Could not find seeded project in any select.");
}

async function main() {
  await seedLongOfficialDraft();

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  page.on("console", (message) => {
    state.events.console.push({ type: message.type(), text: message.text().slice(0, 1200) });
  });
  page.on("pageerror", (error) => {
    state.events.pageErrors.push({ message: error.message, stack: error.stack });
  });
  page.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
    });
  });

  try {
    await page.goto(appUrl, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
      (name) => Array.from(document.querySelectorAll("select option")).some((option) => option.textContent === name),
      state.projectName,
      { timeout: 15000 },
    );
    await page.waitForTimeout(600);
    await evidence(page, "01-app-loaded");

    await recordAction("select seeded project", async () => selectSeededProject(page));
    await evidence(page, "02-project-selected");

    await recordAction("open expert tools", async () => {
      const expertButton = page.getByRole("button", { name: /专家工具/ });
      if ((await expertButton.count()) > 0 && await expertButton.first().isVisible().catch(() => false)) {
        await expertButton.first().click();
        await page.waitForTimeout(1200);
        return;
      }
      await clickVisibleText(page, "专家工具");
    });
    await evidence(page, "03-expert-tools");

    await recordAction("open filing readiness tool card", async () => clickVisibleButtonContaining(page, "提交成熟度"));
    await evidence(page, "04-filing-readiness-tool");

    await recordAction("return expert tools", async () => clickVisibleText(page, "返回向导"));
    await recordAction("open expert tools again", async () => clickVisibleText(page, "专家工具"));
    await recordAction("open export files tool card", async () => clickVisibleButtonContaining(page, "导出文件"));
    await evidence(page, "05-export-files-tool");

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(800);
    await evidence(page, "06-export-files-mobile");

    await page.goto(`${apiBase}/api/projects/${state.seeded.projectId}/official-compile-runs/${state.seeded.compileRunId}/report.md`, {
      waitUntil: "domcontentloaded",
    });
    await page.waitForTimeout(700);
    await evidence(page, "07-official-compile-report-md-mobile");

    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.waitForTimeout(500);
    await evidence(page, "08-official-compile-report-md-desktop");

    await page.goto(`${apiBase}/api/projects/${state.seeded.projectId}/filing-readiness/${state.seeded.readinessId}/export.md`, {
      waitUntil: "domcontentloaded",
    });
    await page.waitForTimeout(700);
    await evidence(page, "09-filing-readiness-export-md-desktop");
  } finally {
    state.assertions = {
      seededProjectId: state.seeded.projectId || null,
      compileRunId: state.seeded.compileRunId || null,
      readinessId: state.seeded.readinessId || null,
      actionFailures: state.actions.filter((action) => !action.ok),
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      appEvidenceWithHorizontalOverflow: state.evidence
        .filter((entry) => !entry.name.includes("md") && entry.name !== "01-app-loaded")
        .filter((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.overflowers.length > 0)
        .map((entry) => entry.name),
      markdownPreviewWithHorizontalOverflow: state.evidence
        .filter((entry) => entry.name.includes("md"))
        .filter((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.overflowers.length > 0)
        .map((entry) => entry.name),
      longTokenVisibleInApp: state.evidence.some((entry) => !entry.name.includes("md") && entry.metrics.longTokenVisible),
      longTokenVisibleInMarkdown: state.evidence.some((entry) => entry.name.includes("md") && entry.metrics.longTokenVisible),
    };

    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify(state.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);
    await browser.close().catch(() => {});
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
