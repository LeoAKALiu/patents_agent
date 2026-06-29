import { useState } from "react";
import { ClipboardList, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

import { SettingsPanel } from "@/SettingsPanel";
import { ExpertToolChooser } from "@/views/expertViews";
import { BusyOperationConsole } from "@/views/runtimePanel";
import { SystemDiagnosticsDialog, SystemStatusPanel } from "@/ui/SystemStatusPanel";
import type { ThemeMode } from "@/ui/useTheme";
import { ShellLayout } from "@/app/ShellLayout";
import {
  fixedGoalModeFor,
  classifyExpertTool,
  resolveRoute,
} from "@/app/routes";
import { agentRunModeLabel } from "@/domain";
import {
  ProjectSelectorSlot,
  ProjectWorkspace,
  type ProjectWorkspaceHandlers,
  type ProjectWorkspaceState,
} from "@/features/projects/ProjectWorkspace";
import { WorkbenchWorkspace } from "@/features/workbench/WorkbenchWorkspace";
import { deriveWorkbenchState, type WorkbenchPrimaryTarget } from "@/features/workbench/selectors";
import {
  CorpusWorkspace,
  type CorpusTool,
  type CorpusWorkspaceHandlers,
  type CorpusWorkspaceState,
} from "@/features/corpus/CorpusWorkspace";
import {
  QualityWorkspace,
  type QualityTool,
  type QualityWorkspaceHandlers,
  type QualityWorkspaceState,
} from "@/features/quality/QualityWorkspace";
import {
  PostDraftWorkspace,
  type PostDraftTool,
  type PostDraftWorkspaceHandlers,
  type PostDraftWorkspaceState,
} from "@/features/postDraft/PostDraftWorkspace";
import { DocumentRepairWorkspace } from "@/features/documentRepair/DocumentRepairWorkspace";
import { guidedBusyLabel, guidedOperationLog, mainSections } from "@/guidedFlow";
import type { MainSectionId, ExpertToolId, StartChoiceId } from "@/guidedFlow";
import type { Health, AgentDoctorReport, ProjectRecord } from "@/api";

/**
 * AppRoot receives everything App.tsx currently manages — state, handlers,
 * navigation — and renders the production shell with the active feature
 * workspace inside. App.tsx keeps the existing state machine and forwards the
 * current state/handlers as props.
 *
 * AppRoot does not own workflow state. It only:
 *   1. Decides which route is active via resolveRoute().
 *   2. Renders ShellLayout (sidebar + topbar + workspace area).
 *   3. Renders the workspace that matches the active route.
 */
export interface AppRootProps {
  // -- shell state ---------------------------------------------------------
  activeSection: MainSectionId;
  activeExpertTool: ExpertToolId;
  startChoice: StartChoiceId | null;
  selectedProject: ProjectRecord | null;
  projects: ProjectRecord[];
  busy: string;
  busyElapsedSeconds: number;
  message: string;
  error: string;
  health: Health | null;
  agentDoctor: AgentDoctorReport | null;
  backendStatus: "unknown" | "online" | "offline";
  projectListStatus: "idle" | "loading" | "ready" | "failed";
  theme: ThemeMode;
  // -- shell handlers ------------------------------------------------------
  onSelectSection: (section: MainSectionId) => void;
  onSelectExpertTool: (tool: ExpertToolId) => void;
  onSelectProjectId: (projectId: string) => void;
  onReturnToStartChoices: () => void;
  onChangeTheme: (theme: ThemeMode) => void;
  onRefresh: () => Promise<void> | void;
  // -- project workspace ---------------------------------------------------
  projectState: ProjectWorkspaceState;
  projectHandlers: ProjectWorkspaceHandlers;
  // -- corpus workspace ----------------------------------------------------
  corpusState: CorpusWorkspaceState;
  corpusHandlers: CorpusWorkspaceHandlers;
  // -- quality workspace ---------------------------------------------------
  qualityState: QualityWorkspaceState;
  qualityHandlers: QualityWorkspaceHandlers;
  // -- post-draft workspace ------------------------------------------------
  postDraftState: PostDraftWorkspaceState;
  postDraftHandlers: PostDraftWorkspaceHandlers;
}

function knowledgeTool(activeExpertTool: ExpertToolId): CorpusTool {
  return activeExpertTool === "build" || activeExpertTool === "corpus"
    ? activeExpertTool
    : "build";
}

function topbarRecoveryAction(props: AppRootProps): React.ReactNode {
  if (props.activeSection !== "workbench" || !props.startChoice) return null;
  return (
    <Button
      variant="outline"
      className="topbar-action-button"
      onClick={props.onReturnToStartChoices}
      type="button"
    >
      <ClipboardList size={16} />
      <span>返回三选一</span>
    </Button>
  );
}

function mobileNav(props: AppRootProps): React.ReactNode {
  return (
    <nav className="mobile-nav" aria-label="移动主导航">
      {mainSections.map((section) => {
        const Icon = section.icon;
        return (
          <button
            className={props.activeSection === section.id ? "is-active" : ""}
            key={section.id}
            onClick={() => props.onSelectSection(section.id)}
            type="button"
            title={section.label}
          >
            <Icon size={16} />
            <span>{section.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function noticeBar(props: AppRootProps): React.ReactNode {
  if (!props.busy && !props.message && !props.error) return null;
  return (
    <div className={props.error ? "notice error" : "notice"}>
      {props.busy && <Loader2 className="animate-spin" size={16} />}
      <span>
        {props.error || props.message || guidedBusyLabel(props.busy) || "处理中"}
      </span>
      {!props.error && props.busy && (
        <BusyOperationConsole
          log={guidedOperationLog(props.busy, props.busyElapsedSeconds)}
        />
      )}
    </div>
  );
}

function expertSection(props: AppRootProps): React.ReactNode {
  const toolGroup = classifyExpertTool(props.activeExpertTool);
  if (toolGroup === "corpus") {
    return (
      <CorpusWorkspace
        tool={props.activeExpertTool as CorpusTool}
        state={props.corpusState}
        handlers={props.corpusHandlers}
      />
    );
  }
  if (toolGroup === "quality") {
    return (
      <QualityWorkspace
        tool={props.activeExpertTool as QualityTool}
        state={props.qualityState}
        handlers={props.qualityHandlers}
      />
    );
  }
  return (
    <PostDraftWorkspace
      tool={props.activeExpertTool as PostDraftTool}
      state={props.postDraftState}
      handlers={props.postDraftHandlers}
    />
  );
}

function exportStatus(props: AppRootProps): {
  label: string;
  variant: "idle" | "busy" | "error" | "success" | "warning";
} {
  const readiness = props.postDraftState.exportReadiness;
  if (!props.selectedProject) return { label: "导出待检查", variant: "idle" };
  if (!readiness) return { label: "导出待检查", variant: "idle" };
  if (readiness.export_allowed || readiness.next_action === "export_ready") {
    return { label: "可导出", variant: "success" };
  }
  if (readiness.compile_status === "running" || readiness.review_gate_status === "running") {
    return { label: "导出检查中", variant: "busy" };
  }
  if (readiness.compile_status === "failed" || readiness.review_gate_status === "failed") {
    return { label: "导出异常", variant: "error" };
  }
  return { label: "导出锁定", variant: "warning" };
}

function pageTitleForSection(activeSection: MainSectionId): { title: string; subtitle?: string } {
  if (activeSection === "projects") return { title: "项目", subtitle: "查看历史项目和运行记录" };
  if (activeSection === "documents") return { title: "文稿与修复", subtitle: "处理当前项目的正文、问题和版本链路" };
  if (activeSection === "settings") return { title: "设置", subtitle: "本机 LLM 服务参数与 API Key" };
  if (activeSection === "knowledge") return { title: "知识库", subtitle: "构建与检索现有语料库" };
  if (activeSection === "expert") return { title: "专家工具", subtitle: "按工作流阶段拆分的子工具集" };
  if (activeSection === "export") return { title: "导出", subtitle: "导出正式稿与相关交付文件" };
  if (activeSection === "workbench") return { title: "工作台", subtitle: "当前项目、下一步和导出风险概览" };
  return { title: "工作台" };
}

function projectWorkspace(props: AppRootProps, section: "generate" | "utility" | "projects"): React.ReactNode {
  return (
    <div className="px-4 md:px-8 py-4 md:py-6">
      <ProjectWorkspace
        section={section}
        state={props.projectState}
        handlers={props.projectHandlers}
        loadStatus={props.projectListStatus}
        fixedGoalMode={section === "projects" ? undefined : fixedGoalModeFor(props.startChoice, props.activeSection)}
        initialIntakeMode={
          section === "projects"
            ? undefined
            : props.startChoice === "external" ? "external" : "idea"
        }
      />
    </div>
  );
}

function onWorkbenchNavigate(props: AppRootProps, target: WorkbenchPrimaryTarget): void {
  if (target === "workbench-start") return;
  props.onSelectSection(target);
}

export function AppRoot(props: AppRootProps) {
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
  const route = resolveRoute(
    props.activeSection,
    props.activeExpertTool,
    Boolean(props.selectedProject),
    Boolean(props.startChoice),
  );
  const { title, subtitle } = pageTitleForSection(props.activeSection);
  const exportStatusChip = exportStatus(props);
  const sidebarMain = mainSections.map((section) => ({
    id: section.id,
    label: section.label,
    icon: <section.icon size={16} aria-hidden="true" />,
    description: section.description,
  }));
  const showExpertWorkspace = route === "knowledge" || route === "export" || route === "expert";
  const showExpertChooser = props.activeSection === "expert";
  const workbenchState = deriveWorkbenchState({
    projectState: props.projectState,
    exportReadiness: props.postDraftState.exportReadiness,
  });
  const workbenchStartWorkspace = !props.selectedProject && props.startChoice
    ? projectWorkspace(props, props.startChoice === "utility" ? "utility" : "generate")
    : undefined;
  return (
    <>
      <ShellLayout
        activeSectionId={props.activeSection}
        mainSections={sidebarMain}
        onSelectSection={(id) => props.onSelectSection(id as MainSectionId)}
        sidebarFooter={
          <SystemStatusPanel
            health={props.health}
            agentDoctor={props.agentDoctor}
            backendStatus={props.backendStatus}
            projectListStatus={props.projectListStatus}
            agentRunModeLabel={agentRunModeLabel}
          />
        }
        topbar={{
          onRefresh: () => void props.onRefresh(),
          statusLabel: props.busy ? "处理中" : "空闲",
          statusVariant: props.busy ? "busy" : "idle",
          exportStatusLabel: exportStatusChip.label,
          exportStatusVariant: exportStatusChip.variant,
          backendStatus: props.backendStatus,
          onOpenDiagnostics: () => setDiagnosticsOpen(true),
          projectSelector: (
            <ProjectSelectorSlot
              projects={props.projects}
              selectedProjectId={props.selectedProject?.id ?? ""}
              loadStatus={props.projectListStatus}
              onSelect={props.onSelectProjectId}
            />
          ),
          actions: topbarRecoveryAction(props),
        }}
        pageTitle={title}
        pageSubtitle={subtitle}
      >
        {mobileNav(props)}
        {noticeBar(props)}
        <div className="workspace">
          {route === "workbench" && (
            <WorkbenchWorkspace
              state={workbenchState}
              handlers={props.projectHandlers}
              onNavigate={(target) => onWorkbenchNavigate(props, target)}
              startWorkspace={workbenchStartWorkspace}
            />
          )}
          {route === "documents" && (
            <DocumentRepairWorkspace
              projectState={props.projectState}
              handlers={props.projectHandlers}
              exportReadiness={props.postDraftState.exportReadiness}
              onNavigate={props.onSelectSection}
            />
          )}
          {route === "projects-overview" && projectWorkspace(props, "projects")}
          {route === "settings" && (
            <div className="px-4 md:px-8 py-4 md:py-6">
              <SettingsPanel theme={props.theme} onThemeChange={props.onChangeTheme} />
            </div>
          )}
          {showExpertWorkspace && (
            <div className="flex flex-col gap-4">
              {showExpertChooser && (
                <ExpertToolChooser activeToolId={props.activeExpertTool} onSelect={props.onSelectExpertTool} />
              )}
              {route === "knowledge" && (
                <CorpusWorkspace
                  tool={knowledgeTool(props.activeExpertTool)}
                  state={props.corpusState}
                  handlers={props.corpusHandlers}
                />
              )}
              {route === "export" && (
                <PostDraftWorkspace
                  tool="export"
                  state={props.postDraftState}
                  handlers={props.postDraftHandlers}
                />
              )}
              {route === "expert" && expertSection(props)}
            </div>
          )}
        </div>
      </ShellLayout>
      <SystemDiagnosticsDialog
        open={diagnosticsOpen}
        onOpenChange={setDiagnosticsOpen}
        health={props.health}
        agentDoctor={props.agentDoctor}
        backendStatus={props.backendStatus}
        projectListStatus={props.projectListStatus}
        agentRunModeLabel={agentRunModeLabel}
      />
    </>
  );
}
