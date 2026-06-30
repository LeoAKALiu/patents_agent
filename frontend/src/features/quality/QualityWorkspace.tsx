import {
  ClaimDefenseView,
  GrantabilityView,
  ReviewView,
} from "@/views/qualityViews";
import {
  DraftCompletionView,
  FilingReadinessView,
} from "@/views/filingViews";

import type {
  ClaimDefenseWorksheet,
  DraftCompletionRun,
  FilingReadinessReport,
  GrantabilityReport,
  OfficialCompileRun,
  PostDraftReviewRun,
  ProjectKnowledgeOverview,
  ProjectRecord,
} from "@/api";

/**
 * State slice consumed by the "quality" workspace: filing readiness,
 * grantability, claim defense, draft completion, and review expert tools.
 */
export interface QualityWorkspaceState {
  selectedProject: ProjectRecord | null;
  projectKnowledge: ProjectKnowledgeOverview | null;
  filingReports: FilingReadinessReport[];
  latestFilingReport: FilingReadinessReport | null;
  grantabilityReports: GrantabilityReport[];
  latestGrantabilityReport: GrantabilityReport | null;
  worksheets: ClaimDefenseWorksheet[];
  latestWorksheet: ClaimDefenseWorksheet | null;
  completionRuns: DraftCompletionRun[];
  latestCompletionRun: DraftCompletionRun | null;
  latestOfficialCompileRun: OfficialCompileRun | null;
  latestPostDraftReview: PostDraftReviewRun | null;
  currentDraftHash: string;
  currentSourceDraftHash: string;
  busy: string;
}

export interface QualityWorkspaceHandlers {
  onRunFilingReadiness: () => Promise<void> | void;
  onCreateGrantabilityReport: () => Promise<void> | void;
  onCreateWorksheet: () => Promise<void> | void;
  onRunDraftCompletion: () => Promise<void> | void;
  onImproveScore: () => Promise<void> | void;
  onCompletionPatch: (runId: string, patchId: string, action: "accept" | "reject") => Promise<void> | void;
  onReview: () => Promise<void> | void;
}

/** Which quality sub-tool is currently active. */
export type QualityTool =
  | "readiness"
  | "grantability"
  | "claimDefense"
  | "completion"
  | "review";

export interface QualityWorkspaceProps {
  tool: QualityTool;
  state: QualityWorkspaceState;
  handlers: QualityWorkspaceHandlers;
}

/**
 * Routes the active quality sub-tool to its view. The route is decided by
 * the parent (App.tsx) which owns the active expert tool id; this component
 * is pure presentational.
 */
export function QualityWorkspace({ tool, state, handlers }: QualityWorkspaceProps) {
  switch (tool) {
    case "readiness":
      return (
        <FilingReadinessView
          project={state.selectedProject}
          report={state.latestFilingReport}
          reports={state.filingReports}
          postDraftReview={state.latestPostDraftReview}
          officialCompileRun={state.latestOfficialCompileRun}
          currentDraftHash={state.currentDraftHash}
          currentSourceDraftHash={state.currentSourceDraftHash}
          busy={state.busy}
          onRun={() => void handlers.onRunFilingReadiness()}
        />
      );
    case "grantability":
      return (
        <GrantabilityView
          project={state.selectedProject}
          projectKnowledge={state.projectKnowledge}
          report={state.latestGrantabilityReport}
          reports={state.grantabilityReports}
          busy={state.busy}
          onGenerate={() => void handlers.onCreateGrantabilityReport()}
        />
      );
    case "claimDefense":
      return (
        <ClaimDefenseView
          project={state.selectedProject}
          worksheet={state.latestWorksheet}
          worksheets={state.worksheets}
          busy={state.busy}
          onGenerate={() => void handlers.onCreateWorksheet()}
        />
      );
    case "completion":
      return (
        <DraftCompletionView
          project={state.selectedProject}
          run={state.latestCompletionRun}
          runs={state.completionRuns}
          busy={state.busy}
          onRun={() => void handlers.onRunDraftCompletion()}
          onImprove={() => void handlers.onImproveScore()}
          onPatch={(runId, patchId, action) =>
            void handlers.onCompletionPatch(runId, patchId, action)
          }
        />
      );
    case "review":
      return <ReviewView project={state.selectedProject} busy={state.busy} onReview={() => void handlers.onReview()} />;
  }
}
