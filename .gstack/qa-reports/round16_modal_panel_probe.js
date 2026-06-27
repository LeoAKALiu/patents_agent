const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round16");
const statePath = path.resolve(".gstack/qa-reports/round16-modal-panel-state.json");

fs.mkdirSync(outDir, { recursive: true });

const now = new Date().toISOString().replace(/[:.]/g, "-");
const projectName = `Round16 面板回归 ${now.slice(0, 19)}`;
const idea =
  "一种面向专利撰写软件的面板关闭与重开测试方案，用于验证专家工具、提示词详情、材料详情和导航返回控件在连续点击、Escape 关闭和重新打开后的状态一致性。";

function cleanName(value) {
  return value.replace(/[^\w\u4e00-\u9fa5-]+/g, "-").replace(/-+/g, "-").slice(0, 80);
}

async function saveScreenshot(page, name) {
  const filePath = path.join(outDir, `${cleanName(name)}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

async function visibleLocatorCount(locator) {
  const count = await locator.count();
  let visible = 0;
  for (let i = 0; i < count; i += 1) {
    if (await locator.nth(i).isVisible().catch(() => false)) visible += 1;
  }
  return visible;
}

async function firstVisible(page, label) {
  const exact = page.getByText(label, { exact: true });
  const count = await exact.count();
  for (let i = 0; i < count; i += 1) {
    const item = exact.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  const fuzzy = page.getByText(label);
  const fuzzyCount = await fuzzy.count();
  for (let i = 0; i < fuzzyCount; i += 1) {
    const item = fuzzy.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function firstVisibleExact(page, label) {
  const exact = page.getByText(label, { exact: true });
  const count = await exact.count();
  for (let i = 0; i < count; i += 1) {
    const item = exact.nth(i);
    if (await item.isVisible().catch(() => false)) return item;
  }
  return null;
}

async function clickLabel(page, label) {
  const item = await firstVisible(page, label);
  if (!item) return false;
  await item.scrollIntoViewIfNeeded();
  await item.click({ timeout: 5000 });
  await page.waitForTimeout(500);
  return true;
}

async function domState(page, label) {
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
        style.visibility !== "hidden" &&
        style.opacity !== "0"
      );
    }

    const dialogs = Array.from(
      document.querySelectorAll("[role=dialog],[aria-modal=true],dialog[open]")
    )
      .filter(isVisible)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        role: el.getAttribute("role"),
        modal: el.getAttribute("aria-modal"),
        text: (el.innerText || "").trim().slice(0, 500),
        rect: el.getBoundingClientRect().toJSON(),
      }));

    const fixedLike = Array.from(document.querySelectorAll("body *"))
      .filter((el) => {
        const style = getComputedStyle(el);
        if (el.matches("aside.sidebar")) return false;
        if (!["fixed", "sticky"].includes(style.position)) return false;
        const rect = el.getBoundingClientRect();
        return isVisible(el) && rect.width > 240 && rect.height > 80;
      })
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        className: String(el.className || "").slice(0, 120),
        text: (el.innerText || "").trim().slice(0, 300),
        rect: el.getBoundingClientRect().toJSON(),
      }))
      .slice(0, 10);

    const details = Array.from(document.querySelectorAll("details"))
      .filter(isVisible)
      .map((el) => ({
        open: el.open,
        summary: (el.querySelector("summary")?.innerText || "").trim().slice(0, 120),
        text: (el.innerText || "").trim().slice(0, 300),
      }));

    const visibleButtons = Array.from(
      document.querySelectorAll("button,[role=button],summary,a")
    )
      .filter(isVisible)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 120),
        disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        rect: el.getBoundingClientRect().toJSON(),
      }))
      .filter((entry) => entry.text)
      .slice(0, 80);

    return {
      label: stateLabel,
      url: location.href,
      title: document.title,
      scrollY: window.scrollY,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      bodyOverflow: getComputedStyle(document.body).overflow,
      activeElement:
        document.activeElement &&
        `${document.activeElement.tagName.toLowerCase()} ${(
          document.activeElement.innerText ||
          document.activeElement.getAttribute("aria-label") ||
          document.activeElement.getAttribute("placeholder") ||
          ""
        )
          .trim()
          .slice(0, 120)}`,
      bodyTextHash: String(document.body.innerText || "").length,
      bodyTextSample: (document.body.innerText || "").slice(0, 1400),
      dialogs,
      fixedLike,
      details,
      visibleButtons,
    };
  }, label);
}

function hasVisibleText(state, text) {
  return state.bodyTextSample.includes(text);
}

async function ensureProject(page, evidence) {
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1200);
  evidence.push({
    step: "load-app",
    screenshot: await saveScreenshot(page, "01-load-app"),
    state: await domState(page, "load-app"),
  });

  const body = await page.textContent("body");
  if (body && body.includes("查看前置材料详情") && body.includes("查看护城河地图")) {
    return "existing-project";
  }

  const selectedMode = await clickLabel(page, "从技术想法撰写发明专利");
  if (!selectedMode) {
    throw new Error("Could not find invention entry card on start screen.");
  }

  await page.waitForTimeout(600);
  evidence.push({
    step: "select-invention-mode",
    screenshot: await saveScreenshot(page, "02-select-invention-mode"),
    state: await domState(page, "select-invention-mode"),
  });

  const firstInput = page.locator("input:visible").first();
  const firstTextarea = page.locator("textarea:visible").first();
  await firstInput.fill(projectName);
  await firstTextarea.fill(idea);

  evidence.push({
    step: "filled-create-form",
    screenshot: await saveScreenshot(page, "03-filled-create-form"),
    state: await domState(page, "filled-create-form"),
  });

  const createButton = page.getByRole("button", { name: /创建并继续|填写并创建项目/ }).last();
  await createButton.click();
  await page.waitForTimeout(1800);

  evidence.push({
    step: "project-created",
    screenshot: await saveScreenshot(page, "04-project-created"),
    state: await domState(page, "project-created"),
  });

  return "created-project";
}

async function closeByCommonMeans(page, triggerLabel) {
  const attempts = [];
  const closeLabels = ["关闭", "收起", "返回向导", "取消", "完成", "知道了", "×", "x"];

  await page.keyboard.press("Escape");
  await page.waitForTimeout(350);
  attempts.push({ method: "Escape", state: await domState(page, `${triggerLabel}-after-escape`) });

  for (const label of closeLabels) {
    const item = await firstVisibleExact(page, label);
    if (item) {
      await item.scrollIntoViewIfNeeded();
      await item.click().catch(() => {});
      await page.waitForTimeout(350);
      attempts.push({ method: `click ${label}`, state: await domState(page, `${triggerLabel}-after-${label}`) });
      return attempts;
    }
  }

  const trigger = await firstVisible(page, triggerLabel);
  if (trigger) {
    await trigger.scrollIntoViewIfNeeded();
    await trigger.click().catch(() => {});
    await page.waitForTimeout(350);
    attempts.push({
      method: `toggle ${triggerLabel}`,
      state: await domState(page, `${triggerLabel}-after-toggle`),
    });
    return attempts;
  }

  await page.mouse.click(280, 90);
  await page.waitForTimeout(350);
  attempts.push({ method: "click outside", state: await domState(page, `${triggerLabel}-after-outside`) });
  return attempts;
}

async function exerciseExpertToolsNavigation(page) {
  const result = { label: "专家工具", skipped: false, screenshots: {}, states: {} };
  const expert = await firstVisible(page, "专家工具");
  if (!expert) {
    result.skipped = true;
    result.reason = "button not visible";
    return result;
  }

  result.screenshots.before = await saveScreenshot(page, "expert-tools-before");
  result.states.before = await domState(page, "expert-tools-before");

  await expert.click();
  await page.waitForTimeout(600);
  result.screenshots.open = await saveScreenshot(page, "expert-tools-open");
  result.states.open = await domState(page, "expert-tools-open");

  const returnToGuide = await firstVisibleExact(page, "返回向导");
  if (returnToGuide) {
    await returnToGuide.click();
    await page.waitForTimeout(600);
    result.screenshots.afterReturn = await saveScreenshot(page, "expert-tools-after-return");
    result.states.afterReturn = await domState(page, "expert-tools-after-return");
  } else {
    result.returnSkipped = "返回向导 button not visible after opening expert tools";
  }

  const expertAgain = await firstVisible(page, "专家工具");
  if (expertAgain) {
    await expertAgain.click();
    await page.waitForTimeout(600);
    result.screenshots.reopen = await saveScreenshot(page, "expert-tools-reopen");
    result.states.reopen = await domState(page, "expert-tools-reopen");
    const returnAgain = await firstVisibleExact(page, "返回向导");
    if (returnAgain) {
      await returnAgain.click();
      await page.waitForTimeout(600);
      result.screenshots.finalGuide = await saveScreenshot(page, "expert-tools-final-guide");
      result.states.finalGuide = await domState(page, "expert-tools-final-guide");
    }
  } else {
    result.reopenSkipped = "专家工具 button not visible after returning to guide";
  }

  return result;
}

async function exerciseTrigger(page, label, options = {}) {
  const result = { label, skipped: false, screenshots: {}, states: {}, closeAttempts: [] };
  const item = await firstVisible(page, label);
  if (!item) {
    result.skipped = true;
    result.reason = "trigger not visible";
    return result;
  }

  await item.scrollIntoViewIfNeeded();
  result.screenshots.before = await saveScreenshot(page, `trigger-${label}-before`);
  result.states.before = await domState(page, `${label}-before`);
  await item.click();
  await page.waitForTimeout(options.waitAfterClick || 500);
  result.screenshots.open = await saveScreenshot(page, `trigger-${label}-open`);
  result.states.open = await domState(page, `${label}-open`);

  result.closeAttempts = await closeByCommonMeans(page, label);
  result.screenshots.afterClose = await saveScreenshot(page, `trigger-${label}-after-close`);
  result.states.afterClose = await domState(page, `${label}-after-close`);

  const reopen = await firstVisible(page, label);
  if (reopen) {
    await reopen.scrollIntoViewIfNeeded();
    await reopen.click().catch(() => {});
    await page.waitForTimeout(options.waitAfterClick || 500);
    result.screenshots.reopen = await saveScreenshot(page, `trigger-${label}-reopen`);
    result.states.reopen = await domState(page, `${label}-reopen`);
    if (options.closeAfterReopen) {
      result.closeAfterReopenAttempts = await closeByCommonMeans(page, label);
      result.screenshots.finalClose = await saveScreenshot(page, `trigger-${label}-final-close`);
      result.states.finalClose = await domState(page, `${label}-final-close`);
    }
  } else {
    result.reopenSkipped = "trigger not visible after close attempts";
  }

  return result;
}

async function exercisePromptDetails(page) {
  const result = { label: "查看完整提示词", skipped: false, screenshots: {}, states: {} };
  const summary = await firstVisible(page, "查看完整提示词");
  if (!summary) {
    result.skipped = true;
    result.reason = "summary not visible";
    return result;
  }

  await summary.scrollIntoViewIfNeeded();
  result.screenshots.before = await saveScreenshot(page, "prompt-details-before");
  result.states.before = await domState(page, "prompt-details-before");

  await summary.click();
  await page.waitForTimeout(350);
  result.screenshots.collapsed = await saveScreenshot(page, "prompt-details-collapsed");
  result.states.collapsed = await domState(page, "prompt-details-collapsed");

  const summaryAgain = await firstVisible(page, "查看完整提示词");
  if (summaryAgain) {
    await summaryAgain.scrollIntoViewIfNeeded();
    await summaryAgain.click();
    await page.waitForTimeout(350);
    result.screenshots.reopened = await saveScreenshot(page, "prompt-details-reopened");
    result.states.reopened = await domState(page, "prompt-details-reopened");
  }

  return result;
}

async function exerciseTopbarReturn(page) {
  const result = { label: "返回三选一", skipped: false, screenshots: {}, states: {} };
  const button = await firstVisible(page, "返回三选一");
  if (!button) {
    result.skipped = true;
    result.reason = "button not visible";
    return result;
  }
  await button.click();
  await page.waitForTimeout(700);
  result.screenshots.afterReturn = await saveScreenshot(page, "return-three-choice-after-click");
  result.states.afterReturn = await domState(page, "return-three-choice-after-click");

  const invention = await firstVisible(page, "从技术想法撰写发明专利");
  if (invention) {
    await invention.click();
    await page.waitForTimeout(700);
    result.screenshots.afterReenter = await saveScreenshot(page, "return-three-choice-after-reenter");
    result.states.afterReenter = await domState(page, "return-three-choice-after-reenter");
  } else {
    result.reenterSkipped = "mode card not visible after return";
  }
  return result;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  const events = { console: [], pageErrors: [], requestFailures: [] };

  page.on("console", (msg) => {
    events.console.push({ type: msg.type(), text: msg.text() });
  });
  page.on("pageerror", (err) => {
    events.pageErrors.push({ message: err.message, stack: err.stack });
  });
  page.on("requestfailed", (request) => {
    events.requestFailures.push({
      method: request.method(),
      url: request.url(),
      failure: request.failure(),
    });
  });

  const evidence = [];
  const setupMode = await ensureProject(page, evidence);
  const results = [];

  results.push(await exerciseExpertToolsNavigation(page));
  results.push(await exerciseTrigger(page, "查看前置材料详情", { closeAfterReopen: true }));
  results.push(await exerciseTrigger(page, "查看护城河地图", { closeAfterReopen: true }));
  results.push(await exercisePromptDetails(page));
  results.push(await exerciseTopbarReturn(page));

  const summary = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    setupMode,
    projectName,
    events,
    evidence,
    results,
    heuristics: results.map((result) => {
      if (result.skipped) return { label: result.label, status: "skipped", reason: result.reason };
      const open = result.states.open || result.states.afterReturn || result.states.collapsed;
      const afterClose =
        result.states.afterClose ||
        result.states.afterReturn ||
        result.states.finalGuide ||
        result.states.finalClose ||
        result.states.reopened ||
        result.states.afterReenter;
      const changed =
        open && afterClose
          ? JSON.stringify({
              openHash: open.bodyTextHash,
              afterHash: afterClose.bodyTextHash,
              openDialogs: open.dialogs?.length,
              afterDialogs: afterClose.dialogs?.length,
              openFixed: open.fixedLike?.length,
              afterFixed: afterClose.fixedLike?.length,
            })
          : "n/a";
      return {
        label: result.label,
        status: "observed",
        changed,
        openDialogs: open?.dialogs?.length || 0,
        openFixedLike: open?.fixedLike?.length || 0,
        afterCloseDialogs: afterClose?.dialogs?.length || 0,
        afterCloseFixedLike: afterClose?.fixedLike?.length || 0,
        promptCollapsed:
          result.label === "查看完整提示词"
            ? !hasVisibleText(result.states.collapsed, "你是一名专利情报研究员")
            : undefined,
      };
    }),
  };

  fs.writeFileSync(statePath, JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary.heuristics, null, 2));
  console.log(`STATE_PATH ${statePath}`);
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
