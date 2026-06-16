# Next Version UI Visual Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved next-version UI-SPEC with less visible text, unified button sizing, light motion, and consistent shell/workflow styling.

**Architecture:** Keep the lazy path: CSS variables plus the existing React components. No new component library, no new animation dependency, and no shell rewrite. The main behavior change is reusing `OperationConsole` for compact run details.

**Tech Stack:** React 19, Vite, Vitest, Tailwind v4 import, plain CSS variables, `lucide-react`.

---

## File Structure

- Create `frontend/src/uiContract.test.ts`: source-level regression checks for the UI-SPEC contract.
- Modify `frontend/src/styles.css`: button tokens, motion tokens, compact text rules, reduced-motion handling, operation console styles.
- Modify `frontend/src/ui/OperationConsole.tsx`: show one-line summary and expandable technical details.
- Modify `frontend/src/App.tsx`: reuse `OperationConsole` for the global busy console.
- Modify `frontend/src/GuidedPatentFlow.tsx`: reuse `OperationConsole` for guided step consoles.
- Keep `docs/ui/2026-06-16-next-version-UI-SPEC.md` in the PR as the source contract.

---

### Task 1: UI Contract Regression Test

**Files:**
- Create: `frontend/src/uiContract.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- uiContract.test.ts`

Expected: FAIL because button/motion tokens and compact console markup do not exist yet.

---

### Task 2: CSS Contract

**Files:**
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/uiContract.test.ts`

- [ ] **Step 1: Implement minimal CSS tokens and rules**

Add button and motion variables to `:root`, update existing button classes to use those variables, add `.motion-reveal`, `.operation-console*`, compact `.workflow-hint`, and reduced-motion handling.

Required declarations:

```css
--button-height-default: 44px;
--button-height-compact: 36px;
--button-size-icon: 32px;
--button-size-icon-prominent: 40px;
--motion-instant: 120ms ease;
--motion-guide: 180ms ease;
--motion-reveal: 240ms ease-out;
```

- [ ] **Step 2: Run contract test**

Run: `npm run test -- uiContract.test.ts`

Expected: still FAIL until Task 3 updates React components.

---

### Task 3: Compact Operation Console

**Files:**
- Modify: `frontend/src/ui/OperationConsole.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/GuidedPatentFlow.tsx`
- Test: `frontend/src/uiContract.test.ts`

- [ ] **Step 1: Rework `OperationConsole`**

Use the first log line as always-visible summary and put the remaining lines inside native `<details>`.

```tsx
const [summaryLine, ...detailLines] = lines;
```

Visible detail label: `技术详情`

- [ ] **Step 2: Reuse it in app/guided consoles**

Replace duplicated busy console markup in `App.tsx` and `GuidedPatentFlow.tsx` with:

```tsx
<OperationConsole label={log.label} lines={log.lines} elapsedSeconds={log.elapsedSeconds} />
```

- [ ] **Step 3: Verify**

Run:

```bash
npm run test -- uiContract.test.ts
npm run test
npm run build
```

Expected: all pass.

---

## Self-Review

Spec coverage:
- Less text: Task 3 compact logs and Task 2 line-clamped hints.
- Motion: Task 2 motion tokens, reveal class, reduced-motion guard.
- Button alignment: Task 2 button tokens and shared sizes.
- Unified style: Task 2 style tokens plus Task 3 shared operation console.
- Registry safety: no new dependency or registry.

Placeholder scan: none.

Type consistency: all paths and component names match current source.
