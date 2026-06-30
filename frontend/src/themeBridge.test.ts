import { describe, expect, it } from "vitest";

// The frontend intentionally does not depend on @types/node. This test still
// needs the real stylesheet text because Vite treats CSS raw imports specially.
// @ts-expect-error node:fs types are not installed in this package.
const { readFileSync } = await import("node:fs");

const testProcess = (globalThis as unknown as { process: { cwd: () => string } }).process;
const stylesSrc = readFileSync(`${testProcess.cwd()}/src/styles.css`, "utf8") as string;

const SHADCN_THEME_COLORS = [
  "background",
  "foreground",
  "card",
  "card-foreground",
  "popover",
  "popover-foreground",
  "primary",
  "primary-foreground",
  "secondary",
  "secondary-foreground",
  "muted",
  "muted-foreground",
  "accent",
  "accent-foreground",
  "destructive",
  "destructive-foreground",
  "border",
  "input",
  "ring",
] as const;

describe("Tailwind theme bridge", () => {
  it("exposes shadcn semantic colors used by shared UI components", () => {
    for (const color of SHADCN_THEME_COLORS) {
      expect(stylesSrc, `${color} must be available as a Tailwind color`).toContain(`--color-${color}:`);
    }
  });
});
