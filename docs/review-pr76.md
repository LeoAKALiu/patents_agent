# Code Review: PR #76 — Align next UI visual guidance

**Branch:** `codex/next-ui-visual-guidance` (commit `729afbe`)
**Base:** `origin/release/v1.1.0` (post PR #73 merge)
**Date:** 2026-06-16 · **Reviewer:** MiMoCode (updated after Claude cross-review)

---

## 1. Change Summary

| Metric | Value |
|--------|-------|
| Files changed | 7 |
| Lines added | 521 |
| Lines deleted | 37 |

The PR adds a UI-SPEC and implementation plan, then implements the visual guidance: CSS motion/button tokens, reduced-motion handling, compact workflow hints, and unified OperationConsole styling.

### Files

| File | Change |
|------|--------|
| `docs/ui/2026-06-16-next-version-UI-SPEC.md` | NEW — design contract (208 lines) |
| `docs/superpowers/plans/2026-06-16-next-version-ui-visual-guidance.md` | NEW — implementation plan (154 lines) |
| `frontend/src/styles.css` | CSS tokens, motion, compact console, reduced-motion |
| `frontend/src/ui/OperationConsole.tsx` | Reworked: summary + expandable `<details>` |
| `frontend/src/App.tsx` | Replace inline `BusyOperationConsole` with `<OperationConsole>` |
| `frontend/src/GuidedPatentFlow.tsx` | Replace inline `GuidedOperationConsole` with `<OperationConsole>` |
| `frontend/src/uiContract.test.ts` | NEW — source-level contract regression tests |

### Test Results

| Suite | Result |
|-------|--------|
| `uiContract.test.ts` | ✅ 2 passed |
| `npm run build` | ✅ 1695 modules, 386 KB JS, 87 KB CSS |

---

## 2. ✅ Strengths

1. **CSS variables replace magic numbers.** Button heights and motion durations centralized in `:root`.
2. **`<details>` for expandable logs.** Native HTML element — no JS state, accessible by default.
3. **Reduced-motion handling.** `prefers-reduced-motion: reduce` block present. Required for vestibular accessibility.
4. **No new dependencies.** Pure CSS + existing React.
5. **Contract test prevents token regression.** `uiContract.test.ts` verifies tokens exist and class names are correct.
6. **Code deduplication.** Two inline console implementations replaced by one shared component.

---

## 3. Issues

### 🔴 3.1 Console unification is incomplete — `GuidedRuntimeConsole` still uses old markup

`GuidedPatentFlow.tsx:907-942` — A **third** console consumer, `GuidedRuntimeConsole`, still renders with `.inline-console` / `.console-heading` markup. It is called from 4 sites:

- Line 1086: 发明点提炼运行中
- Line 1209: 会审运行中
- Line 1332: 核心公式运行中
- Line 1634: 成稿会审运行中

The PR migrated `BusyOperationConsole` (App.tsx) and `GuidedOperationConsole` (GuidedPatentFlow.tsx) but missed this one. Result: two visually divergent console treatments coexist — `operation-console` with reveal animation and tokens vs `inline-console` without. The old CSS rules at `styles.css:897-920` are kept alive by this consumer.

**Recommendation:** Migrate `GuidedRuntimeConsole` to use `<OperationConsole>` or explicitly carve it out in the SPEC as intentionally different.

### 🔴 3.2 Token rollout skipped high-traffic selectors

The SPEC tokens were added to `:root` but several major selectors still hardcode values:

| Selector | Hardcoded | Should be |
|----------|-----------|-----------|
| `.nav-link` (`styles.css:224`) | `min-height: 44px` | `var(--button-height-default)` |
| `.nav-link` (`styles.css:234`) | `transition: ... .12s` | `var(--motion-instant)` |
| `.guided-progress-meter span` (`styles.css:1662`) | `transition: width .16s ease` | `var(--motion-guide)` (SPEC: "Progress width") |
| `.guided-step` (`styles.css:1680`) | `transition: ... .12s` | `var(--motion-instant)` |
| 8+ other selectors | `transition: ... .12s` | `var(--motion-instant)` |

Total: **13+ transition declarations** still use hardcoded `.12s` instead of `var(--motion-instant)`. The `.nav-link` selector is the entire sidebar nav — arguably the highest-traffic interactive surface.

The token contract is currently aspirational: any future "tweak motion" change still has to touch multiple selectors manually, defeating the purpose of centralizing the values.

**Recommendation:** Migrate at minimum `.nav-link`, `.guided-step`, and `.guided-progress-meter span` to use the declared tokens.

### 🟡 3.3 Two declared tokens have zero consumers

| Token | Declared at | Used at |
|-------|-------------|---------|
| `--button-size-icon-prominent: 40px` | `styles.css:60` | **nowhere** |
| `--motion-guide: 180ms ease` | `styles.css:62` | **nowhere** |

The contract test (`uiContract.test.ts`) requires both tokens be *declared* but doesn't require they be *used*. They will silently rot.

SPEC says `--motion-guide` is for "Progress width, current-step highlight, status dot changes" and `--button-size-icon-prominent` is for "40px square prominent" toolbar actions. Neither was wired up.

**Recommendation:** Either delete the tokens or wire up the SPEC-stated consumers. Add a test assertion that tokens are *used* (not just declared).

### 🟡 3.4 Reduced-motion implementation contradicts the SPEC

**SPEC** (line 67): "Respect `prefers-reduced-motion: reduce` by disabling reveal/guide movement **and keeping opacity changes only.**"

**Implementation** (`styles.css:1959-1969`):
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 1ms !important;
    transition-duration: 1ms !important;
  }
}
```

This kills **all** animation including the opacity fade-in. Reduced-motion users get jump-cut reveals instead of opacity-only reveals.

**Recommendation:** Override `transform: none !important` while keeping opacity transitions alive, or create a reduced-motion variant of `reveal-in` that omits the `translateY`.

### 🟡 3.5 Workflow-hint clamp: 2 lines, no toggle — double SPEC violation

**SPEC** (line 78): "**Max 1 line in normal state. Use detail toggles for long reasons.**"

**Implementation** (`styles.css:1366-1374`):
```css
.workflow-hint {
  -webkit-line-clamp: 2;   /* SPEC says 1 line */
  overflow: hidden;          /* no toggle mechanism */
}
```

Two violations:
1. Line count: 2 lines instead of SPEC's 1 line
2. No escape hatch: truncated hints have no `<details>`, hover, or tooltip

Actionable hints like "请先上传 DeepResearch 报告 (会进入 …)" can be silently hidden mid-sentence.

**Recommendation:** Either implement `<details>` for long hints, or reduce to 1 line and ensure all current hints fit.

### 🟡 3.6 Icon-button touch target halved without rationale

`.btn-icon` (`styles.css:682-686`) went from `width: 44px` (44×44 via inherited `min-height`) to `width: 32px; min-height: 32px` — a ~47% area reduction.

This follows SPEC line 123 ("32px square compact"), but the SPEC doesn't justify why 44px touch-grade targets needed to shrink. For a macOS/Tauri mouse-driven app this is acceptable, but the rationale should be recorded.

### 🟢 3.7 Implementation checklist item unticked

`UI-SPEC.md:195`: "Verify installed app flow manually after packaging, not just frontend build" — unchecked. Since PR #73 removed Electron and CI no longer builds Tauri, this manual verification step is the only proof that a real DMG renders these styles correctly.

### 🟢 3.8 `letter-spacing: -` contract assertion is overbroad

`uiContract.test.ts:28`:
```ts
expect(stylesSource).not.toContain("letter-spacing: -");
```

Global substring assertion. If a future change adds `letter-spacing: -0.02em` for a legitimate reason, this test blocks it. Should scope to the three original selectors (`.brand`, `.section-heading`, `.card-title`).

### 🟢 3.9 `prefers-reduced-motion` uses global `*` selector

The `*` override is heavy-handed. The explicit per-class block below it (`.motion-reveal`, `.operation-console`, etc.) already handles the project's own animations. The `*` block may be redundant.

### 🟢 3.10 OperationConsole spinner runs while collapsed

`OperationConsole.tsx:21` — `Loader2` spinner renders even when details are collapsed and the operation is complete. Should be replaced with a check icon or hidden on completion.

### 🟢 3.11 Reveal animation fires on all panels simultaneously

`.reveal-in` is applied to `.guided-panel`, `.guided-choice`, `.start-choice-card` — all animate at once on step change, creating a "wall of movement." Consider staggering or limiting to the current step.

---

## 4. Merge Conflict Risk

PRs #74, #75, and #76 all modify `App.tsx` and `GuidedPatentFlow.tsx`. PR #76 is based on `release/v1.1.0` (post PR #73), while #74/#75 branch from an earlier commit.

| File | PR #74 | PR #75 | PR #76 |
|------|--------|--------|--------|
| `App.tsx` | ✅ | ✅ | ✅ |
| `GuidedPatentFlow.tsx` | ✅ | ✅ | ✅ |
| `styles.css` | — | — | ✅ |
| `ui/OperationConsole.tsx` | — | — | ✅ |

**Recommendation:** Merge PR #76 last. Its changes are cosmetic and localized; #74/#75 add functional logic that takes priority.

---

## 5. Risk Matrix

| # | Risk | Severity | Likelihood |
|---|------|----------|------------|
| 3.1 | `GuidedRuntimeConsole` not migrated — 4 call sites use old markup | 🔴 High | Certain |
| 3.2 | 13+ selectors still hardcode `.12s` / `44px` — tokens are aspirational | 🔴 High | Certain |
| 3.3 | `--button-size-icon-prominent` and `--motion-guide` have zero consumers | 🟡 Important | Certain |
| 3.4 | Reduced-motion kills opacity — contradicts SPEC "opacity changes only" | 🟡 Important | Certain |
| 3.5 | Workflow-hint: 2-line clamp, no toggle — double SPEC violation | 🟡 Important | Certain |
| 3.6 | Icon-button 44→32px — no rationale in SPEC | 🟢 Minor | Low |
| 3.7 | Manual verification checklist unticked | 🟢 Minor | Medium |
| 3.8 | Overbroad `letter-spacing` assertion | 🟢 Minor | Low |
| — | Merge conflict with PRs #74/#75 | 🟡 Important | Certain |

---

## 6. Verdict

PR #76 is a **partial implementation of its own SPEC**. The documentation and contract-test discipline are good, but:

- Console unification is incomplete (3.1) — one of three consumers was missed
- Token rollout is incomplete (3.2) — the highest-traffic selectors still hardcode values
- Two tokens are declared but never used (3.3)
- Reduced-motion behavior contradicts the SPEC (3.4) — opacity is killed, not preserved
- Workflow-hint truncation violates SPEC twice (3.5) — wrong line count, no toggle

None are launch-blocking, but **3.1, 3.2, and 3.5 should land before claiming the visual-guidance phase is done**. Otherwise the next developer following the SPEC tokens will find half the codebase uses them and half doesn't, and the contract tests won't tell them which is which.

**Recommendation:** Fix 3.5 (user-visible content bug) before merge. Merge after PRs #74/#75. Open a follow-up for 3.1, 3.2, 3.3, 3.4.
