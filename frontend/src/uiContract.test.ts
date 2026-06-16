import { describe, expect, it } from "vitest";
// @ts-expect-error Vitest runs this in Node; avoid adding @types/node for one source-level check.
import { readFileSync } from "node:fs";

import appSource from "./App.tsx?raw";
import guidedSource from "./GuidedPatentFlow.tsx?raw";
import operationConsoleSource from "./ui/OperationConsole.tsx?raw";

const stylesSource = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

describe("next-version UI contract", () => {
  it("declares the approved button and motion tokens", () => {
    expect(stylesSource).toContain("--button-height-default: 44px");
    expect(stylesSource).toContain("--button-height-compact: 36px");
    expect(stylesSource).toContain("--button-size-icon: 32px");
    expect(stylesSource).toContain("--motion-instant: 120ms ease");
    expect(stylesSource).toContain("--motion-guide: 180ms ease");
    expect(stylesSource).toContain("--motion-reveal: 240ms ease-out");
    expect(stylesSource).toContain("@media (prefers-reduced-motion: reduce)");
    expect(stylesSource).not.toContain("letter-spacing: -");
  });

  it("keeps operation logs compact with expandable details", () => {
    expect(operationConsoleSource).toContain("operation-console-summary");
    expect(operationConsoleSource).toContain("<details className=\"operation-console-details\">");
    expect(appSource).toContain("<OperationConsole label={log.label}");
    expect(guidedSource).toContain("import { OperationConsole }");
    expect(guidedSource).toContain("<OperationConsole label={log.label}");
    expect(appSource).not.toContain("max-h-32");
  });
});
