import type {
  MainSectionId,
  ExpertToolId,
  StartChoiceId,
} from "@/guidedFlow";

/**
 * Routes maps the active main section (and, for the expert section, the
 * active expert tool id) to a "route kind" that the AppRoot component uses
 * to decide which feature workspace to render.
 *
 * The routing decision is pure data — no React, no state, no side effects —
 * so it can be unit-tested without rendering anything.
 */
export type RouteKind =
  | "start-choice"
  | "guided"
  | "projects-overview"
  | "documents"
  | "settings"
  | "knowledge"
  | "export"
  | "expert-corpus"
  | "expert-quality"
  | "expert-post-draft";

/**
 * Translate the active main section into a coarse route kind. Expert tools
 * are folded into one of three feature workspaces: corpus, quality, or
 * post-draft. The expert tool id is still passed in because the workspace
 * itself decides which sub-view to render.
 */
export function resolveRoute(
  activeSection: MainSectionId,
  activeExpertTool: ExpertToolId,
  hasSelectedProject: boolean,
  hasStartChoice: boolean,
): RouteKind {
  if (activeSection === "projects") return "projects-overview";
  if (activeSection === "documents") return "documents";
  if (activeSection === "settings") return "settings";
  if (activeSection === "knowledge") return "knowledge";
  if (activeSection === "export") return "export";
  if (activeSection === "expert") {
    if (activeExpertTool === "build" || activeExpertTool === "corpus") {
      return "expert-corpus";
    }
    if (
      activeExpertTool === "readiness"
      || activeExpertTool === "grantability"
      || activeExpertTool === "claimDefense"
      || activeExpertTool === "completion"
      || activeExpertTool === "review"
    ) {
      return "expert-quality";
    }
    return "expert-post-draft";
  }
  // generate / utility: start choice when nothing picked, otherwise the flow.
  if (!hasSelectedProject && !hasStartChoice) return "start-choice";
  return "guided";
}

/**
 * Group the expert tools into the three feature workspaces. Used by the
 * expert chooser to decide which sub-tool ids belong under each tab.
 */
export const CORPUS_EXPERT_TOOLS: ReadonlyArray<ExpertToolId> = ["build", "corpus"];
export const QUALITY_EXPERT_TOOLS: ReadonlyArray<ExpertToolId> = [
  "readiness",
  "grantability",
  "claimDefense",
  "completion",
  "review",
];
export const POST_DRAFT_EXPERT_TOOLS: ReadonlyArray<ExpertToolId> = [
  "moat",
  "materials",
  "deliberate",
  "write",
  "export",
];

/**
 * Decide whether a given expert tool id is the corpus, quality, or
 * post-draft workspace's responsibility.
 */
export function classifyExpertTool(tool: ExpertToolId): "corpus" | "quality" | "post-draft" {
  if (CORPUS_EXPERT_TOOLS.includes(tool)) return "corpus";
  if (QUALITY_EXPERT_TOOLS.includes(tool)) return "quality";
  return "post-draft";
}

/**
 * Compute the fixed goal mode override used by the guided flow when the
 * user picked the "实用新型" start choice. Used by AppRoot to pass the
 * right prop into ProjectWorkspace.
 */
export function fixedGoalModeFor(
  startChoice: StartChoiceId | null,
  activeSection: MainSectionId,
): "utility" | undefined {
  void activeSection;
  if (startChoice === "utility") return "utility";
  return undefined;
}
