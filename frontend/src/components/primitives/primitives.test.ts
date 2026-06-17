import { describe, expect, it } from "vitest";

/**
 * Primitives structural + design-discipline tests.
 *
 * Project convention: existing tests assert against raw source / module shape
 * (no jsdom/@testing-library is configured for this project). These tests
 * follow that convention while still guarding the contract that matters:
 *   • no hard-coded hex escapes the company-palette token system
 *   • the green-contrast discipline (#1DBF73 never used as text) holds
 *   • variants/sizes/tiers exist and resolve to tokens
 * A full RTL + jsdom render suite is scoped to M5.
 */
import buttonSrc from "./Button.tsx?raw";
import glassCardSrc from "./GlassCard.tsx?raw";
import badgeSrc from "./Badge.tsx?raw";
import bannerSrc from "./Banner.tsx?raw";
import scoreTileSrc from "./ScoreTile.tsx?raw";
import emptyStateSrc from "./EmptyState.tsx?raw";
import spinnerSrc from "./Spinner.tsx?raw";

import * as primitives from "./index";

const ALL_SOURCES = [
  ["Button", buttonSrc],
  ["GlassCard", glassCardSrc],
  ["Badge", badgeSrc],
  ["Banner", bannerSrc],
  ["ScoreTile", scoreTileSrc],
  ["EmptyState", emptyStateSrc],
  ["Spinner", spinnerSrc],
] as const;

describe("primitives barrel", () => {
  it("exports all 7 atoms", () => {
    expect(primitives.Button).toBeTruthy();
    expect(primitives.GlassCard).toBeTruthy();
    expect(primitives.Badge).toBeTruthy();
    expect(primitives.Banner).toBeTruthy();
    expect(primitives.ScoreTile).toBeTruthy();
    expect(primitives.EmptyState).toBeTruthy();
    expect(primitives.Spinner).toBeTruthy();
  });
});

describe("design discipline: no hard-coded hex in any primitive", () => {
  // Strip comment lines (// ... and * ...) before scanning — doc comments
  // legitimately cite palette hex for humans; only CODE must use tokens.
  const stripComments = (src: string) =>
    src
      .split("\n")
      .filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("*"))
      .join("\n");

  for (const [name, src] of ALL_SOURCES) {
    it(`${name} references colour only via tokens`, () => {
      expect(stripComments(src)).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    });
  }
});

describe("design discipline: bright green never used as text", () => {
  // #1DBF73 ≈ 2.2:1 on light glass → FAILS contrast as text. It may appear
  // only as a fill / progress / status colour. Banner success tone must use
  // the darkened success text token, not the bright green.
  it("Banner success tone uses --success-strong, not --success as text", () => {
    expect(bannerSrc).toContain("var(--success-strong)");
    expect(bannerSrc).not.toMatch(/text-\[var\(--success\)\]/);
  });
  it("Badge success variant is a FILL (no text-[var(--success)])", () => {
    expect(badgeSrc).toContain("bg-[var(--brand-green-100)]");
    expect(badgeSrc).not.toMatch(/text-\[var\(--success\)\]/);
  });
});

describe("Button variants resolve to the right tokens", () => {
  it("default = accent-blue primary CTA (reserved list)", () => {
    expect(buttonSrc).toContain("bg-[var(--action-primary)]");
  });
  it("danger = destructive token", () => {
    expect(buttonSrc).toContain("bg-[var(--danger)]");
  });
  it("sizes include control-h (40px) and control-touch (44px)", () => {
    expect(buttonSrc).toContain("var(--control-h)");
    expect(buttonSrc).toContain("var(--control-touch)");
  });
  it("motion is transform-only (active scale, no layout anim)", () => {
    expect(buttonSrc).toContain("active:scale");
    expect(buttonSrc).not.toMatch(/animate-\[.*(width|height|padding)/);
  });
});

describe("GlassCard tiers + modifiers", () => {
  it("maps three frost tiers to .glass-* classes", () => {
    expect(glassCardSrc).toContain("glass-soft");
    expect(glassCardSrc).toContain('"glass"');
    expect(glassCardSrc).toContain("glass-strong");
  });
  it("selected modifier applies the accent ring", () => {
    expect(glassCardSrc).toContain("is-selected");
  });
});

describe("ScoreTile progress is accessible + green-only-as-fill", () => {
  it("renders a progressbar role with aria-valuenow", () => {
    expect(scoreTileSrc).toContain('role="progressbar"');
    expect(scoreTileSrc).toContain("aria-valuenow");
  });
  it("uses --success only as a bar fill, never as text", () => {
    expect(scoreTileSrc).toContain("var(--success)");
    expect(scoreTileSrc).not.toMatch(/text-\[var\(--success\)\]/);
  });
});
