async (page) => {
  const projectName = `UI端到端全流程-happy-${Date.now()}`;
  const idea = "一种基于低置信区域热力图自动生成无人机补采任务并回写任务状态的城市体检方法。";

  async function waitForBodyText(pattern, timeout = 30000) {
    const matcher = typeof pattern === "string" ? pattern : pattern.source;
    await page.waitForFunction(
      ({ source, isRegex }) => {
        const text = document.body.innerText;
        return isRegex ? new RegExp(source).test(text) : text.includes(source);
      },
      { source: matcher, isRegex: pattern instanceof RegExp },
      { timeout },
    );
  }

  async function clickEnabledButton(name, options = {}) {
    const locator = page.getByRole("button", { name, exact: options.exact ?? true });
    const button = options.first ? locator.first() : locator.last();
    await button.waitFor({ timeout: options.timeout ?? 30000 });
    await page.waitForFunction(
      (label) => {
        const buttons = [...document.querySelectorAll("button")];
        return buttons.some((button) => button.innerText.trim() === label && !button.disabled);
      },
      typeof name === "string" ? name : name.source,
      { timeout: options.timeout ?? 30000 },
    );
    await button.click();
  }

  await page.goto("http://127.0.0.1:5175/");
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.reload();

  await page.getByRole("button", { name: /从技术想法撰写发明专利/ }).click();
  await page.getByLabel("项目名称").fill(projectName);
  await page.getByLabel("一句话想法").fill(idea);
  await page.getByRole("button", { name: "创建并继续" }).click();

  await waitForBodyText(projectName);
  await page.getByRole("combobox", { name: "当前项目" }).selectOption({ label: projectName }).catch(() => {});

  await clickEnabledButton("提炼发明点");
  await page.getByText("低置信区域驱动的无人机补采任务生成").waitFor({ timeout: 30000 });
  await clickEnabledButton("选为主线并保存后备路线");

  await clickEnabledButton("启动多智能体会审");
  await waitForBodyText("下一步：凝练核心公式");

  await clickEnabledButton("凝练核心公式");
  await waitForBodyText("下一步：生成专利初稿");

  await clickEnabledButton("生成初稿");
  await waitForBodyText("下一步：运行质量检查");

  await clickEnabledButton("运行质量检查");
  await waitForBodyText("下一步：生成正式稿");

  await clickEnabledButton("生成正式稿");
  await waitForBodyText("下一步：启动成稿会审");

  await clickEnabledButton("启动成稿会审");
  await waitForBodyText(/导出正式稿|可导出|已通过成稿会审|下一步：打开导出工具/);

  const result = await page.evaluate(async (name) => {
    const projects = await fetch("/api/projects").then((response) => response.json());
    const project = projects.projects.find((item) => item.name === name);
    if (!project) return { projectName: name, projectId: "", exportReady: false };
    const readiness = await fetch(`/api/projects/${project.id}/export-readiness`).then((response) => response.json());
    return {
      projectName: name,
      projectId: project.id,
      exportReady: readiness.export_allowed === true || readiness.next_action === "export_ready",
      nextAction: readiness.next_action,
      officialPackageHash: readiness.official_package_hash ?? "",
    };
  }, projectName);

  if (!result.exportReady) {
    throw new Error(`Export was not unlocked: ${JSON.stringify(result)}`);
  }
  return result;
}
