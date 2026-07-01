# PatentAgent UI Flow Audit - 2026-06-30

## Source Identity

- Worktree: `/Users/leo/Projects/patents_agent`
- Branch: `codex/grantatlas-readme-branding`
- HEAD: `f566fc09`
- Worktree state: dirty before audit. Existing modified and untracked files were not reverted.
- Design token source: no `DESIGN.md` was found in this repository, so this audit used current React/Tauri source, `docs/ui-redesign`, live dev UI, and backend data.
- Cleanup note: during browser exploration, a transient QA project `a851fc0bac944f8cb886384270ea33db` was created by the live app state and then deleted through the project API. Verified after cleanup: `projects=0`, `disclosure_runs=0` for that id. Dev servers were stopped after capture.

## Evidence

Accepted screenshots:

1. `screenshots/02-stable-workbench-no-selection.png` - stable workbench with no project selected.
2. `screenshots/03-workbench-selected-draft-project.png` - workbench with an existing draft project selected.
3. `screenshots/04-document-repair-overview.png` - document repair overview for the selected project.
4. `screenshots/05-export-locked.png` - export workspace in locked state.

Rejected or limited screenshots:

- `screenshots/01-initial-workbench.png` captured a useful loading-state issue, but not a stable screen.
- `screenshots/06-mobile-export-locked.png` captured a narrow viewport during refresh and was not accepted as stable evidence. Narrow-window verification remains a gap.

Sample project used:

- `2f871154949a4b20af410ebab6ffcaf2`
- Name: `V110-E2E-01 城市体检多模态无人机主动采集`
- State: has an internal draft package, export is locked.

## User Goal

The user wants the fastest reliable path from patent idea or existing draft to a professionally reviewable patent draft and export package, with agents doing the heavy work automatically while stopping at the right human checkpoints.

This means the UI should optimize for:

1. One obvious next action.
2. Clear automation scope before an agent run starts.
3. Human confirmation only where it protects quality or legal reliability.
4. Immediate recovery path when a gate fails.
5. Tools available in context, but not competing with the main flow.

## Current Flow Health

1. Start / no project selected: workable, but redundant.
   - The workbench shows a primary `创建项目` button and three start cards.
   - The primary button silently defaults to the invention path while the three cards imply the user must choose.
   - Recommendation: remove the generic primary button in this state, or relabel it as `从发明专利开始`.

2. Selected draft project: good state inference, noisy routing.
   - The workbench correctly identifies `运行质量检查` as the next step.
   - It also shows secondary links to `文稿与修复`, `知识库`, and `专家工具` at the same visual level as the main continuation.
   - Recommendation: keep one dominant `让 Agent 继续` action and move secondary links under `其他操作`.

3. Document repair overview: highest-risk inconsistency.
   - The backend export readiness says `next_action=run_quality_checks`, `quality_done=false`, and unknown checks include `claim_defense_worksheet` and `draft_completion`.
   - The document overview still shows `质量检查 当前有效`, while the same screen later says quality is incomplete.
   - The primary action is `编辑文稿`, even though the safer next action is to finish quality checks or recover the failed review path.
   - Recommendation: derive document gates and primary action from export-readiness first, then latest artifacts second.

4. Export locked state: clear gate message, too much competing content.
   - The locked export page clearly says quality is incomplete and links back to document repair.
   - It also exposes long draft content below the locked gate, which dilutes the action needed to unlock export.
   - Recommendation: in locked state, show only unlock checklist, responsible gate, and links to the exact repair/check action. Hide draft previews behind a collapsed disclosure.

## Proposed Information Architecture

Use this product shape:

1. `工作台`
   - The single default home for the patent drafting journey.
   - Shows current objective, next recommended action, agent run plan, human checkpoint, progress, and risks.

2. `项目`
   - Project switching, archive, deletion, and history.
   - Not part of the drafting flow once a current project is selected.

3. `知识库`
   - Evidence and prior-art corpus.
   - Opened from the workbench only when the current step needs evidence.

4. `文稿`
   - Draft, formal draft, issue queue, annotated repair, versions.
   - Task-first: when locked, the first screen is the unlock task, not a document editor.

5. `导出`
   - File output and traceability only.
   - If locked, it becomes an unlock checklist, not a content review page.

6. `设置`
   - Model, providers, runtime, preferences.

Move `专家工具` out of the top-level default nav. Keep it as `高级工具` inside contextual menus, or show it only in an advanced drawer. The current top-level `专家工具` competes with the flow and makes users decide implementation details.

## Proposed Primary Flow

Collapse the visible user journey into five phases, while keeping the backend's finer nine-step state machine internally:

1. `输入`
   - Choose `从技术想法`, `实用新型`, or `已有稿件`.
   - Required fields stay minimal: project name and one technical description, or uploaded/pasted draft.
   - Optional metadata remains collapsed.

2. `提炼`
   - Agent extracts invention points, evidence gaps, and optional prior-art research needs.
   - Human checkpoint: select or confirm the main invention line.

3. `成稿`
   - Agent runs deliberation, formula extraction when needed, and draft generation.
   - Human checkpoint only if the agent needs missing materials or a strategy choice.

4. `质检修复`
   - Agent runs filing readiness, grantability, claim defense, completion, formal compile, and post-draft review as a guided chain.
   - Human checkpoint: review blocking issues and approve safe patches.

5. `导出`
   - Export only when the current source hash, formal draft hash, quality gates, and post-draft review match.
   - Human checkpoint: final professional review reminder and export confirmation.

## Workbench Redesign

The workbench should answer four questions above the fold:

1. `我现在在哪个项目？`
2. `离可导出正式稿还差什么？`
3. `点击继续后 Agent 会做什么？`
4. `哪里需要我确认？`

Recommended layout:

- Header band: project, patent type, target, export readiness.
- Primary action card: `下一步：运行质量检查` or `让 Agent 继续到下一门禁`.
- Agent plan drawer: list the exact runs that will start, for example `提交成熟度 -> 授权前景 -> 权利要求防线 -> 成稿完整度`.
- Human checkpoint card: `当前无需人工输入` or `需要确认主发明点`.
- Risk card: blockers first, suggestions second.
- Progress rail: five user phases, not nine backend steps by default.

## Reliability Rules

1. Any page with an export gate must use export-readiness as the source of truth.
2. Primary CTA must always match `next_action`.
3. If `next_action=run_quality_checks`, do not show `编辑文稿` as the dominant action.
4. If a run failed because of agent output format, show `重试成稿会审` and the repair suggestion, not a generic issue queue.
5. If a page exposes advanced tools, label them as optional and keep them visually secondary.
6. Every agent run start should preview what will run and when it will stop for human confirmation.
7. Every completed run should summarize `生成了什么`, `改动了什么`, `还有什么风险`, and `下一步是什么`.

## Implementation Priorities

P0:

- Fix document repair gate derivation so `quality_done=false` and unknown quality checks cannot appear as `质量检查 当前有效`.
- Fix document repair primary action to follow export-readiness `next_action`.
- In export locked state, show unlock checklist before any draft content and collapse long previews.

P1:

- Simplify top-level nav by demoting `专家工具`.
- Replace workbench secondary links with an `其他操作` menu.
- Replace no-project generic `创建项目` CTA with the three explicit path cards, or make the CTA's path explicit.

P2:

- Add an agent run plan preview before multi-step automation.
- Add a compact five-phase user progress view over the existing nine-step internal model.
- Add narrow-window regression checks for workbench, document repair, and export locked states.
