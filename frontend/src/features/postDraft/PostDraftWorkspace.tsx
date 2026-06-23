import type { FormEvent } from "react";

import { ExportView } from "@/views/exportView";
import {
  DeliberationView,
  DisclosureView,
  MoatView,
} from "@/views/pipelineViews";
import { WriteView } from "@/views/expertViews";

import type {
  AgentDoctorReport,
  DeliberationRun,
  DisclosureRun,
  DraftPackage,
  FormulaNeedAssessment,
  FormulaRun,
  OfficialCompileRun,
  PatentPointCandidate,
  PatentPointCreatePayload,
  PostDraftReviewRun,
  ProjectMaterial,
  ProjectRecord,
} from "@/api";

/**
 * State slice consumed by the "post-draft" workspace: moat (invention
 * points), materials, deliberation, write (draft generation), and export.
 */
export interface PostDraftWorkspaceState {
  selectedProject: ProjectRecord | null;
  agentDoctor: AgentDoctorReport | null;
  /** The patent-point candidates scoped to the active project. */
  visiblePatentPoints: PatentPointCandidate[];
  projectMaterials: ProjectMaterial[];
  disclosureRuns: DisclosureRun[];
  deliberationRuns: DeliberationRun[];
  /** The most recent completed disclosure run (if any). */
  currentDisclosure: DisclosureRun | null;
  /** The most recent completed deliberation run (if any). */
  currentDeliberation: DeliberationRun | null;
  formulaRequirement: FormulaNeedAssessment | null;
  currentFormulaRun: FormulaRun | null;
  currentPackage: DraftPackage | null;
  latestOfficialCompileRun: OfficialCompileRun | null;
  latestPostDraftReview: PostDraftReviewRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  selectedDeliberationProviders: string[];
  lastExport: {
    format: "docx" | "md" | "sidecar";
    filePath: string;
    byteCount: number;
    officialPackageHash?: string;
  } | null;
  busy: string;
  desktopDialogsAvailable: boolean;
}

export interface PostDraftWorkspaceHandlers {
  // Moat / patent points
  onCreatePatentPoint: (payload: PatentPointCreatePayload) => Promise<boolean>;
  onSelectPatentPoint: (point: PatentPointCandidate) => Promise<void>;
  onDeletePatentPoint: (point: PatentPointCandidate) => Promise<void>;
  onEvaluatePatentPointMoat: () => Promise<void>;
  // Materials
  onUploadMaterial: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onStartDisclosure: (trace?: boolean) => Promise<void>;
  onRefreshDisclosures: () => Promise<void>;
  onCancelDisclosureRun: (runId: string) => Promise<void>;
  onRetryDisclosureRun: (runId: string) => Promise<void>;
  // Deliberation
  onStartDeliberation: (trace?: boolean) => Promise<void>;
  onToggleDeliberationProvider: (providerId: string, enabled: boolean) => void;
  onRefreshDeliberations: () => Promise<void>;
  onCancelDeliberationRun: (runId: string) => Promise<void>;
  onRetryDeliberationRun: (runId: string) => Promise<void>;
  // Write (draft generation)
  onGenerate: () => Promise<void>;
  // Export
  onNativeExport: (format: "docx" | "md" | "sidecar") => Promise<void> | void;
  onOpenExportFolder: () => Promise<void> | void;
}

/** Which post-draft sub-tool is currently active. */
export type PostDraftTool =
  | "moat"
  | "materials"
  | "deliberate"
  | "write"
  | "export";

export interface PostDraftWorkspaceProps {
  tool: PostDraftTool;
  state: PostDraftWorkspaceState;
  handlers: PostDraftWorkspaceHandlers;
}

/**
 * Routes the active post-draft sub-tool to its view. Pure presentational
 * — the active tool id is decided by the parent (App.tsx).
 */
export function PostDraftWorkspace({ tool, state, handlers }: PostDraftWorkspaceProps) {
  switch (tool) {
    case "moat":
      return (
        <MoatView
          project={state.selectedProject}
          points={state.visiblePatentPoints}
          busy={state.busy}
          onCreate={handlers.onCreatePatentPoint}
          onSelect={handlers.onSelectPatentPoint}
          onDelete={handlers.onDeletePatentPoint}
          onEvaluateMoat={handlers.onEvaluatePatentPointMoat}
        />
      );
    case "materials":
      return (
        <DisclosureView
          project={state.selectedProject}
          materials={state.projectMaterials}
          runs={state.disclosureRuns}
          busy={state.busy}
          onUpload={handlers.onUploadMaterial}
          onStart={handlers.onStartDisclosure}
          onRefresh={handlers.onRefreshDisclosures}
          onCancelRun={handlers.onCancelDisclosureRun}
          onRetryRun={handlers.onRetryDisclosureRun}
        />
      );
    case "deliberate":
      return (
        <DeliberationView
          project={state.selectedProject}
          doctor={state.agentDoctor}
          runs={state.deliberationRuns}
          disclosure={state.currentDisclosure}
          selectedProviders={state.selectedDeliberationProviders}
          busy={state.busy}
          onStart={handlers.onStartDeliberation}
          onToggleProvider={handlers.onToggleDeliberationProvider}
          onRefresh={handlers.onRefreshDeliberations}
          onCancelRun={handlers.onCancelDeliberationRun}
          onRetryRun={handlers.onRetryDeliberationRun}
        />
      );
    case "write":
      return (
        <WriteView
          project={state.selectedProject}
          deliberation={state.currentDeliberation}
          disclosure={state.currentDisclosure}
          formulaRequirement={state.formulaRequirement}
          formulaRun={state.currentFormulaRun}
          busy={state.busy}
          onGenerate={() => void handlers.onGenerate()}
        />
      );
    case "export":
      return (
        <ExportView
          project={state.selectedProject}
          packageValue={state.currentPackage}
          postDraftReview={state.latestPostDraftReview}
          officialCompileRun={state.latestOfficialCompileRun}
          currentDraftHash={state.currentDraftHash}
          currentSourceDraftHash={state.currentSourceDraftHash}
          lastExport={state.lastExport}
          onNativeExport={(format) => void handlers.onNativeExport(format)}
          onOpenExportFolder={() => void handlers.onOpenExportFolder()}
          desktopDialogsAvailable={state.desktopDialogsAvailable}
        />
      );
  }
}
