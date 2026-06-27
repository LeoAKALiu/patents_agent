const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromFrontend = createRequire(path.resolve(__dirname, "../../frontend/package.json"));
const { chromium } = requireFromFrontend("playwright");

const baseUrl = "http://127.0.0.1:5174/";
const apiBase = "http://127.0.0.1:8000";
const outDir = path.resolve(".gstack/qa-reports");
const screenshotDir = path.join(outDir, "screenshots", "round36-missing-path");
const statePath = path.join(outDir, "round36-missing-path-file-state.json");
const missingPath = path.join(outDir, "fixtures", `round36-definitely-missing-${Date.now()}.md`);

fs.mkdirSync(screenshotDir, { recursive: true });

const state = {
  generatedAt: new Date().toISOString(),
  baseUrl,
  apiBase,
  missingPath,
  missingPathExists: fs.existsSync(missingPath),
  projectName: `Round36 不存在路径文件 ${Date.now()}`,
  events: {
    console: [],
    pageErrors: [],
    requestFailures: [],
    materialResponses: [],
    mutatingRequests: [],
  },
  evidence: [],
  assertions: {},
};

function shotPath(name) {
  return path.join(screenshotDir, `${name}.png`);
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
        style.visibility !== "hidden"
      );
    }

    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]')).map((input) => {
      const rect = input.getBoundingClientRect();
      return {
        visible: isVisible(input),
        value: input.value,
        files: Array.from(input.files || []).map((file) => ({
          name: file.name,
          size: file.size,
          type: file.type,
        })),
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      };
    });

    const buttons = Array.from(document.querySelectorAll("button"))
      .filter(isVisible)
      .map((button) => ({
        text: (button.innerText || button.textContent || "").trim().replace(/\s+/g, " ").slice(0, 180),
        disabled: button.disabled,
      }));

    return {
      label: metricLabel,
      url: location.href,
      viewport: { width: innerWidth, height: innerHeight },
      hasHorizontalOverflow: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) > innerWidth + 1,
      bodyTextSample: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 2000),
      fileInputs,
      buttons,
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

async function apiJson(pathname) {
  const response = await fetch(`${apiBase}${pathname}`);
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    // Keep text body.
  }
  if (!response.ok) {
    throw new Error(`GET ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function projectIdForName(name) {
  const payload = await apiJson("/api/projects");
  const projects = Array.isArray(payload) ? payload : payload.projects || [];
  const project = projects.find((entry) => entry.name === name);
  if (!project) {
    throw new Error(`Project not found after create: ${name}`);
  }
  return project.id;
}

async function materialsFor(projectId) {
  const payload = await apiJson(`/api/projects/${projectId}/materials`);
  return Array.isArray(payload) ? payload : payload.materials || [];
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
  page.on("pageerror", (error) => state.events.pageErrors.push(error.message));
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
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/projects/") && url.includes("/materials")) {
      state.events.materialResponses.push({
        method: response.request().method(),
        url,
        status: response.status(),
      });
    }
  });

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(900);
    await evidence(page, "01-start");

    await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).click();
    await page.waitForTimeout(400);
    await page.getByLabel("项目名称").fill(state.projectName);
    await page.getByLabel("一句话想法").fill("一种用于验证不存在路径文件选择是否能真实到达应用上传流程的测试项目。");
    await evidence(page, "02-create-form-filled");

    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/api/projects") && response.request().method() === "POST", { timeout: 15000 }),
      page.getByRole("button", { name: "创建并继续" }).click(),
    ]);
    await page.waitForTimeout(1200);
    await evidence(page, "03-project-created");

    state.projectId = await projectIdForName(state.projectName);
    const projectSelector = page.locator(`select:has(option[value="${state.projectId}"])`).first();
    if (await projectSelector.isVisible().catch(() => false)) {
      await projectSelector.selectOption(state.projectId);
      await page.waitForTimeout(1200);
      await evidence(page, "03b-project-selected");
    }

    try {
      await page.waitForFunction(
        () => {
          const buttonText = Array.from(document.querySelectorAll("button"))
            .map((button) => (button.innerText || button.textContent || "").replace(/\s+/g, " ").trim())
            .join("\n");
          return (
            document.querySelectorAll('input[type="file"]').length > 0 ||
            /选择并上传多份报告|上传材料|选择文件|上传外部研究报告|选择并上传|上传文件/.test(buttonText)
          );
        },
        { timeout: 15000 },
      );
      state.uploadControlWait = { ok: true };
    } catch (error) {
      state.uploadControlWait = {
        ok: false,
        name: error.name,
        message: error.message,
      };
    }
    await evidence(page, "03c-upload-control-ready");

    state.materialsBefore = await materialsFor(state.projectId);
    const materialPostCountBefore = state.events.materialResponses.filter((entry) => entry.method === "POST").length;

    state.fileInputCount = await page.locator('input[type="file"]').count();
    const uploadButton = page.getByRole("button", {
      name: /选择并上传多份报告|上传材料|选择文件|上传外部研究报告|选择并上传|上传文件/,
    }).first();
    state.uploadButtonVisible = await uploadButton.isVisible().catch(() => false);
    if (state.uploadButtonVisible) {
      try {
        const chooserPromise = page.waitForEvent("filechooser", { timeout: 5000 });
        await uploadButton.click();
        const chooser = await chooserPromise;
        try {
          await chooser.setFiles(missingPath);
          state.setInputFiles = { ok: true, via: "filechooser" };
        } catch (error) {
          state.setInputFiles = {
            ok: false,
            via: "filechooser",
            name: error.name,
            message: error.message,
          };
        }
      } catch (error) {
        state.fileChooserOpen = {
          ok: false,
          name: error.name,
          message: error.message,
        };
      }
    }

    if (!state.setInputFiles) {
      const fileInput = page.locator('input[type="file"]').first();
      try {
        await fileInput.setInputFiles(missingPath, { timeout: 5000 });
        state.setInputFiles = { ok: true, via: "locator" };
      } catch (error) {
        state.setInputFiles = {
          ok: false,
          via: "locator",
          name: error.name,
          message: error.message,
        };
      }
    }

    await page.waitForTimeout(800);
    await evidence(page, "04-after-missing-path-attempt");

    state.materialsAfter = await materialsFor(state.projectId);
    const materialPostCountAfter = state.events.materialResponses.filter((entry) => entry.method === "POST").length;

    state.assertions = {
      projectId: state.projectId,
      missingPathExists: state.missingPathExists,
      fileInputCount: state.fileInputCount,
      uploadControlWait: state.uploadControlWait,
      uploadButtonVisible: state.uploadButtonVisible,
      fileChooserOpen: state.fileChooserOpen || null,
      setInputFilesBlockedBeforeApp: state.setInputFiles && state.setInputFiles.ok === false,
      setInputFilesErrorMentionsMissingPath: /ENOENT|no such file|not found|failed to read|does not exist/i.test(
        state.setInputFiles?.message || "",
      ),
      materialCountBefore: state.materialsBefore.length,
      materialCountAfter: state.materialsAfter.length,
      materialPostCountBefore,
      materialPostCountAfter,
      noMaterialPostAfterMissingPath: materialPostCountAfter === materialPostCountBefore,
      noMaterialCountIncrease: state.materialsAfter.length === state.materialsBefore.length,
      productDidNotReceiveMissingPath:
        state.setInputFiles &&
        state.setInputFiles.ok === false &&
        materialPostCountAfter === materialPostCountBefore &&
        state.materialsAfter.length === state.materialsBefore.length,
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrors: state.events.console.filter((entry) => entry.type === "error").length,
    };
  } catch (error) {
    state.error = { message: error.message, stack: error.stack };
  } finally {
    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify({
      statePath,
      projectId: state.projectId || null,
      missingPath,
      missingPathExists: state.missingPathExists,
      fileInputCount: state.fileInputCount || 0,
      setInputFiles: state.setInputFiles || null,
      assertions: state.assertions,
      error: state.error?.message || null,
    }, null, 2));
    await browser.close().catch(() => {});
  }
})();
