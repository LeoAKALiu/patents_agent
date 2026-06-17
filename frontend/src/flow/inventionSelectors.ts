/**
 * Pure invention-point extraction helpers, extracted from GuidedPatentFlow.tsx
 * (M4). These hold the disclosure-run → patent-point-candidate logic that the
 * InventionPointConfirmation panel renders. Moving them out shrinks the
 * 1763-line GuidedPatentFlow and makes the selection rule unit-testable in
 * isolation.
 *
 * Behaviour is byte-identical to the previous inline functions — only the
 * module location changed. The raw-source regression test
 * (GuidedPatentFlowView.test.ts) was updated to point at this module.
 */
import type { DisclosureRun, PatentPointCandidate } from "@/api";

/** Surface candidates from a disclosure run: prefer the settled package,
 *  otherwise fall back to the latest in-flight stage result. */
export function patentPointCandidatesFromDisclosureRun(
  run: DisclosureRun | null,
): PatentPointCandidate[] {
  const packageCandidates = run?.package?.candidates ?? [];
  if (packageCandidates.length > 0) return packageCandidates;
  return patentPointCandidatesFromStageResults(run);
}

/** Walk stage_results newest-first; return the first patent_points payload. */
export function patentPointCandidatesFromStageResults(
  run: DisclosureRun | null,
): PatentPointCandidate[] {
  const stageResults = run?.stage_results ?? [];
  for (let index = stageResults.length - 1; index >= 0; index -= 1) {
    const result = stageResults[index];
    if (result.phase !== "patent_points") continue;
    const payload = result.payload;
    if (isRecord(payload) && Array.isArray(payload.candidates)) {
      return payload.candidates.filter(isPatentPointCandidate);
    }
  }
  return [];
}

export function isPatentPointCandidate(
  value: unknown,
): value is PatentPointCandidate {
  return (
    isRecord(value)
    && typeof value.id === "string"
    && typeof value.title === "string"
    && Array.isArray(value.protection_focus)
    && Array.isArray(value.support_gaps)
    && typeof value.innovation === "string"
    && typeof value.technical_solution === "string"
    && typeof value.evidence_status === "string"
  );
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Human-readable zh-CN label for a candidate's evidence status. */
export function evidenceStatusText(
  status: PatentPointCandidate["evidence_status"],
): string {
  if (status === "verified") return "已验证";
  if (status === "needs_experiment") return "需实验";
  if (status === "feasible_unverified") return "可行未验证";
  return "模型生成";
}
