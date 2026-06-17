/**
 * Pure leaf parts extracted from GuidedPatentFlow.tsx (M4, continued).
 *
 * These have no closure over GuidedPatentFlowView's props/state — explicit,
 * narrow props only. Extracted to shrink the 1728-line file. The local
 * ScoreTile here renders the existing `.score-card` class (already migrated
 * to the glass token layer in M5b) and is deliberately kept separate from
 * the richer primitives/ScoreTile to avoid a visual reflow inside the
 * guided quality summary grid.
 */
import type { GuidedActionGate } from "@/guidedFlow";

/**
 * The subset of expert tools a guided step can deep-link into. Shared across
 * step panels so each can type its onOpenExpertTool prop without referencing
 * the parent GuidedPatentFlowProps type.
 */
export type ExpertToolOpener = (
  tool: "materials" | "moat" | "deliberate" | "readiness" | "claimDefense" | "completion" | "export",
) => void;

/** Inline score tile bound to the `.score-card` glass surface. */
export function GuidedScoreTile({ label, value }: { label: string; value: string }) {
  return (
    <article className="score-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

/** Shows the action-gate block reason when a step is locked. */
export function ActionGateHint({ gate }: { gate: GuidedActionGate }) {
  if (gate.allowed || !gate.reason) {
    return null;
  }
  return <p className="workflow-hint">{gate.reason}</p>;
}
