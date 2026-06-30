import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GuidedPatentFlowView, type GuidedPatentFlowProps } from "./GuidedPatentFlow";
import type { ProjectMaterial, ProjectRecord } from "./api";

const project: ProjectRecord = {
  id: "project-1",
  name: "材料计数项目",
  draft_text: "一种基于图像采集的检测方法。",
  patent_type: "invention",
  package: null,
  created_at: "2026-06-27T00:00:00Z",
  updated_at: "2026-06-27T00:00:00Z",
  applicant: "",
  inventors: "",
  technical_field: "",
  background: "",
  pain_point: "",
  technical_solution: "",
  innovation: "",
  embodiments: "",
  beneficial_effects: "",
};

const processedMaterial: ProjectMaterial = {
  id: "m-processed",
  project_id: project.id,
  file_name: "valid.md",
  path: "data/project-materials/project-1/valid.md",
  file_type: "md",
  text: "有效材料",
  status: "processed",
  warnings: [],
  metadata: {},
};

const failedMaterial: ProjectMaterial = {
  id: "m-failed",
  project_id: project.id,
  file_name: "unsupported-round5.xyz",
  path: "data/project-materials/project-1/unsupported-round5.xyz",
  file_type: "xyz",
  text: "",
  status: "failed",
  warnings: ["Unsupported project material file type: .xyz"],
  metadata: {},
};

const noop = () => undefined;
const asyncNoop = async () => undefined;

function renderGuidedFlow(materials: ProjectMaterial[]) {
  const props: GuidedPatentFlowProps = {
    project,
    materials,
    disclosures: [],
    deliberations: [],
    patentPoints: [],
    formulaRequirement: null,
    formulaRuns: [],
    officialCompileRuns: [],
    currentSourceDraftHash: "",
    postDraftReviews: [],
    currentDraftHash: "",
    currentPackage: null,
    agentDoctor: null,
    selectedDeliberationProviders: [],
    selectedDeliberationParticipantProviders: [],
    selectedFormulaProviders: [],
    filingReports: [],
    worksheets: [],
    completionRuns: [],
    externalDraftSources: [],
    externalDraftIntakeRuns: [],
    busy: "",
    busyElapsedSeconds: 0,
    onCreateIdeaProject: asyncNoop,
    onCreateExternalDraft: asyncNoop,
    onUploadExternalDraft: asyncNoop,
    onStartExternalDraftIntake: asyncNoop,
    onConfirmExternalDraftIntake: asyncNoop,
    onUploadMaterial: noop,
    disclosureResearchMode: "standard",
    onChangeDisclosureResearchMode: noop,
    onStartDisclosure: noop,
    onCancelDisclosureRun: noop,
    onRetryDisclosureRun: noop,
    onSelectPatentPoint: noop,
    onStartDeliberation: noop,
    onCancelDeliberationRun: noop,
    onRetryDeliberationRun: noop,
    onStartFormula: noop,
    onCancelFormulaRun: noop,
    onRetryFormulaRun: noop,
    onStartOfficialCompile: noop,
    onStartKimiLanguagePolish: noop,
    onStartPostDraftReview: noop,
    onApplyOfficialCompileCleanup: noop,
    onApplyPostDraftSafePatches: noop,
    onSaveDraftPackage: noop,
    onCancelPostDraftReviewRun: noop,
    onRetryPostDraftReviewRun: noop,
    onToggleDeliberationProvider: noop,
    onToggleDeliberationParticipantProvider: noop,
    onToggleFormulaProvider: noop,
    onGenerateDraft: noop,
    onRunQualityChecks: noop,
    onImproveScore: noop,
    onAcceptPatch: noop,
    onAcceptAllPatches: noop,
    onOpenExpertTool: noop,
  };
  return render(<GuidedPatentFlowView {...props} />);
}

describe("guided material status", () => {
  it("counts only processed materials in the invention confirmation upload prompt", () => {
    renderGuidedFlow([failedMaterial, processedMaterial]);

    expect(screen.getByText("当前已有 1 份可用材料，1 份失败上传。")).toBeTruthy();
    expect(screen.queryByText("当前已有 2 份材料。")).toBeNull();
  });
});
