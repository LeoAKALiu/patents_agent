const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5174/";
const apiBaseUrl = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports/screenshots/round25");
const statePath = path.resolve(".gstack/qa-reports/round25-guided-create-bad-llm-state.json");

fs.mkdirSync(outDir, { recursive: true });

function screenshotPath(name) {
  return path.join(outDir, `${name}.png`);
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

    return {
      label: stateLabel,
      url: location.href,
      bodyText: document.body.innerText,
      bodyTextSample: document.body.innerText.slice(0, 4200),
      visibleButtons: Array.from(document.querySelectorAll("button,[role=button]"))
        .filter(isVisible)
        .map((el) => ({
          text: (el.innerText || el.getAttribute("aria-label") || "").trim(),
          disabled: Boolean(el.disabled) || el.getAttribute("aria-disabled") === "true",
        })),
      visibleInputs: Array.from(document.querySelectorAll("input,textarea,select"))
        .filter(isVisible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          value: el.value,
          placeholder: el.getAttribute("placeholder") || "",
          label:
            el.closest("label")?.innerText?.trim() ||
            document.querySelector(`label[for="${el.id}"]`)?.innerText?.trim() ||
            "",
        })),
    };
  }, label);
}

async function screenshotAndState(page, evidence, name) {
  const file = screenshotPath(name);
  await page.screenshot({ path: file, fullPage: true });
  const state = await collectState(page, name);
  evidence.push({ step: name, screenshot: file, state });
  return state;
}

async function fillFirstVisible(locator, value, label) {
  const count = await locator.count().catch(() => 0);
  for (let index = 0; index < count; index += 1) {
    const candidate = locator.nth(index);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.fill(value);
      return;
    }
  }
  throw new Error(`Could not find visible field for ${label}`);
}

async function clickLastVisible(locator, label, options = {}) {
  const count = await locator.count();
  for (let index = count - 1; index >= 0; index -= 1) {
    const candidate = locator.nth(index);
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.click(options);
      return;
    }
  }
  throw new Error(`Could not find visible control for ${label}`);
}

async function configureBadLlm(page, evidence) {
  await page.getByRole("button", { name: "设置" }).first().click();
  await page.waitForTimeout(900);
  await screenshotAndState(page, evidence, "01-settings-initial");

  await page.getByLabel("Provider").fill("qa-bad-guided");
  await page.getByLabel("Base URL").fill("http://127.0.0.1:9/v1");
  await page.getByLabel("Model").fill("qa-guided-bad-model");
  await page.getByLabel(/API Key/).fill("qa-round25-key-not-real");
  await screenshotAndState(page, evidence, "02-settings-bad-llm-filled");

  await page.getByRole("button", { name: "保存" }).click();
  await page.waitForTimeout(1200);
  return screenshotAndState(page, evidence, "03-settings-bad-llm-saved");
}

async function waitForDisclosureTerminal(projectId) {
  const deadline = Date.now() + 70000;
  let latest = null;
  while (Date.now() < deadline) {
    latest = await fetchJson(`${apiBaseUrl}/api/projects/${projectId}/disclosures`);
    const runs = latest.json?.runs || [];
    const run = runs[0];
    if (run && !["queued", "running", "started", "pending"].includes(String(run.status || "").toLowerCase())) {
      return { latest, timedOut: false };
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  return { latest, timedOut: true };
}

(async () => {
  const now = Date.now();
  const projectName = `Round25 Guided 错误配置项目 ${now}`;
  const idea =
    "一种用于验证授权导向专利撰写主路径的本地智能代理系统，在错误 LLM 配置下应安全失败并保留项目上下文。";
  const evidence = [];
  const events = { console: [], pageErrors: [], requestFailures: [], mutatingRequests: [], appResponses: [] };

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on("console", (msg) => events.console.push({ type: msg.type(), text: msg.text().slice(0, 1000) }));
    page.on("pageerror", (err) => events.pageErrors.push({ message: err.message, stack: err.stack }));
    page.on("requestfailed", (request) => {
      events.requestFailures.push({ method: request.method(), url: request.url(), failure: request.failure() });
    });
    page.on("request", (request) => {
      if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) {
        events.mutatingRequests.push({ method: request.method(), url: request.url(), postData: request.postData(), ts: Date.now() });
      }
    });
    page.on("response", (response) => {
      const url = response.url();
      if (url.includes("/api/projects") || url.includes("/api/desktop-config")) {
        events.appResponses.push({ method: response.request().method(), url, status: response.status() });
      }
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    await screenshotAndState(page, evidence, "00-home");

    const savedSettings = await configureBadLlm(page, evidence);

    await page.getByRole("button", { name: "开始" }).first().click();
    await page.waitForTimeout(800);
    await screenshotAndState(page, evidence, "04-start-after-bad-settings");

    await clickLastVisible(page.getByRole("button", { name: /从技术想法撰写发明专利/ }), "invention idea entry");
    await page.waitForTimeout(600);
    await fillFirstVisible(page.getByLabel("项目名称", { exact: true }), projectName, "project name");
    await fillFirstVisible(page.getByLabel("一句话想法", { exact: true }), idea, "idea");
    await screenshotAndState(page, evidence, "05-guided-form-filled");

    const createResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/projects") && response.request().method() === "POST",
      { timeout: 15000 }
    );
    await page.getByRole("button", { name: "创建并继续" }).click();
    const createResponse = await createResponsePromise;
    await page.waitForTimeout(1600);
    const afterCreate = await screenshotAndState(page, evidence, "06-after-create");

    const projectsAfterCreate = await fetchJson(`${apiBaseUrl}/api/projects`);
    const projects = Array.isArray(projectsAfterCreate.json) ? projectsAfterCreate.json : projectsAfterCreate.json?.projects || [];
    const project = projects.find((item) => item.name === projectName) || null;

    await clickLastVisible(page.locator("button").filter({ hasText: /^提炼发明点$/ }), "start disclosure run");
    await page.waitForTimeout(1000);
    await screenshotAndState(page, evidence, "07-after-click-extract");

    let disclosurePoll = { latest: null, timedOut: true };
    if (project?.id) {
      disclosurePoll = await waitForDisclosureTerminal(project.id);
    }
    await page.waitForTimeout(1000);
    const afterRun = await screenshotAndState(page, evidence, "08-after-run-terminal-or-timeout");

    const disclosureRuns = disclosurePoll.latest?.json?.runs || [];
    const latestRun = disclosureRuns[0] || null;
    const bodyAfterRun = afterRun.bodyText;
    const disclosurePosts = events.mutatingRequests.filter(
      (request) => request.method === "POST" && /\/api\/projects\/[^/]+\/disclosures/.test(request.url)
    );
    const extractButtonsAfterRun = afterRun.visibleButtons.filter((button) => button.text === "提炼发明点");

    const result = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      apiBaseUrl,
      projectName,
      settings: {
        provider: "qa-bad-guided",
        baseUrl: "http://127.0.0.1:9/v1",
        model: "qa-guided-bad-model",
        savedSettingsSample: savedSettings.bodyTextSample,
      },
      events,
      evidence,
      api: {
        createResponseStatus: createResponse.status(),
        projectsAfterCreate,
        project,
        disclosurePoll,
      },
      assertions: {
        settingsSavedAsBadLocalConfig:
          /qa-guided-bad-model/.test(savedSettings.bodyText) &&
          /127\.0\.0\.1:9/.test(savedSettings.bodyText) &&
          /本机配置|已配置|密钥指纹/.test(savedSettings.bodyText),
        projectCreateResponseOk: createResponse.status() >= 200 && createResponse.status() < 300,
        projectCreatedExactlyOnce: projects.filter((item) => item.name === projectName).length === 1,
        enteredDisclosureStep: /提炼发明点|确认发明点|护城河/.test(afterCreate.bodyText),
        disclosurePostCount: disclosurePosts.length,
        exactlyOneDisclosurePost: disclosurePosts.length === 1,
        disclosureReachedTerminalState: Boolean(latestRun) && !disclosurePoll.timedOut,
        disclosureFailedClosed:
          Boolean(latestRun) &&
          /failed|error|interrupted|cancelled/i.test(String(latestRun.status || latestRun.runtime_state?.status || "")),
        retryButtonAvailable: extractButtonsAfterRun.some((button) => !button.disabled),
        uiStillOnProjectContext: bodyAfterRun.includes(projectName) && /提炼发明点|确认发明点|护城河/.test(bodyAfterRun),
        rawSdkErrorVisible:
          /APIConnectionError|InternalServerError|RateLimitError|Traceback|Error code:|Connection error/i.test(bodyAfterRun),
        userFacingFailureVisible: /失败|错误|无法|连接|检查|重试|配置|Base URL/i.test(bodyAfterRun),
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
