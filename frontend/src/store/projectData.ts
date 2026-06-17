/**
 * Project data-loading layer — extracted from App.tsx (M3 batch B).
 *
 * App.tsx held ~20 async loaders as closures over its useState setters and a
 * selectedProjectIdRef. This module pulls them out as plain functions that take
 * their dependencies explicitly. That separates I/O from rendering, shrinks
 * App.tsx, and makes the load/poll behaviour unit-testable in isolation.
 *
 * Race-guard contract: every setter call is gated by `isStillSelected` so a
 * slow fetch that returns after the user switched projects cannot write
 * stale data into state. This mirrors the in-App original behaviour exactly.
 */
import {
  listProjectDeliberations,
  listProjectDisclosures,
  listProjectMaterials,
  listProjectPatentPoints,
  listFormulaRuns,
  listOfficialCompileRuns,
  listPostDraftReviews,
  getFormulaRequirement,
  type DeliberationRun,
  type DisclosureRun,
  type FormulaNeedAssessment,
  type FormulaRun,
  type OfficialCompileRun,
  type PatentPointCandidate,
  type PostDraftReviewRun,
  type ProjectMaterial,
} from "@/api";

/** Dependencies the loaders need, supplied by the App store. */
export interface ProjectDataDeps {
  /** Returns true if `projectId` is still the active project (race guard). */
  isStillSelected: (projectId: string) => boolean;
  setDeliberationRuns: (runs: DeliberationRun[]) => void;
  setProjectMaterials: (materials: ProjectMaterial[]) => void;
  setDisclosureRuns: (runs: DisclosureRun[]) => void;
  setPatentPoints: (points: PatentPointCandidate[]) => void;
  setPatentPointsProjectId: (projectId: string) => void;
  setFormulaRequirement: (value: FormulaNeedAssessment | null) => void;
  setFormulaRuns: (runs: FormulaRun[]) => void;
  setPostDraftReviews: (runs: PostDraftReviewRun[]) => void;
  setCurrentDraftHash: (hash: string) => void;
  setOfficialCompileRuns: (runs: OfficialCompileRun[]) => void;
  setCurrentSourceDraftHash: (hash: string) => void;
}

/**
 * Generic guarded loader. Captures the repeated try → guard → set → catch
 * pattern shared by all the per-resource loaders: fetch, apply only if the
 * project is still selected, and on failure clear (still-selected only).
 * `fallback` is the failure value written to the setter when still selected.
 */
export async function guardedLoad<T>(
  projectId: string,
  deps: ProjectDataDeps,
  fetch: () => Promise<T>,
  setter: (value: T) => void,
  fallback: T,
): Promise<boolean> {
  try {
    const value = await fetch();
    if (!deps.isStillSelected(projectId)) return false;
    setter(value);
    return true;
  } catch {
    if (deps.isStillSelected(projectId)) setter(fallback);
    return false;
  }
}

/** Reload the patent points for a project; guarded against project switches. */
export async function loadPatentPoints(
  projectId: string,
  deps: ProjectDataDeps,
): Promise<boolean> {
  try {
    const points = await listProjectPatentPoints(projectId);
    if (!deps.isStillSelected(projectId)) return false;
    deps.setPatentPoints(points);
    deps.setPatentPointsProjectId(projectId);
    return true;
  } catch {
    if (deps.isStillSelected(projectId)) {
      deps.setPatentPoints([]);
      deps.setPatentPointsProjectId("");
    }
    return false;
  }
}

export const loadDeliberations = (projectId: string, deps: ProjectDataDeps) =>
  guardedLoad(projectId, deps, () => listProjectDeliberations(projectId), deps.setDeliberationRuns, [] as DeliberationRun[]);

export const loadMaterials = (projectId: string, deps: ProjectDataDeps) =>
  guardedLoad(projectId, deps, () => listProjectMaterials(projectId), deps.setProjectMaterials, [] as ProjectMaterial[]);

export const loadDisclosures = (projectId: string, deps: ProjectDataDeps) =>
  guardedLoad(projectId, deps, () => listProjectDisclosures(projectId), deps.setDisclosureRuns, [] as DisclosureRun[]);

/** Formula state is a (requirement, runs) pair, so it has its own shape. */
export async function loadFormulaState(
  projectId: string,
  deps: ProjectDataDeps,
): Promise<boolean> {
  try {
    const [requirement, runs] = await Promise.all([
      getFormulaRequirement(projectId),
      listFormulaRuns(projectId),
    ]);
    if (!deps.isStillSelected(projectId)) return false;
    deps.setFormulaRequirement(requirement);
    deps.setFormulaRuns(runs);
    return true;
  } catch {
    if (deps.isStillSelected(projectId)) {
      deps.setFormulaRequirement(null);
      deps.setFormulaRuns([]);
    }
    return false;
  }
}

/** Post-draft reviews return a {runs, current_draft_hash} pair. */
export async function loadPostDraftReviews(
  projectId: string,
  deps: ProjectDataDeps,
): Promise<boolean> {
  try {
    const { runs, current_draft_hash } = await listPostDraftReviews(projectId);
    if (!deps.isStillSelected(projectId)) return false;
    deps.setPostDraftReviews(runs);
    deps.setCurrentDraftHash(current_draft_hash);
    return true;
  } catch {
    if (deps.isStillSelected(projectId)) {
      deps.setPostDraftReviews([]);
      deps.setCurrentDraftHash("");
    }
    return false;
  }
}

/** Official compile runs return a {runs, current_source_draft_hash} pair. */
export async function loadOfficialCompileRuns(
  projectId: string,
  deps: ProjectDataDeps,
): Promise<boolean> {
  try {
    const { runs, current_source_draft_hash } = await listOfficialCompileRuns(projectId);
    if (!deps.isStillSelected(projectId)) return false;
    deps.setOfficialCompileRuns(runs);
    deps.setCurrentSourceDraftHash(current_source_draft_hash);
    return true;
  } catch {
    if (deps.isStillSelected(projectId)) {
      deps.setOfficialCompileRuns([]);
      deps.setCurrentSourceDraftHash("");
    }
    return false;
  }
}

/**
 * Poll disclosure runs until the given run leaves the in-flight state,
 * reloading patent points each pass. Same back-off schedule as the original
 * (900/1500/2500/3500/5000/7000 ms). Stops early if the user switches project.
 */
export async function refreshDisclosureRunUntilSettled(
  projectId: string,
  runId: string,
  deps: ProjectDataDeps,
  delay: (ms: number) => Promise<void>,
): Promise<void> {
  const pollDelaysMs = [900, 1500, 2500, 3500, 5000, 7000];
  for (const delayMs of pollDelaysMs) {
    await delay(delayMs);
    if (!deps.isStillSelected(projectId)) return;
    try {
      const runs = await listProjectDisclosures(projectId);
      if (!deps.isStillSelected(projectId)) return;
      deps.setDisclosureRuns(runs);
      await loadPatentPoints(projectId, deps);
      const current = runs.find((item) => item.id === runId);
      if (!current || (current.status !== "queued" && current.status !== "running")) return;
    } catch {
      return;
    }
  }
}
