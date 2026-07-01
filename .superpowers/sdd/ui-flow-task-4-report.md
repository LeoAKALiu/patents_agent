# Task 4 Report: Reduce Workbench Routing Noise

## What changed

- Removed the generic no-project primary CTA from the workbench next-step header so the no-project state is driven only by the three explicit start cards.
- Moved selected-project secondary routes under an explicit `其他操作` disclosure.
- Kept `进入文稿与修复` as the dominant primary action when `primaryTarget === "documents"`.
- Added test coverage for both the no-project CTA removal and the secondary-route disclosure behavior.

## Tests and output

### RED

Command:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx
```

Result:

- Failed as expected.
- Failure 1: `创建项目` button still existed in the no-project state.
- Failure 2: `知识库` and `专家工具` were still directly visible instead of being tucked behind a disclosure.

### GREEN

Command:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx src/features/workbench/selectors.test.ts
```

Result:

```text
Test Files  2 passed (2)
Tests       12 passed (12)
```

## TDD evidence

1. Updated `WorkbenchWorkspace.test.tsx` first:
   - changed the no-project assertion to reject the generic `创建项目` CTA
   - added the new `其他操作` disclosure test
2. Ran the focused workbench test and confirmed the expected failures before touching production code.
3. Implemented the minimal production change in `WorkbenchWorkspace.tsx`.
4. Re-ran the focused workbench and selector tests to green.

## Files changed

- `frontend/src/features/workbench/WorkbenchWorkspace.tsx`
- `frontend/src/features/workbench/WorkbenchWorkspace.test.tsx`

## Self-review

- Scope stayed within the two owned files.
- The selected-project state now exposes only the primary route directly and defers secondary routes behind `其他操作`.
- The no-project state no longer shows the generic header CTA and still starts the invention flow from the explicit start card.
- A small implementation detail was needed for test/runtime parity: the disclosure content is hidden unless opened, and the `summary` is explicitly exposed with `role="button"` so the test can interact with it consistently in jsdom.

## Concerns

- The `details` / `summary` interaction needed a small accessibility/test shim (`hidden` gating plus `role="button"` on `summary`) because jsdom did not mirror browser behavior closely enough for the requested test shape. The user-facing behavior still matches the brief.

## Review fix evidence

### Issues addressed

- Removed the non-native `role="button"` override from `<summary>`.
- Kept the disclosure semantic-neutral by retaining native `details` / `summary` semantics and leaving only the `hidden={!otherActionsOpen}` visibility gate.
- Updated the disclosure test to interact with the native `summary` element directly via its text instead of querying it by button role.
- Added the optional assertion that the secondary `文稿与修复` entry is hidden before expansion.

### Review RED

Command:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx
```

Result:

- Failed as expected after the test update.
- Failure: the `summary` element still had `role="button"`, which violated the review requirement.

### Review GREEN

Commands:

```bash
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx
npm --prefix frontend test -- --run src/features/workbench/WorkbenchWorkspace.test.tsx src/features/workbench/selectors.test.ts
```

Results:

```text
WorkbenchWorkspace.test.tsx: 5 passed
WorkbenchWorkspace.test.tsx + selectors.test.ts: 12 passed
```

### Additional self-review

- The fix stayed inside the owned component and test files.
- The disclosure now relies on native browser semantics for `summary`.
- The tests now verify the product-safe contract the reviewer asked for rather than a jsdom-specific role mapping.
