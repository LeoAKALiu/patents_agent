import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  guardedLoad,
  loadDeliberations,
  loadFormulaState,
  loadMaterials,
  loadPatentPoints,
  refreshDisclosureRunUntilSettled,
  type ProjectDataDeps,
} from "./projectData";

// Mock the API module so the loaders never hit the network.
vi.mock("@/api", () => ({
  listProjectPatentPoints: vi.fn(),
  listProjectDisclosures: vi.fn(),
  listProjectDeliberations: vi.fn(),
  listProjectMaterials: vi.fn(),
  listFormulaRuns: vi.fn(),
  listOfficialCompileRuns: vi.fn(),
  listPostDraftReviews: vi.fn(),
  getFormulaRequirement: vi.fn(),
}));

// Import after the mock is registered.
import {
  listProjectPatentPoints,
  listProjectDisclosures,
  listProjectDeliberations,
  listProjectMaterials,
  listFormulaRuns,
  getFormulaRequirement,
} from "@/api";

// Mock call counts leak across tests (shared module-level vi.fn); reset between each.
beforeEach(() => {
  vi.clearAllMocks();
});

function makeDeps(overrides: Partial<ProjectDataDeps> = {}): ProjectDataDeps {
  return {
    isStillSelected: () => true,
    setDeliberationRuns: vi.fn(),
    setProjectMaterials: vi.fn(),
    setDisclosureRuns: vi.fn(),
    setPatentPoints: vi.fn(),
    setPatentPointsProjectId: vi.fn(),
    setFormulaRequirement: vi.fn(),
    setFormulaRuns: vi.fn(),
    setPostDraftReviews: vi.fn(),
    setCurrentDraftHash: vi.fn(),
    setOfficialCompileRuns: vi.fn(),
    setCurrentSourceDraftHash: vi.fn(),
    ...overrides,
  };
}

describe("guardedLoad (shared try/guard/set/catch primitive)", () => {
  it("writes the fetched value when still selected", async () => {
    const setter = vi.fn();
    const ok = await guardedLoad("p", makeDeps(), async () => 42, setter, 0);
    expect(ok).toBe(true);
    expect(setter).toHaveBeenCalledWith(42);
  });

  it("writes the fallback on error when still selected", async () => {
    const setter = vi.fn();
    const ok = await guardedLoad(
      "p",
      makeDeps(),
      async () => {
        throw new Error("x");
      },
      setter,
      99,
    );
    expect(ok).toBe(false);
    expect(setter).toHaveBeenCalledWith(99);
  });

  it("skips the write if the project switched during fetch", async () => {
    const setter = vi.fn();
    const ok = await guardedLoad(
      "p",
      makeDeps({ isStillSelected: () => false }),
      async () => 42,
      setter,
      0,
    );
    expect(ok).toBe(false);
    expect(setter).not.toHaveBeenCalled();
  });
});

describe("guarded loaders (loadDeliberations / loadMaterials / loadFormulaState)", () => {
  it("loadDeliberations writes runs via the shared guard", async () => {
    const runs = [{ id: "d1" }];
    vi.mocked(listProjectDeliberations).mockResolvedValue(runs as never);
    const deps = makeDeps();
    expect(await loadDeliberations("p", deps)).toBe(true);
    expect(deps.setDeliberationRuns).toHaveBeenCalledWith(runs);
  });

  it("loadMaterials writes materials via the shared guard", async () => {
    const mats = [{ id: "m1" }];
    vi.mocked(listProjectMaterials).mockResolvedValue(mats as never);
    const deps = makeDeps();
    expect(await loadMaterials("p", deps)).toBe(true);
    expect(deps.setProjectMaterials).toHaveBeenCalledWith(mats);
  });

  it("loadFormulaState writes the requirement + runs pair", async () => {
    vi.mocked(getFormulaRequirement).mockResolvedValue({ status: "ok" } as never);
    vi.mocked(listFormulaRuns).mockResolvedValue([{ id: "f1" }] as never);
    const deps = makeDeps();
    expect(await loadFormulaState("p", deps)).toBe(true);
    expect(deps.setFormulaRequirement).toHaveBeenCalledWith({ status: "ok" });
    expect(deps.setFormulaRuns).toHaveBeenCalledWith([{ id: "f1" }]);
  });
});

describe("loadPatentPoints", () => {
  it("writes points when the project is still selected", async () => {
    const points = [{ id: "p1" }];
    vi.mocked(listProjectPatentPoints).mockResolvedValue(points as never);
    const deps = makeDeps();
    const ok = await loadPatentPoints("proj", deps);
    expect(ok).toBe(true);
    expect(deps.setPatentPoints).toHaveBeenCalledWith(points);
    expect(deps.setPatentPointsProjectId).toHaveBeenCalledWith("proj");
  });

  it("clears points on failure when still selected", async () => {
    vi.mocked(listProjectPatentPoints).mockRejectedValue(new Error("boom"));
    const deps = makeDeps();
    const ok = await loadPatentPoints("proj", deps);
    expect(ok).toBe(false);
    expect(deps.setPatentPoints).toHaveBeenCalledWith([]);
    expect(deps.setPatentPointsProjectId).toHaveBeenCalledWith("");
  });

  it("skips writes if the project changed during the fetch", async () => {
    vi.mocked(listProjectPatentPoints).mockResolvedValue([{ id: "p1" }] as never);
    const deps = makeDeps({ isStillSelected: () => false });
    const ok = await loadPatentPoints("proj", deps);
    expect(ok).toBe(false);
    expect(deps.setPatentPoints).not.toHaveBeenCalled();
  });
});

describe("refreshDisclosureRunUntilSettled", () => {
  it("stops polling once the run leaves the in-flight state", async () => {
    // First poll: still running. Second poll: completed → should stop.
    vi.mocked(listProjectDisclosures)
      .mockResolvedValueOnce([{ id: "r1", status: "running" }] as never)
      .mockResolvedValueOnce([{ id: "r1", status: "completed" }] as never);
    vi.mocked(listProjectPatentPoints).mockResolvedValue([] as never);
    const deps = makeDeps();
    const noDelay = vi.fn().mockResolvedValue(undefined);

    await refreshDisclosureRunUntilSettled("proj", "r1", deps, noDelay);

    // Two delay ticks (one per poll iteration) before settling.
    expect(noDelay).toHaveBeenCalledTimes(2);
    expect(deps.setDisclosureRuns).toHaveBeenCalledTimes(2);
    expect(listProjectPatentPoints).toHaveBeenCalledTimes(2);
  });

  it("stops early when the user switches project", async () => {
    vi.mocked(listProjectDisclosures).mockResolvedValue([{ id: "r1", status: "running" }] as never);
    const deps = makeDeps({ isStillSelected: () => false });
    const noDelay = vi.fn().mockResolvedValue(undefined);

    await refreshDisclosureRunUntilSettled("proj", "r1", deps, noDelay);

    // First delay awaited, then the guard fires before any fetch.
    expect(noDelay).toHaveBeenCalledTimes(1);
    expect(deps.setDisclosureRuns).not.toHaveBeenCalled();
  });

  it("aborts silently on fetch error", async () => {
    vi.mocked(listProjectDisclosures).mockRejectedValue(new Error("net") as never);
    const deps = makeDeps();
    const noDelay = vi.fn().mockResolvedValue(undefined);

    await refreshDisclosureRunUntilSettled("proj", "r1", deps, noDelay);

    expect(deps.setDisclosureRuns).not.toHaveBeenCalled();
  });
});
