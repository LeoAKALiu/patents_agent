const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const appUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round34-editable");
const statePath = path.join(outDir, "round34-editable-long-text-state.json");

fs.mkdirSync(screenshotDir, { recursive: true });

const longToken = `ROUND34_EDITABLE_INPUT_NO_BREAK_${"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".repeat(18)}`;
const longChinese =
  "本段用于验证真实可编辑输入区对长中文专利文本的换行、内部滚动、可见提交按钮和移动端布局保持能力。";
const longIdea = [
  longChinese.repeat(18),
  longToken,
  "技术效果：" + longChinese.repeat(14),
].join("\n\n");
const projectName = `Round34 可编辑长文本 ${Date.now()} ${longToken}`;

const state = {
  generatedAt: new Date().toISOString(),
  appUrl,
  apiBase,
  projectName,
  longTokenLength: longToken.length,
  longIdeaLength: longIdea.length,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    mutatingRequests: [],
  },
  actions: [],
  evidence: [],
  assertions: {},
};

function shotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
}

async function clickLastVisible(locator, label, options = {}) {
  const count = await locator.count().catch(() => 0);
  for (let i = count - 1; i >= 0; i -= 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.click(options);
      state.actions.push({ label, ok: true });
      return true;
    }
  }
  state.actions.push({ label, ok: false, reason: "no visible control" });
  return false;
}

async function findFirstVisible(locator) {
  const count = await locator.count().catch(() => 0);
  for (let i = 0; i < count; i += 1) {
    const candidate = locator.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      return candidate;
    }
  }
  return null;
}

async function fillFirstVisible(locators, value, label) {
  for (const locator of locators) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < count; i += 1) {
      const candidate = locator.nth(i);
      if (await candidate.isVisible().catch(() => false)) {
        await candidate.fill(value);
        state.actions.push({ label, ok: true });
        return true;
      }
    }
  }
  state.actions.push({ label, ok: false, reason: "no visible field" });
  return false;
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

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const doc = document.documentElement;
    const body = document.body;

    const editables = Array.from(document.querySelectorAll("input, textarea, [contenteditable='true']"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        const value =
          el.tagName === "TEXTAREA" || el.tagName === "INPUT"
            ? el.value || ""
            : el.innerText || el.textContent || "";
        const parent = el.parentElement;
        const parentRect = parent?.getBoundingClientRect();
        const parentStyle = parent ? getComputedStyle(parent) : null;
        return {
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type"),
          label: labelFor(el),
          valueLength: value.length,
          hasLongToken: value.includes("ROUND34_EDITABLE_INPUT_NO_BREAK"),
          valuePreview: value.slice(0, 180),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          clientWidth: el.clientWidth,
          scrollWidth: el.scrollWidth,
          clientHeight: el.clientHeight,
          scrollHeight: el.scrollHeight,
          overflowX: style.overflowX,
          overflowY: style.overflowY,
          whiteSpace: style.whiteSpace,
          wordBreak: style.wordBreak,
          overflowWrap: style.overflowWrap,
          horizontallyOffscreen: rect.left < -1 || rect.right > viewportWidth + 1,
          internallyHorizontalOverflow: el.scrollWidth > el.clientWidth + 2,
          internallyVerticalOverflow: el.scrollHeight > el.clientHeight + 2,
          parent: parent
            ? {
                tag: parent.tagName.toLowerCase(),
                className: String(parent.className || "").slice(0, 160),
                left: Math.round(parentRect.left),
                right: Math.round(parentRect.right),
                width: Math.round(parentRect.width),
                clientWidth: parent.clientWidth,
                scrollWidth: parent.scrollWidth,
                overflowX: parentStyle.overflowX,
              }
            : null,
        };
      });

    const controls = Array.from(document.querySelectorAll("button,[role=button],select,a"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const text = (el.innerText || el.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim();
        return {
          tag: el.tagName.toLowerCase(),
          text: text.slice(0, 180),
          disabled: Boolean(el.disabled || el.getAttribute("aria-disabled") === "true"),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          top: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          horizontallyOffscreen: rect.left < -1 || rect.right > viewportWidth + 1,
        };
      })
      .filter((entry) => entry.text);

    const overflowers = Array.from(document.querySelectorAll("body *"))
      .filter(isVisible)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        const text = (
          el.tagName === "INPUT" || el.tagName === "TEXTAREA"
            ? el.value || el.getAttribute("placeholder") || ""
            : el.innerText || el.textContent || el.getAttribute("aria-label") || ""
        )
          .replace(/\s+/g, " ")
          .trim();
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
          overflowX: style.overflowX,
          whiteSpace: style.whiteSpace,
          hasLongToken: text.includes("ROUND34_EDITABLE_INPUT_NO_BREAK"),
        };
      })
      .filter((entry) => entry.text && (entry.left < -2 || entry.right > viewportWidth + 2 || entry.scrollWidth > entry.clientWidth + 2))
      .slice(0, 120);

    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: viewportWidth, height: viewportHeight },
      documentScrollWidth: doc.scrollWidth,
      bodyScrollWidth: body.scrollWidth,
      hasPageHorizontalOverflow: Math.max(doc.scrollWidth, body.scrollWidth) > viewportWidth + 2,
      bodyTextSample: (body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 1200),
      editables,
      controls,
      overflowers,
    };
  }, label);
}

async function snapshot(page, name) {
  await page.screenshot({ path: shotPath(name), fullPage: true });
  const metrics = await collectMetrics(page, name);
  const evidence = {
    name,
    screenshot: shotPath(name),
    metrics,
  };
  state.evidence.push(evidence);
  return evidence;
}

async function tryOpenStart(page) {
  await page.goto(appUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(900);
  if (!(await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).last().isVisible().catch(() => false))) {
    await clickLastVisible(page.getByRole("button", { name: "开始" }), "open start nav").catch(() => false);
    await page.waitForTimeout(400);
  }
}

async function openInventionEntry(page) {
  await tryOpenStart(page);
  const returnButton = await findFirstVisible(page.getByRole("button", { name: /返回三选一/ }));
  if (returnButton) {
    await returnButton.click();
    state.actions.push({ label: "return to three choices", ok: true });
    await page.waitForTimeout(300);
  }
  await clickLastVisible(page.getByRole("button", { name: "开始" }), "open start nav").catch(() => false);
  await page.waitForTimeout(300);
  await clickLastVisible(page.getByRole("button", { name: /从技术想法撰写发明专利/ }), "open invention create form");
  await page.waitForTimeout(400);
}

async function runMobileEditableForm(browser) {
  const mobilePage = await browser.newPage({ viewport: { width: 390, height: 1100 } });
  mobilePage.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      state.events.console.push({ type: message.type(), text: message.text(), page: "mobile" });
    }
  });
  mobilePage.on("pageerror", (error) => {
    state.events.pageErrors.push(`[mobile] ${error.message}`);
  });
  mobilePage.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
      page: "mobile",
    });
  });
  mobilePage.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      state.events.mutatingRequests.push({ method: request.method(), url: request.url(), ts: Date.now(), page: "mobile" });
    }
  });

  await openInventionEntry(mobilePage);
  await snapshot(mobilePage, "06-create-form-empty-mobile");
  await fillFirstVisible(
    [mobilePage.getByLabel("项目名称", { exact: true }), mobilePage.locator("input:not([type='hidden'])")],
    `Round34 移动端可编辑长文本 ${Date.now()} ${longToken}`,
    "fill mobile long project name",
  );
  await fillFirstVisible(
    [mobilePage.getByLabel("一句话想法", { exact: true }), mobilePage.locator("textarea")],
    longIdea,
    "fill mobile long idea textarea",
  );
  await mobilePage.waitForTimeout(500);
  await snapshot(mobilePage, "07-create-form-filled-mobile");
  await mobilePage.close();
}

(async () => {
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
  page.on("pageerror", (error) => {
    state.events.pageErrors.push(error.message);
  });
  page.on("requestfailed", (request) => {
    state.events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || "unknown",
    });
  });
  page.on("request", (request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
      state.events.mutatingRequests.push({ method: request.method(), url: request.url(), ts: Date.now() });
    }
  });

  try {
    await tryOpenStart(page);
    await snapshot(page, "01-start-desktop");

    await openInventionEntry(page);
    await snapshot(page, "02-create-form-empty-desktop");

    await fillFirstVisible(
      [page.getByLabel("项目名称", { exact: true }), page.locator("input:not([type='hidden'])")],
      projectName,
      "fill long project name",
    );
    await fillFirstVisible(
      [page.getByLabel("一句话想法", { exact: true }), page.locator("textarea")],
      longIdea,
      "fill long idea textarea",
    );
    await page.waitForTimeout(500);
    await snapshot(page, "03-create-form-filled-desktop");

    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.waitForTimeout(400);
    await clickLastVisible(page.getByRole("button", { name: "创建并继续" }), "submit long create form");
    await page.waitForTimeout(1500);
    await snapshot(page, "04-after-create-desktop");

    const projectsResponse = await fetch(`${apiBase}/api/projects`);
    const projects = await projectsResponse.json();
    const projectList = Array.isArray(projects) ? projects : projects.projects || [];
    state.createdProject = projectList.find((project) => project.name === projectName) || null;

    await runMobileEditableForm(browser);
  } catch (error) {
    state.error = { message: error.message, stack: error.stack };
    await snapshot(page, "99-error").catch(() => {});
  } finally {
    state.assertions = {
      actionFailures: state.actions.filter((action) => !action.ok),
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
      createdProjectId: state.createdProject?.id || null,
      evidenceWithPageHorizontalOverflow: state.evidence
        .filter((entry) => entry.metrics.hasPageHorizontalOverflow)
        .map((entry) => entry.name),
      visibleEditableStates: state.evidence
        .filter((entry) => entry.metrics.editables.length > 0)
        .map((entry) => ({
          name: entry.name,
          editables: entry.metrics.editables.map((editable) => ({
            tag: editable.tag,
            type: editable.type,
            label: editable.label,
            valueLength: editable.valueLength,
            hasLongToken: editable.hasLongToken,
            width: editable.width,
            scrollWidth: editable.scrollWidth,
            height: editable.height,
            scrollHeight: editable.scrollHeight,
            horizontallyOffscreen: editable.horizontallyOffscreen,
            internallyHorizontalOverflow: editable.internallyHorizontalOverflow,
            internallyVerticalOverflow: editable.internallyVerticalOverflow,
            overflowX: editable.overflowX,
            overflowY: editable.overflowY,
            whiteSpace: editable.whiteSpace,
            overflowWrap: editable.overflowWrap,
          })),
        })),
      longTokenVisibleInEditable: state.evidence.some((entry) =>
        entry.metrics.editables.some((editable) => editable.hasLongToken),
      ),
      offscreenLongTokenEditables: state.evidence
        .flatMap((entry) =>
          entry.metrics.editables
            .filter((editable) => editable.hasLongToken && editable.horizontallyOffscreen)
            .map((editable) => ({ state: entry.name, editable })),
        ),
      abortedAgentDoctorRequests: state.events.requestFailures.filter((entry) =>
        entry.url.includes("/api/agents/doctor") && entry.failure.includes("ERR_ABORTED"),
      ).length,
    };

    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify({
      statePath,
      projectId: state.createdProject?.id || null,
      longTokenLength: state.longTokenLength,
      longIdeaLength: state.longIdeaLength,
      actionFailures: state.assertions.actionFailures.length,
      pageErrors: state.assertions.pageErrors,
      requestFailures: state.assertions.requestFailures,
      consoleErrors: state.assertions.consoleErrors,
      evidenceWithPageHorizontalOverflow: state.assertions.evidenceWithPageHorizontalOverflow,
      longTokenVisibleInEditable: state.assertions.longTokenVisibleInEditable,
      offscreenLongTokenEditables: state.assertions.offscreenLongTokenEditables.length,
      visibleEditableStateCount: state.assertions.visibleEditableStates.length,
      abortedAgentDoctorRequests: state.assertions.abortedAgentDoctorRequests,
      error: state.error?.message || null,
    }, null, 2));
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
