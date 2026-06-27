const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const appUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round33");
const statePath = path.join(outDir, "round33-long-editor-report-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  appUrl,
  apiBase,
  projectName: `Round33 长编辑报告 ${Date.now()}`,
  seeded: {},
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    apiResponses: [],
  },
  actions: [],
  evidence: [],
  assertions: {},
};

function shotPath(name) {
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
    // Keep text bodies for markdown exports.
  }
  state.events.apiResponses.push({
    method: options.method || "GET",
    path: pathname,
    status: response.status,
    bodySample: typeof body === "string" ? body.slice(0, 260) : JSON.stringify(body).slice(0, 260),
  });
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function seedLongReportProject() {
  const longToken = `ROUND33_EDITOR_REPORT_NO_BREAK_${"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".repeat(18)}`;
  const longChinese =
    "本段用于验证专利编辑区和生成报告区对长中文技术文本的换行滚动能力，界面应保持标题、操作按钮、正文、报告卡片和移动端底部导航都可读。";
  const claims = [
    `1. 一种长文本编辑和报告验证方法，其特征在于，包括：在专利文本编辑区输入包含连续技术标识符 ${longToken} 的权利要求。`,
    `2. 根据权利要求1所述的方法，其中，所述连续技术标识符用于模拟型号、哈希、设备编号、公式串或客户粘贴的不可断行文本。`,
    `3. 根据权利要求1所述的方法，其中，报告区域包含多个长中文段落：${longChinese.repeat(14)}`,
  ].join("\n");
  const description = [
    "技术领域：" + longChinese.repeat(8),
    "背景技术：" + longChinese.repeat(10),
    `发明内容：系统应在编辑区和生成报告区处理 ${longToken}，避免正文被不可见父容器裁掉。`,
    "具体实施方式：" + Array.from({ length: 14 }, (_, index) => `实施例${index + 1}：${longChinese.repeat(5)}`).join("\n"),
  ].join("\n\n");

  const project = await fetchJson("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: state.projectName,
      draft_text: "Round33 long editor/report setup",
      patent_type: "invention",
    }),
  });
  const projectId = project.id;

  const source = await fetchJson(`/api/projects/${projectId}/external-drafts`, {
    method: "POST",
    body: JSON.stringify({
      source_type: "pasted_text",
      file_name: "round33-long-editor-report.md",
      text: `# ${state.projectName}\n\n## 摘要\n${longChinese.repeat(4)}\n\n## 权利要求\n${claims}\n\n## 说明书\n${description}\n\n## 附图说明\n图1为长文本编辑和报告验证流程图。`,
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
      abstract: longChinese.repeat(7),
      claims,
      description,
      drawing_description: `图1为长文本编辑和报告验证流程图，图中标注 ${longToken}。`,
    }),
  });

  const grantability = await fetchJson(`/api/projects/${projectId}/grantability-reports`, {
    method: "POST",
    body: "{}",
  }).catch((error) => ({ error: error.message }));
  const claimDefense = await fetchJson(`/api/projects/${projectId}/claim-defense-worksheets`, {
    method: "POST",
    body: "{}",
  }).catch((error) => ({ error: error.message }));
  const completion = await fetchJson(`/api/projects/${projectId}/completion-runs`, {
    method: "POST",
    body: "{}",
  }).catch((error) => ({ error: error.message }));

  state.seeded = {
    projectId,
    sourceId,
    intakeRunId,
    grantabilityId: grantability.id || null,
    grantabilityError: grantability.error || null,
    claimDefenseId: claimDefense.id || null,
    claimDefenseError: claimDefense.error || null,
    completionRunId: completion.id || null,
    completionError: completion.error || null,
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

function visibleControlSelector() {
  return "button,[role=button],a,summary,select,input,textarea";
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
        const text = (el.innerText || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "")
          .replace(/\s+/g, " ")
          .trim();
        return {
          tag: el.tagName.toLowerCase(),
          text: text.slice(0, 260),
          className: String(el.className || "").slice(0, 180),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          overflowX: getComputedStyle(el).overflowX,
          whiteSpace: getComputedStyle(el).whiteSpace,
        };
      })
      .filter((entry) => entry.text && (entry.right > window.innerWidth + 2 || entry.left < -2 || entry.scrollWidth > entry.clientWidth + 2))
      .slice(0, 100);

    const longTokenElements = Array.from(document.querySelectorAll("body *"))
      .filter((el) => {
        const text = el.tagName === "TEXTAREA" || el.tagName === "INPUT" ? el.value || "" : el.innerText || "";
        return text.includes("ROUND33_EDITOR_REPORT_NO_BREAK");
      })
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const text = (el.tagName === "TEXTAREA" || el.tagName === "INPUT" ? el.value || "" : el.innerText || "")
          .replace(/\s+/g, " ")
          .trim();
        return {
          tag: el.tagName.toLowerCase(),
          className: String(el.className || "").slice(0, 180),
          visible: isVisible(el),
          text: text.slice(0, 320),
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
      .slice(0, 60);

    const textControls = Array.from(document.querySelectorAll("textarea,input[type='text'],input:not([type])"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          placeholder: el.getAttribute("placeholder") || "",
          valueLength: (el.value || "").length,
          valueSample: (el.value || "").slice(0, 200),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          scrollLeft: el.scrollLeft,
          overflowX: getComputedStyle(el).overflowX,
          whiteSpace: getComputedStyle(el).whiteSpace,
        };
      });

    const controls = Array.from(document.querySelectorAll("button,[role=button],a,summary,select,input,textarea"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          text: (el.innerText || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, 180),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
          left: Math.round(rect.left),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        };
      })
      .slice(0, 100);

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
      longTokenVisible: bodyText.includes("ROUND33_EDITOR_REPORT_NO_BREAK"),
      overflowers,
      longTokenElements,
      textControls,
      controls,
    };
  }, label);
}

async function evidence(page, name) {
  const screenshot = shotPath(name);
  await page.screenshot({ path: screenshot, fullPage: true });
  const metrics = await collectMetrics(page, name);
  state.evidence.push({ name, screenshot, metrics });
  return metrics;
}

async function action(label, fn) {
  try {
    await fn();
    state.actions.push({ label, ok: true });
  } catch (error) {
    state.actions.push({ label, ok: false, message: error.message });
  }
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
    const hasProject = await select
      .evaluate((el, name) => Array.from(el.options).some((option) => option.textContent === name), state.projectName)
      .catch(() => false);
    if (hasProject) {
      await select.selectOption({ label: state.projectName });
      await page.waitForFunction((name) => document.body.innerText.includes(name), state.projectName, { timeout: 15000 });
      await page.waitForTimeout(1200);
      return;
    }
  }
  throw new Error("Could not find seeded project in any select.");
}

async function clickButtonContaining(page, text) {
  const buttons = page.getByRole("button").filter({ hasText: text });
  const count = await buttons.count();
  for (let i = 0; i < count; i += 1) {
    const candidate = buttons.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 5000 });
      await page.waitForTimeout(1200);
      return;
    }
  }
  throw new Error(`No visible button containing: ${text}`);
}

async function clickVisibleText(page, text) {
  const locator = page.getByText(text, { exact: false });
  const count = await locator.count();
  for (let i = 0; i < count; i += 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 5000 });
      await page.waitForTimeout(1000);
      return;
    }
  }
  throw new Error(`No visible text target: ${text}`);
}

async function returnToExpertTools(page) {
  const body = await page.locator("body").innerText();
  if (body.includes("当前工具") && body.includes("返回向导")) {
    await clickVisibleText(page, "返回向导");
    await page.waitForTimeout(700);
  }
  await clickVisibleText(page, "专家工具");
}

async function fillVisibleTextAreaWithLongText(page) {
  const longText = [
    `Round33 编辑区长文本 ${state.seeded.longToken}`,
    "本段用于验证可编辑文本区域能否在输入长中文和不可断行 token 后保持按钮、标签和正文可达。".repeat(20),
    state.seeded.longToken,
  ].join("\n\n");
  const textareas = page.locator("textarea");
  const count = await textareas.count();
  for (let i = 0; i < count; i += 1) {
    const candidate = textareas.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.fill(longText);
      await page.waitForTimeout(700);
      return true;
    }
  }
  const editable = page.locator("[contenteditable='true']");
  const editableCount = await editable.count();
  for (let i = 0; i < editableCount; i += 1) {
    const candidate = editable.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.fill(longText);
      await page.waitForTimeout(700);
      return true;
    }
  }
  return false;
}

async function main() {
  await seedLongReportProject();

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

    await action("select seeded project", async () => selectSeededProject(page));
    await evidence(page, "02-project-selected");

    await action("open expert tools", async () => clickVisibleText(page, "专家工具"));
    await evidence(page, "03-expert-tools");

    await action("open grantability report", async () => clickButtonContaining(page, "授权前景"));
    await evidence(page, "04-grantability-report");

    await action("return and open claim defense", async () => {
      await returnToExpertTools(page);
      await clickButtonContaining(page, "权利要求防线");
    });
    await evidence(page, "05-claim-defense-report");

    await action("return and open completion report", async () => {
      await returnToExpertTools(page);
      await clickButtonContaining(page, "初稿完善");
    });
    await evidence(page, "06-completion-report");

    await action("return and open step writing editor", async () => {
      await returnToExpertTools(page);
      await clickButtonContaining(page, "分步撰写");
    });
    await evidence(page, "07-step-writing-editor-empty");

    await action("fill visible editor long text if present", async () => {
      const filled = await fillVisibleTextAreaWithLongText(page);
      state.seeded.editorFilled = filled;
    });
    await evidence(page, "08-step-writing-editor-long-text");

    await page.setViewportSize({ width: 390, height: 1100 });
    await page.waitForTimeout(800);
    await evidence(page, "09-step-writing-editor-mobile");

    if (state.seeded.completionRunId) {
      await page.goto(`${apiBase}/api/projects/${state.seeded.projectId}/completion-runs/${state.seeded.completionRunId}/report.md`, {
        waitUntil: "domcontentloaded",
      });
      await page.waitForTimeout(600);
      await evidence(page, "10-completion-report-md-mobile");
    }

    if (state.seeded.grantabilityId) {
      await page.goto(`${apiBase}/api/projects/${state.seeded.projectId}/grantability-reports/${state.seeded.grantabilityId}/export.md`, {
        waitUntil: "domcontentloaded",
      });
      await page.waitForTimeout(600);
      await evidence(page, "11-grantability-export-md-mobile");
    }
  } finally {
    state.assertions = {
      seededProjectId: state.seeded.projectId || null,
      grantabilityId: state.seeded.grantabilityId || null,
      claimDefenseId: state.seeded.claimDefenseId || null,
      completionRunId: state.seeded.completionRunId || null,
      editorFilled: Boolean(state.seeded.editorFilled),
      actionFailures: state.actions.filter((entry) => !entry.ok),
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      appEvidenceWithHorizontalOverflow: state.evidence
        .filter((entry) => !entry.name.includes("-md-") && !entry.name.includes("export-md"))
        .filter((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.overflowers.length > 0)
        .map((entry) => entry.name),
      markdownEvidenceWithHorizontalOverflow: state.evidence
        .filter((entry) => entry.name.includes("-md-") || entry.name.includes("export-md"))
        .filter((entry) => entry.metrics.hasHorizontalOverflow || entry.metrics.overflowers.length > 0)
        .map((entry) => entry.name),
      longTokenVisibleInApp: state.evidence.some((entry) => !entry.name.includes("-md-") && entry.metrics.longTokenVisible),
      longTokenVisibleInMarkdown: state.evidence.some((entry) => entry.name.includes("-md-") && entry.metrics.longTokenVisible),
      textControlsObserved: state.evidence.reduce((count, entry) => count + (entry.metrics.textControls?.length || 0), 0),
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
