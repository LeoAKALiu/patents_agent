import { useState } from "react";
import { ClipboardList, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

import { SettingsPanel } from "@/SettingsPanel";
import { BusyOperationConsole } from "@/views/runtimePanel";
import { SystemDiagnosticsDialog, SystemStatusPanel } from "@/ui/SystemStatusPanel";
import { PrimarySurface, type StatusChip } from "@/ui/PrimarySurface";
import type { ThemeMode } from "@/ui/useTheme";
import { ShellLayout } from "@/app/ShellLayout";
import {
  fixedGoalModeFor,
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
  type CorpusWorkspaceHandlers,
  type CorpusWorkspaceState,
} from "@/features/corpus/CorpusWorkspace";
import { KnowledgeWorkspace } from "@/features/knowledge/KnowledgeWorkspace";
import {
  type QualityWorkspaceHandlers,
  type QualityWorkspaceState,
} from "@/features/quality/QualityWorkspace";
import {
  type PostDraftWorkspaceHandlers,
  type PostDraftWorkspaceState,
} from "@/features/postDraft/PostDraftWorkspace";
import { DocumentRepairWorkspace } from "@/features/documentRepair/DocumentRepairWorkspace";
import { ExportWorkspace } from "@/features/export/ExportWorkspace";
import { ExpertToolsWorkspace } from "@/features/expert/ExpertToolsWorkspace";
import { guidedBusyLabel, guidedOperationLog, mainSections } from "@/guidedFlow";
import type { MainSectionId, ExpertToolId, StartChoiceId } from "@/guidedFlow";
import type { Health, AgentDoctorReport, ProjectRecord } from "@/api";

type DocumentRepairIntent = {
  id: number;
  tab: "overview" | "annotated";
};

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

function topbarRecoveryAction(props: AppRootProps): React.ReactNode {
  if (props.activeSection !== "workbench" || !props.startChoice || props.selectedProject) return null;
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
  const visibleError = shouldDemoteHealthError(props.error) ? "" : props.error;
  if (!props.busy && !props.message && !visibleError) return null;
  return (
    <div className={visibleError ? "notice error" : "notice"}>
      {props.busy && <Loader2 className="animate-spin" size={16} />}
      <span>
        {visibleError || props.message || guidedBusyLabel(props.busy) || "处理中"}
      </span>
      {!visibleError && props.busy && (
        <BusyOperationConsole
          log={guidedOperationLog(props.busy, props.busyElapsedSeconds)}
        />
      )}
    </div>
  );
}

function shouldDemoteHealthError(error: string): boolean {
  return error.includes("/api/health");
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

function compactStatusChips(chips: Array<StatusChip | null | undefined | false>): StatusChip[] {
  return chips.filter(Boolean) as StatusChip[];
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
  const [documentRepairIntent, setDocumentRepairIntent] = useState<DocumentRepairIntent | null>(null);
  const route = resolveRoute(
    props.activeSection,
    props.activeExpertTool,
    Boolean(props.selectedProject),
    Boolean(props.startChoice),
  );
  const exportStatusChip = exportStatus(props);
  const sidebarMain = mainSections.map((section) => ({
    id: section.id,
    label: section.label,
    icon: <section.icon size={16} aria-hidden="true" />,
    description: section.description,
  }));
  const workbenchState = deriveWorkbenchState({
    projectState: props.projectState,
    exportReadiness: props.postDraftState.exportReadiness,
  });
  const workbenchStartWorkspace = props.startChoice && !props.selectedProject
    ? projectWorkspace(props, props.startChoice === "utility" ? "utility" : "generate")
    : undefined;

  function navigateDocuments(tab: DocumentRepairIntent["tab"]): void {
    setDocumentRepairIntent((current) => ({
      id: (current?.id ?? 0) + 1,
      tab,
    }));
    props.onSelectSection("documents");
  }

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
      >
        {mobileNav(props)}
        {noticeBar(props)}
        <div className="workspace">
          {route === "workbench" && (
            <PrimarySurface
              id="workbench"
              title="工作台"
              description="从起步入口推进到生成、复核、修复和导出，把当前项目状态放在同一处判断。"
              statusChips={compactStatusChips([
                props.selectedProject
                  ? { label: `项目: ${props.selectedProject.name}`, variant: "current" }
                  : { label: "未选择项目", variant: "warning" },
                props.busy
                  ? { label: `运行中: ${guidedBusyLabel(props.busy)}`, variant: "current" }
                  : { label: "空闲", variant: "done" },
                props.selectedProject
                  ? { label: props.selectedProject.patent_type === "invention" ? "发明专利" : "实用新型", variant: "ready" }
                  : null,
              ])}
            >
              <WorkbenchWorkspace
                state={workbenchState}
                handlers={props.projectHandlers}
                onNavigate={(target) => onWorkbenchNavigate(props, target)}
                startWorkspace={workbenchStartWorkspace}
              />
            </PrimarySurface>
          )}
          {route === "documents" && (
            <PrimarySurface
              id="documents"
              title="文稿与修复"
              description="管理内部初稿、正式稿、问题修复和版本链路，把导出前阻断留在同一处处理。"
              statusChips={[
                props.selectedProject
                  ? { label: `项目: ${props.selectedProject.name}`, variant: "current" }
                  : { label: "未选择项目", variant: "warning" },
                { label: props.projectState.currentDraftHash ? "内部初稿已生成" : "暂无内部初稿", variant: props.projectState.currentDraftHash ? "done" : "locked" },
                { label: `材料 ${props.projectState.projectMaterials.length} 份`, variant: "ready" },
              ]}
            >
              <DocumentRepairWorkspace
                projectState={props.projectState}
                handlers={props.projectHandlers}
                exportReadiness={props.postDraftState.exportReadiness}
                onNavigate={props.onSelectSection}
                requestedTab={documentRepairIntent?.tab ?? null}
                onRequestedTabHandled={() => setDocumentRepairIntent(null)}
              />
            </PrimarySurface>
          )}
          {route === "projects-overview" && (
            <PrimarySurface
              id="projects"
              title="项目"
              description="集中查看项目、起草阶段、风险状态和导出准备度，避免在列表里迷路。"
              statusChips={[
                { label: `项目 ${props.projects.length} 个`, variant: "done" },
                { label: props.backendStatus === "online" ? "后端在线" : "后端离线", variant: props.backendStatus === "online" ? "ready" : "error" },
              ]}
            >
              {projectWorkspace(props, "projects")}
            </PrimarySurface>
          )}
          {route === "settings" && (
            <PrimarySurface
              id="settings"
              title="设置"
              description="配置主题、模型接入和智能体运行环境，让系统状态与工作流门禁保持一致。"
              statusChips={[
                { label: `主题: ${props.theme === "dark" ? "深色" : props.theme === "light" ? "浅色" : "系统"}`, variant: "ready" },
                { label: `智能体: ${props.agentDoctor?.run_mode === "partial" ? "部分可用" : props.agentDoctor?.run_mode === "full" ? "完整可用" : props.agentDoctor?.run_mode === "minimal" ? "最小可用" : "未就绪"}`, variant: props.agentDoctor?.run_mode === "full" ? "done" : "warning" },
              ]}
            >
              <div className="px-4 md:px-8 py-4 md:py-6">
                <SettingsPanel theme={props.theme} onThemeChange={props.onChangeTheme} />
              </div>
            </PrimarySurface>
          )}
          {route === "knowledge" && (
            <PrimarySurface
              id="knowledge"
              title="知识库"
              description="沉淀参考材料、语料版本和检索片段，为发明点确认与正文补强提供证据来源。"
              statusChips={[
                { label: `语料版本 ${props.corpusState.corpusVersions.length} 个`, variant: "done" },
                { label: "可导入与检索", variant: "ready" },
              ]}
            >
              <KnowledgeWorkspace
                activeExpertTool={props.activeExpertTool}
                state={props.corpusState}
                handlers={props.corpusHandlers}
                onSelectTool={props.onSelectExpertTool}
              />
            </PrimarySurface>
          )}
          {route === "export" && (
            <PrimarySurface
              id="export"
              title="导出"
              description="分离正式提交稿、内部复核材料和风险追溯，只在门禁满足后开放提交文件。"
              statusChips={[
                { label: exportStatusChip.label, variant: exportStatusChip.variant === "success" ? "done" : exportStatusChip.variant === "busy" ? "current" : exportStatusChip.variant === "error" ? "error" : "warning" },
                { label: props.postDraftState.currentPackage ? "内部初稿就绪" : "待生成内部初稿", variant: props.postDraftState.currentPackage ? "done" : "locked" },
              ]}
            >
              <ExportWorkspace
                postDraftState={props.postDraftState}
                postDraftHandlers={props.postDraftHandlers}
                onNavigateDocuments={navigateDocuments}
              />
            </PrimarySurface>
          )}
          {route === "expert" && (
            <PrimarySurface
              id="expert"
              title="专家工具"
              description="集中处理语料建设、质量检查、授权评估和成稿会审等专业工具。"
              statusChips={[
                { label: `当前工具: ${props.activeExpertTool || "未选择"}`, variant: "current" },
                { label: `报告数: ${props.qualityState.filingReports.length + props.qualityState.grantabilityReports.length} 份`, variant: "ready" },
              ]}
            >
              <ExpertToolsWorkspace
                activeExpertTool={props.activeExpertTool}
                onSelectExpertTool={props.onSelectExpertTool}
                corpusState={props.corpusState}
                corpusHandlers={props.corpusHandlers}
                qualityState={props.qualityState}
                qualityHandlers={props.qualityHandlers}
                postDraftState={props.postDraftState}
                postDraftHandlers={props.postDraftHandlers}
              />
            </PrimarySurface>
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
