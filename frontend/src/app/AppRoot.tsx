import { ClipboardList, Gauge, Loader2, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";

import { SettingsPanel } from "@/SettingsPanel";
import { ExpertToolChooser } from "@/views/expertViews";
import { BusyOperationConsole } from "@/views/runtimePanel";
import { SystemStatusPanel } from "@/ui/SystemStatusPanel";
import type { ThemeMode } from "@/ui/useTheme";
import { ShellLayout } from "@/app/ShellLayout";
import {
  fixedGoalModeFor,
  resolveRoute,
  type RouteKind,
} from "@/app/routes";
import { agentRunModeLabel } from "@/domain";
import {
  ProjectSelectorSlot,
  ProjectWorkspace,
  type ProjectWorkspaceHandlers,
  type ProjectWorkspaceState,
} from "@/features/projects/ProjectWorkspace";
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
import { guidedBusyLabel, guidedOperationLog, mainSections } from "@/guidedFlow";
import type { MainSectionId, ExpertToolId, StartChoiceId } from "@/guidedFlow";
import type { Health, AgentDoctorReport, ProjectRecord } from "@/api";

/**
 * AppRoot receives everything App.tsx currently manages — state, handlers,
 * navigation — and renders the production shell with the active feature
 * workspace inside. App.tsx keeps the existing state machine and forwards the
 * current state/handlers as props.
 *
 * AppRoot does not own state. It only:
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

function routeKindToExpertTool(
  kind: RouteKind,
  activeExpertTool: ExpertToolId,
): CorpusTool | QualityTool | PostDraftTool {
  if (kind === "knowledge") {
    return activeExpertTool === "build" || activeExpertTool === "corpus"
      ? activeExpertTool
      : "build";
  }
  if (kind === "export") return "export";
  if (kind === "expert-corpus") return activeExpertTool as CorpusTool;
  if (kind === "expert-quality") return activeExpertTool as QualityTool;
  return activeExpertTool as PostDraftTool;
}

/**
 * Decide which topbar action buttons to show. Mirrors the App.tsx logic
 * 1:1 so the chrome is preserved.
 */
function topbarActions(props: AppRootProps): React.ReactNode {
  const onStart = props.activeSection === "workbench" && !props.selectedProject && !props.startChoice;
  if (onStart) return null;
  return (
    <>
      {props.activeSection !== "expert" && (
        <Button
          variant="outline"
          className="topbar-action-button"
          onClick={() => props.onSelectSection("expert")}
          type="button"
        >
          <Gauge size={16} />
          <span>专家工具</span>
        </Button>
      )}
      {props.activeSection === "expert" && (
        <Button
          variant="outline"
          className="topbar-action-button"
          onClick={() => props.onSelectSection("workbench")}
          type="button"
        >
          <Wand2 size={16} />
          <span>返回向导</span>
        </Button>
      )}
      {(props.startChoice || props.activeSection === "expert") && (
        <Button
          variant="outline"
          className="topbar-action-button"
          onClick={props.onReturnToStartChoices}
          type="button"
        >
          <ClipboardList size={16} />
          <span>返回三选一</span>
        </Button>
      )}
    </>
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

function expertSection(props: AppRootProps, kind: RouteKind): React.ReactNode {
  if (kind === "knowledge" || kind === "expert-corpus") {
    return (
      <CorpusWorkspace
        tool={routeKindToExpertTool(kind, props.activeExpertTool) as CorpusTool}
        state={props.corpusState}
        handlers={props.corpusHandlers}
      />
    );
  }
  if (kind === "expert-quality") {
    return (
      <QualityWorkspace
        tool={routeKindToExpertTool(kind, props.activeExpertTool) as QualityTool}
        state={props.qualityState}
        handlers={props.qualityHandlers}
      />
    );
  }
  if (kind === "expert-post-draft" || kind === "export") {
    return (
      <PostDraftWorkspace
        tool={routeKindToExpertTool(kind, props.activeExpertTool) as PostDraftTool}
        state={props.postDraftState}
        handlers={props.postDraftHandlers}
      />
    );
  }
  return (
    <PostDraftWorkspace
      tool={routeKindToExpertTool(kind, props.activeExpertTool) as PostDraftTool}
      state={props.postDraftState}
      handlers={props.postDraftHandlers}
    />
  );
}

function pageTitleForSection(activeSection: MainSectionId): { title: string; subtitle?: string } {
  if (activeSection === "projects") return { title: "项目", subtitle: "查看历史项目和运行记录" };
  if (activeSection === "settings") return { title: "设置", subtitle: "本机 LLM 服务参数与 API Key" };
  if (activeSection === "knowledge") return { title: "知识库", subtitle: "构建与检索现有语料库" };
  if (activeSection === "expert") return { title: "专家工具", subtitle: "按工作流阶段拆分的子工具集" };
  if (activeSection === "export") return { title: "导出", subtitle: "导出正式稿与相关交付文件" };
  if (activeSection === "workbench") return { title: "工作台", subtitle: "选择一种默认路径进入 v1.1.0 向导" };
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

export function AppRoot(props: AppRootProps) {
  const route = resolveRoute(
    props.activeSection,
    props.activeExpertTool,
    Boolean(props.selectedProject),
    Boolean(props.startChoice),
  );
  const { title, subtitle } = pageTitleForSection(props.activeSection);
  const sidebarMain = mainSections.map((section) => ({
    id: section.id,
    label: section.label,
    icon: <section.icon size={16} aria-hidden="true" />,
    description: section.description,
  }));
  const keySections = props.selectedProject
    ? [
        { id: "idea", label: "01 想法与材料", icon: <ClipboardList size={14} aria-hidden="true" /> },
        { id: "moat", label: "02 发明点确认", icon: <Gauge size={14} aria-hidden="true" /> },
        { id: "deliberate", label: "03 多智能体会审", icon: <ClipboardList size={14} aria-hidden="true" /> },
      ]
    : undefined;
  const showExpertWorkspace = route === "knowledge"
    || route === "export"
    || route === "expert-corpus"
    || route === "expert-quality"
    || route === "expert-post-draft";
  const showExpertChooser = props.activeSection === "expert";
  return (
    <ShellLayout
      activeSectionId={props.activeSection}
      mainSections={sidebarMain}
      keySections={keySections}
      onSelectSection={(id) => props.onSelectSection(id as MainSectionId)}
      onSelectKeySection={(id) => {
        if (id === "idea") props.onSelectSection("workbench");
        else if (id === "moat") {
          props.onSelectSection("expert");
          props.onSelectExpertTool("moat");
        } else if (id === "deliberate") {
          props.onSelectSection("expert");
          props.onSelectExpertTool("deliberate");
        }
      }}
      sidebarFooter={
        <SystemStatusPanel
          selectedProject={props.selectedProject}
          health={props.health}
          agentDoctor={props.agentDoctor}
          backendStatus={props.backendStatus}
          projectListStatus={props.projectListStatus}
          agentRunModeLabel={agentRunModeLabel}
          onRefresh={props.onRefresh}
        />
      }
      topbar={{
        onRefresh: () => void props.onRefresh(),
        statusLabel: props.busy ? "处理中" : "空闲",
        statusVariant: props.busy ? "busy" : "idle",
        projectSelector: (
          <ProjectSelectorSlot
              projects={props.projects}
              selectedProjectId={props.selectedProject?.id ?? ""}
              loadStatus={props.projectListStatus}
              onSelect={props.onSelectProjectId}
            />
        ),
        actions: topbarActions(props),
      }}
      pageTitle={title}
      pageSubtitle={subtitle}
    >
      {mobileNav(props)}
      {noticeBar(props)}
      <div className="workspace">
        {(route === "start-choice" || route === "guided") &&
          projectWorkspace(props, props.startChoice === "utility" ? "utility" : "generate")}
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
            {expertSection(props, route)}
          </div>
        )}
      </div>
    </ShellLayout>
  );
}
