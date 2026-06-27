const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const requireFromGstack = createRequire("/Users/leo/Projects/gstack/package.json");
const { chromium } = requireFromGstack("playwright");

const baseUrl = process.env.PATENTAGENT_BASE_URL || "http://127.0.0.1:5175/";
const apiBaseUrl = process.env.PATENTAGENT_API_BASE_URL || "http://127.0.0.1:8001";
const outDir = path.resolve(".gstack/qa-reports");
const fixtureDir = path.join(outDir, "test-files");
const screenshotDir = path.join(outDir, "screenshots", "round37-material-upload-errors");
const statePath = path.join(outDir, "round37-material-upload-errors-state.json");

fs.mkdirSync(fixtureDir, { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });

const fixtures = {
  emptyMd: path.join(fixtureDir, "round37-empty.md"),
  fakeDocx: path.join(fixtureDir, "round37-fake.docx"),
  unsupported: path.join(fixtureDir, "round37-unsupported.xyz"),
  unreadable: path.join(fixtureDir, "round37-unreadable.md"),
  validMd: path.join(fixtureDir, "round37-valid-material.md"),
};

function writeFixtures() {
  fs.writeFileSync(fixtures.emptyMd, " \n\t", "utf8");
  fs.writeFileSync(fixtures.fakeDocx, "not a real docx archive", "utf8");
  fs.writeFileSync(fixtures.unsupported, "unsupported material body", "utf8");
  fs.writeFileSync(
    fixtures.unreadable,
    "# Round37 unreadable material\n\nThis file is chmod 000 to simulate a browser-side permission failure.\n",
    "utf8",
  );
  fs.chmodSync(fixtures.unreadable, 0o000);
  fs.writeFileSync(
    fixtures.validMd,
    "# Round37 valid material\n\n有效补充材料：系统包括采集模块、缺陷定位模块和结果输出模块，能够支撑发明点提炼。",
    "utf8",
  );
}

function shotPath(name) {
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
    // Keep raw text for diagnostics.
  }
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${pathname} returned ${response.status}: ${text.slice(0, 500)}`);
  }
  return body;
}

async function uploadFileDirect(projectId, filePath, mimeType) {
  const form = new FormData();
  const data = fs.readFileSync(filePath);
  form.append("file", new Blob([data], { type: mimeType }), path.basename(filePath));
  const response = await fetch(`${apiBaseUrl}/api/projects/${projectId}/materials`, {
    method: "POST",
    body: form,
  });
  const text = await response.text();
  let body = text;
  try {
    body = JSON.parse(text);
  } catch {
    // Keep raw text for diagnostics.
  }
  return { status: response.status, body };
}

async function routeApiToIsolatedBackend(page) {
  await page.route("**/api/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    const targetUrl = `${apiBaseUrl}${requestUrl.pathname}${requestUrl.search}`;
    const response = await route.fetch({ url: targetUrl });
    await route.fulfill({ response });
  });
}

async function materialsFor(projectId) {
  return fetchJson(`/api/projects/${projectId}/materials`);
}

async function collectPageState(page, label) {
  return page.evaluate((stateLabel) => {
    const body = document.body;
    const bodyText = body ? body.innerText : "";
    return {
      label: stateLabel,
      url: location.href,
      bodyTextSample: bodyText.slice(0, 6000),
      hasEmptyFileError: bodyText.includes("材料上传失败：文件为空"),
      hasDocxError: bodyText.includes("材料上传失败：DOCX 文件无法解析"),
      hasUnsupportedError: bodyText.includes("材料上传失败：不支持的材料文件类型"),
      hasPermissionError: bodyText.includes("无法读取该文件，请检查文件权限或重新选择可读文件。"),
      hasRawApiPath: bodyText.includes("/api/projects/"),
      hasFailedFetch: bodyText.includes("Failed to fetch"),
      hasInternalServerError: bodyText.includes("Internal Server Error"),
      hasOneUsableMaterial: bodyText.includes("当前已有 1 份可用材料。"),
      hasLegacyOneMaterialCopy: bodyText.includes("当前已有 1 份材料。"),
      hasLegacyMultipleMaterialCopy: /当前已有 [234] 份材料/.test(bodyText),
      hasMaterialDetailButton: bodyText.includes("查看前置材料详情"),
      hasValidMaterialName: bodyText.includes("round37-valid-material.md"),
      hasSeparatedType: bodyText.includes("类型：md"),
      hasMdMdConcatenation: bodyText.includes("round37-valid-material.mdmd"),
    };
  }, label);
}

async function evidence(page, state, step) {
  const screenshot = shotPath(step);
  await page.screenshot({ path: screenshot, fullPage: true });
  const pageState = await collectPageState(page, step);
  state.evidence.push({ step, screenshot, pageState });
  return pageState;
}

async function uploadFileFromGuidedPanel(page, filePath) {
  const chooserPromise = page.waitForEvent("filechooser", { timeout: 10000 });
  await page.getByRole("button", { name: /选择并上传多份报告|上传材料|选择文件/ }).first().click();
  const chooser = await chooserPromise;
  await chooser.setFiles(filePath);
  await page.waitForTimeout(1000);
}

async function attemptUploadFileFromGuidedPanel(page, filePath) {
  try {
    await uploadFileFromGuidedPanel(page, filePath);
    return { ok: true };
  } catch (error) {
    await page.waitForTimeout(1000);
    return {
      ok: false,
      message: error && error.message ? error.message : String(error),
      name: error && error.name ? error.name : "",
    };
  }
}

async function openGuidedProject(page, projectId) {
  const startButton = page.getByRole("button", { name: /从技术想法撰写发明专利/ }).first();
  if ((await startButton.count()) > 0) {
    await startButton.click();
    await page.waitForTimeout(600);
  }
  await page.locator("select.project-select-control").first().selectOption(projectId);
  await page.waitForTimeout(1000);
}

async function main() {
  writeFixtures();
  const suffix = Date.now();
  const state = {
    generatedAt: new Date().toISOString(),
    baseUrl,
    apiBaseUrl,
    fixtures,
    project: null,
    events: { console: [], pageErrors: [], requestFailures: [], materialResponses: [] },
    evidence: [],
    materials: {},
    assertions: {},
  };

  state.project = await fetchJson("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      name: `Round37 材料上传错误 ${suffix}`,
      draft_text: "一种用于验证补充材料上传错误处理、材料计数和元数据展示的测试项目。",
      patent_type: "invention",
    }),
  });

  const browser = await chromium.launch({
    headless: true,
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    await routeApiToIsolatedBackend(page);
    page.on("console", (message) => state.events.console.push({ type: message.type(), text: message.text().slice(0, 1000) }));
    page.on("pageerror", (error) => state.events.pageErrors.push({ message: error.message, stack: error.stack }));
    page.on("requestfailed", (request) => {
      state.events.requestFailures.push({
        method: request.method(),
        url: request.url(),
        failure: request.failure() && request.failure().errorText,
      });
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

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await openGuidedProject(page, state.project.id);
    await evidence(page, state, "01-selected-project");

    state.materials.before = await materialsFor(state.project.id);

    await uploadFileFromGuidedPanel(page, fixtures.emptyMd);
    state.materials.afterEmptyMd = await materialsFor(state.project.id);
    await evidence(page, state, "02-empty-md-error");

    await uploadFileFromGuidedPanel(page, fixtures.fakeDocx);
    state.materials.afterFakeDocx = await materialsFor(state.project.id);
    await evidence(page, state, "03-fake-docx-error");

    await uploadFileFromGuidedPanel(page, fixtures.unsupported);
    state.materials.afterUnsupported = await materialsFor(state.project.id);
    await evidence(page, state, "04-unsupported-error");

    state.unreadableAttempt = await attemptUploadFileFromGuidedPanel(page, fixtures.unreadable);
    state.materials.afterUnreadable = await materialsFor(state.project.id);
    await evidence(page, state, "05-unreadable-error");

    state.directValidUpload = await uploadFileDirect(state.project.id, fixtures.validMd, "text/markdown");
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await openGuidedProject(page, state.project.id);
    state.materials.afterValid = await materialsFor(state.project.id);
    const afterValidState = await evidence(page, state, "06-valid-upload-count");

    await page.getByRole("button", { name: /查看前置材料详情/ }).first().click();
    await page.waitForTimeout(1000);
    const detailState = await evidence(page, state, "07-material-detail");

    const finalMaterials = state.materials.afterValid.materials || [];
    const processedMaterials = finalMaterials.filter((material) => material.status === "processed");
    const failedMaterials = finalMaterials.filter((material) => material.status !== "processed");
    const postStatuses = state.events.materialResponses
      .filter((entry) => entry.method === "POST")
      .map((entry) => entry.status);

    state.assertions = {
      emptyRejectedWith4xx: postStatuses[0] >= 400 && postStatuses[0] < 500,
      fakeDocxRejectedWith4xx: postStatuses[1] >= 400 && postStatuses[1] < 500,
      unsupportedRejectedWith4xx: postStatuses[2] >= 400 && postStatuses[2] < 500,
      validUploadSucceeded: state.directValidUpload.status === 200,
      invalidUploadsNotPersisted:
        (state.materials.afterEmptyMd.materials || []).length === 0 &&
        (state.materials.afterFakeDocx.materials || []).length === 0 &&
        (state.materials.afterUnsupported.materials || []).length === 0 &&
        (state.materials.afterUnreadable.materials || []).length === 0,
      finalHasOnlyOneProcessedMaterial: processedMaterials.length === 1 && failedMaterials.length === 0,
      finalMaterialIsValidMd: processedMaterials[0] && processedMaterials[0].file_name === "round37-valid-material.md",
      uiShowsEmptyError: state.evidence.some((entry) => entry.pageState.hasEmptyFileError),
      uiShowsDocxError: state.evidence.some((entry) => entry.pageState.hasDocxError),
      uiShowsUnsupportedError: state.evidence.some((entry) => entry.pageState.hasUnsupportedError),
      unreadableAttemptDidNotPersist: (state.materials.afterUnreadable.materials || []).length === 0,
      uiDoesNotExposeRawApiOrFetch:
        !state.evidence.some((entry) => entry.pageState.hasRawApiPath || entry.pageState.hasFailedFetch || entry.pageState.hasInternalServerError),
      uiCountsOnlyProcessed: afterValidState.hasOneUsableMaterial && !afterValidState.hasLegacyOneMaterialCopy && !afterValidState.hasLegacyMultipleMaterialCopy,
      detailSeparatesMetadata: detailState.hasValidMaterialName && detailState.hasSeparatedType && !detailState.hasMdMdConcatenation,
      pageErrors: state.events.pageErrors.length,
      requestFailures: state.events.requestFailures.length,
      consoleErrorsAreExpected4xx: state.events.console
        .filter((entry) => entry.type === "error")
        .every((entry) => /status of (415|422)|Unsupported Media Type|Unprocessable/i.test(entry.text)),
    };
    state.observations = {
      permissionGuidanceObserved:
        state.evidence.some((entry) => entry.pageState.hasPermissionError) ||
        (state.unreadableAttempt && state.unreadableAttempt.ok === false && /EACCES|permission|denied|not readable|open/i.test(state.unreadableAttempt.message)),
      unreadableAttempt: state.unreadableAttempt,
    };

    fs.writeFileSync(statePath, `${JSON.stringify(state, null, 2)}\n`);
    console.log(JSON.stringify(state.assertions, null, 2));
    console.log(`STATE_PATH ${statePath}`);

    const failed = Object.entries(state.assertions).filter(([key, value]) =>
      key === "pageErrors" || key === "requestFailures" ? value !== 0 : value !== true,
    );
    if (failed.length > 0) {
      throw new Error(`round37 material upload assertions failed: ${JSON.stringify(failed)}`);
    }
  } finally {
    try {
      fs.chmodSync(fixtures.unreadable, 0o644);
    } catch (_) {
      // Keep cleanup best-effort so the state file still records the failure.
    }
    await browser.close().catch(() => {});
  }
}

main().catch((error) => {
  try {
    fs.chmodSync(fixtures.unreadable, 0o644);
  } catch (_) {
    // Best-effort cleanup for interrupted permission probes.
  }
  console.error(error);
  process.exit(1);
});
