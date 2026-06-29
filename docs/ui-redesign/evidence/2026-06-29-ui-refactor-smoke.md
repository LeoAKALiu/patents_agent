# 2026-06-29 UI Refactor Smoke

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29`
- Branch: `codex/ui-refactor-2026-06-29`
- HEAD at start: `a4c66e15`
- Dirty at start: `no`
- Evidence type: dev-server evidence only

## Commands Run

```bash
pwd
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
cd frontend && npm run build
cd frontend && npm test
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
git diff --check
```

## Dev Server

- Requested URL: `http://127.0.0.1:5173/`
- Actual URL used for evidence: `http://127.0.0.1:5174/`
- Reason: port `5173` was already in use, so Vite selected the next free port.

## Viewport Smoke

### Desktop

- Viewport: `1440x1100`
- Sidebar top-level destinations: `7`
  - `工作台`
  - `项目`
  - `文稿与修复`
  - `知识库`
  - `专家工具`
  - `导出`
  - `设置`
- Workbench:
  - no horizontal overflow observed
  - one visible primary CTA confirmed: `创建项目`
- Document repair workspace:
  - tabs visible: `总览 / 编辑 / 问题 / 标注修复 / 版本`
  - no horizontal overflow observed
  - current offline state did not expose an enabled `打开标注式修复编辑器` entry, so long-list pane scrolling was not fully proven against live repair data
- Export workspace:
  - no horizontal overflow observed
  - separation of export zones visually confirmed:
    - `正式提交稿`
    - `内部复核材料`
    - `风险说明与追溯`

### Mobile

- Viewport: `390x844`
- Mobile nav destinations visible: `7`
- Mobile nav stayed within its own container bounds
- No horizontal overflow observed
- Button labels remained separated without text overlap in the checked view

## Screenshots

- `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29/docs/ui-redesign/evidence/screenshots/task-8-desktop-workbench.png`
- `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29/docs/ui-redesign/evidence/screenshots/task-8-desktop-document-repair.png`
- `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29/docs/ui-redesign/evidence/screenshots/task-8-desktop-export.png`
- `/Users/leo/Projects/patents_agent/.worktrees/ui-refactor-2026-06-29/docs/ui-redesign/evidence/screenshots/task-8-mobile-workbench.png`

## Notes

- This file records dev-server evidence only. It does **not** prove packaged Tauri app or DMG behavior.
- If packaged UI evidence is requested later, follow:
  - `docs/release/dmg-ui-regression-guard.md`
  - `docs/release/v1.1.0-tauri-release-gate.md`
  - `docs/release/v1.1.0-tauri-packaging.md`

## Controller Follow-Up Smoke

- After the initial smoke, the export lock guidance copy was updated so the export page no longer repeats repair-action labels.
- Re-ran browser smoke against `http://127.0.0.1:5174/`.
- Refreshed `docs/ui-redesign/evidence/screenshots/task-8-desktop-export.png` from the current live dev server after the copy fix.
- Confirmed the export body contains `正式提交稿`, `内部复核材料`, and `风险说明与追溯`.
- Confirmed the export body and refreshed screenshot no longer contain `人工修正`, `一键AI修正`, `一键 AI 修正`, or `标注修复面板`.
- Reconfirmed desktop and mobile horizontal overflow checks passed, and mobile nav labels stayed inside their buttons at `390x844`.
