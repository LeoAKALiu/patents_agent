---
status: draft
owner: product/frontend
created: 2026-06-29
source: Product owner discussion with current production React/Tauri UI
scope: information architecture, page structure, workflow semantics, visual direction
related:
  - docs/ui-redesign/01-UI-SPEC.md
  - docs/ui-redesign/03-opendesign-refero-kanban.md
  - docs/project-design-overview.md
source_identity:
  branch: codex/automation-test-plan
  short_sha: efd94397
  worktree: /Users/leo/Projects/patents_agent
  dirty_at_capture: true
---

# PatentAgent Workbench And Document Repair UI Redesign Spec

This document defines the next PatentAgent UI restructuring direction. It is
based on the production React/Tauri UI, the product owner's heavy-use workflow,
and the current failure mode where the 9-step guided flow, expert tools, status
cards, reports, repair actions, and export gates compete on the same screen.

This spec does not prove implementation. Per project guardrails, production UI
evidence must come from `frontend/src/`, `src-tauri/`, and the real running app.
OpenDesign exports, screenshots, and this document are requirements and
planning inputs only.

## Product Goal

Restructure PatentAgent from:

```text
9-step guided flow + expert tool collection
```

into:

```text
current project command center + document and repair workspace
```

The redesigned UI must let a heavy user answer these questions quickly:

- What project am I working on?
- What is the current status of the draft?
- Why is export locked?
- What is the one next action?
- Which problems block submission?
- Where in the document is each problem?
- After I edit, which generated artifacts are invalidated?

## Non-Goals

- Do not redesign PatentAgent into a marketing site.
- Do not make OpenDesign, screenshots, or static prototypes the source of truth.
- Do not move legal or patent judgment into decorative UI language.
- Do not hide formal gate failures behind optimistic status labels.
- Do not turn the export page into a second repair workspace.
- Do not expose raw JSON, run IDs, full hashes, or logs by default.

## Current Problems

The current UI has several structural issues:

- The left sidebar mixes global navigation, project-specific key steps, and
  system health.
- The 9-step flow appears as both a process model and a navigation model.
- Expert tools duplicate or overlap the guided flow, forcing users to decide
  whether to use the flow or the tool center.
- Post-draft review carries too many responsibilities on one page: gate status,
  issue list, draft summary, agent selection, run controls, report summary, and
  two editor entry points.
- The app does not clearly distinguish:
  - internal draft
  - official draft
  - quality reports
  - post-draft review
  - export files
- Status labels such as "completed" can be misleading when an artifact is
  completed but stale.
- Liquid glass exists in tokens and components, but the product language is not
  consistently defined around where glass is appropriate.

## Design Principles

### One Page, One Primary Job

Each main surface should have one primary purpose:

- `Workbench` decides the next action.
- `Document And Repair` fixes the document.
- `Export` saves final files.
- `Expert Tools` exposes advanced tools.

### One Primary Action

Each page should present one recommended primary action at a time. Secondary
actions may exist, but must not compete visually with the main workflow.

Examples:

- `Enter annotated repair`
- `Save internal draft`
- `Recompile official draft`
- `Run post-draft review`
- `Export official DOCX`

### State Over Completion

Avoid using "completed" as a release signal. A completed artifact can be stale.
Use explicit gate state.

Approved state vocabulary:

- `可编辑`
- `当前有效`
- `已失效`
- `需要修复`
- `待重新验证`
- `导出锁定`
- `可导出`
- `运行中`
- `等待生成`
- `运行失败`

### Process Pages Push, Workspaces Resolve

The 9-step flow should push the user through the process. Complex resolution
belongs in workspaces.

For example:

- The step `成稿会审` can trigger or summarize a review.
- The workspace `文稿与修复` handles the actual issue queue, document editing,
  version invalidation, and repair workflow.

### Formal vs Internal Must Be Visually Separated

Official submission materials and internal review/strategy materials must never
look interchangeable.

The UI must make this distinction visually obvious:

- `正式提交稿`: candidate filing content only.
- `内部复核材料`: strategy, risk, review, and support materials.
- `风险说明与追溯`: reports, hashes, gate evidence, and export trace.

## Information Architecture

### Main Navigation

The left sidebar should contain destinations only:

```text
工作台
项目
文稿与修复
知识库
专家工具
导出
设置
```

The left sidebar should not contain:

- the 9 guided steps
- large current-project status cards
- large model or agent health panels
- expanded expert tool groups

Product owner decision: `知识库` and `导出` remain top-level destinations.
`知识库` owns evidence input and corpus search, and should not be buried under
`专家工具`. `导出` owns final file handoff and trace packaging, and should remain
separate even though export readiness is summarized in `文稿与修复 / 总览`.

### Project Flow Model

The 9 core steps remain part of the product model, but should move into the
workbench as project progress:

```text
构思输入
- 想法与材料
- 发明点

生成成稿
- 多智能体会审
- 核心公式
- 生成初稿
- 质量检查

提交放行
- 正式稿编译
- 成稿会审
- 导出
```

Supported step states:

- `已完成`
- `当前`
- `阻断`
- `等待`
- `已失效`

If a step requires complex handling, the step should link into the appropriate
workspace rather than expand into a dense workbench inside the guided flow.

## Global Shell

### Sidebar

Purpose: navigation only.

Required behavior:

- Fixed desktop sidebar.
- Bottom mobile navigation or mobile sheet for small screens.
- Current project may appear as a compact chip, not as a large card.
- Expert tool groups are not expanded in the sidebar.

Recommended sidebar items:

| Item | Purpose |
| --- | --- |
| 工作台 | Current project command center |
| 项目 | Project list, selection, creation, deletion |
| 文稿与修复 | Draft, official draft, issues, repair, versions |
| 知识库 | Corpus build and search |
| 专家工具 | Low-frequency advanced tools |
| 导出 | Final files and export history |
| 设置 | Model, agents, backend, preferences |

### Topbar

Purpose: global context and current page context.

Left side:

- page title
- short page description

Right side:

- current project selector
- run status chip
- export status chip when applicable
- backend status icon
- refresh action

Examples:

```text
文稿与修复
处理当前项目的正文、问题和版本链路

[城市体检智能体...] [导出锁定] [后端在线] [刷新]
```

### System Health

Keep left-bottom health minimal:

```text
模型 可用
智能体 部分可用
后端 在线
```

Clicking health opens a diagnostic drawer. Detailed diagnostics should not
occupy the default sidebar.

### Error Model

Global errors have three categories:

| Type | Placement | Example |
| --- | --- | --- |
| Blocking | Global banner | Backend offline, save failed |
| Task-specific | Relevant workspace/module | Post-draft review failed |
| Informational | Toast/light notice | Saved, refreshed |

Backend offline copy should be short and actionable:

```text
后端离线，项目和模型状态可能不是最新。
```

Actions:

- `重试`
- `查看诊断`

## Workbench

The workbench is the default app home when a project exists. It is the current
project command center, not a replacement for every workflow surface.

### Primary Questions

The workbench must answer:

- What is the current project?
- Where is the project in the process?
- Is anything running?
- Is export blocked?
- What is the next action?
- Which workspace should I enter?

### Empty State

When no project exists, the workbench shows the three start paths:

- from technical idea to invention patent
- from structural scheme to utility model
- import existing draft for improvement

### Modules

#### Current Project Card

Shows:

- project name
- patent type or entry mode
- current stage
- export status
- last update time

Actions:

- `切换项目`
- `新建项目`
- `刷新状态`

#### Next Action Card

The most important module.

Format:

```text
下一步：处理成稿会审阻断项
当前正式稿导出被锁定，因为成稿会审发现 8 个阻断项。
```

Primary action:

```text
进入文稿与修复
```

Secondary action:

```text
查看版本链路
```

There should be only one visually dominant action.

#### Process Progress

Show the 9 steps in 3 grouped bands:

- `构思输入`
- `生成成稿`
- `提交放行`

The progress component should be compact. Avoid large repeated cards.

#### Run Status

Examples:

```text
当前无运行任务
```

or:

```text
成稿会审运行中 - 权利要求复核 - 01:42
```

Supported actions:

- view details
- cancel
- retry failed task

Run logs are collapsed by default.

#### Risk Summary

Show counts only:

- blocking
- risk
- pending revalidation
- export locked/available

Clicking opens `文稿与修复 / 问题`.

#### Recent Activity

Show recent important events:

- material upload
- draft generation
- quality check
- patch application
- official compile
- post-draft review
- export

Keep this secondary. It supports trust, not navigation.

## Document And Repair Workspace

This is the core heavy-use workspace.

Chinese label:

```text
文稿与修复
```

Purpose:

Manage the internal draft, official draft, quality issues, blocking repairs,
version validity, and gate evidence between draft generation and final export.

Primary workflow:

```text
发现问题 -> 定位正文 -> 修复 -> 保存初稿 -> 重新编译正式稿 -> 重新成稿会审 -> 解锁导出
```

### Tabs

```text
总览
编辑
问题
标注修复
版本
```

### Overview Tab

Purpose: help the user decide what to do next.

It is not a report page. It should not display long text, raw report output,
JSON, or full logs.

#### Top Conclusion

One sentence:

```text
当前文稿阻断导出，需先处理 8 个阻断项。
```

Primary action:

```text
进入标注修复
```

Alternative primary actions by state:

- `重新质量检查`
- `重新编译正式稿`
- `重新成稿会审`
- `导出正式稿`

#### Gate Chain

Show:

```text
内部初稿 -> 质量检查 -> 正式稿编译 -> 成稿会审 -> 导出
```

Each node shows only the conclusion:

- passed
- current blocker
- waiting
- stale

Full hashes and run IDs stay behind details.

#### Draft Status Cards

Two cards:

1. `内部初稿`
   - editable state
   - title
   - section word counts
   - last saved time
   - unsaved edits
   - action: `编辑文稿`

2. `正式稿`
   - exists or missing
   - generated from current internal draft or stale
   - contamination cleanup status
   - export eligibility
   - action: `查看正式稿` or `重新编译`

The UI must make clear that the internal draft is editable and the official
draft is a generated submission candidate.

#### Issue Summary

Show four metrics:

- `阻断`
- `风险`
- `建议`
- `已处理`

Then show the top 5 priority issues.

Row format:

```text
阻断 - 权利要求书 - C_det 使用 IoU 无法在线计算
```

Action:

```text
定位
```

Clicking opens `标注修复` with the issue selected.

#### Next-Step Explanation

Keep this short and explicit:

```text
先处理阻断项。保存初稿后，当前正式稿和旧成稿会审会失效，需要重新编译正式稿并重新成稿会审。
```

#### Recent Records

Show compact records for:

- quality check
- official compile
- post-draft review
- patch application
- export

Details are collapsed.

### Edit Tab

Purpose: quietly edit the current internal draft.

It is not a repair queue and not a report page.

#### Top Status

Show:

- `内部初稿 - 可编辑`
- current draft hash or version short label
- unsaved changes
- invalidation note

Primary button:

- disabled `保存` when unchanged
- `保存初稿` when changed
- after save, suggest `去重新编译正式稿`

#### Layout

Two-column layout:

Left:

- section navigation
- title
- abstract
- claims
- description
- drawing description

Each section shows:

- word count
- issue markers

Example:

```text
权利要求书 - 4105 字 - 2 阻断
说明书 - 11361 字 - 6 风险
```

Center:

- one active section editor at a time
- no all-sections giant textarea by default

Optional right panel on wide screens:

- current section issue summary
- last saved
- related checks
- `进入标注修复`

#### Required Capabilities

First implementation should support:

- section switching
- word count
- save state
- unsaved leave warning
- undo/redo
- search
- basic text preservation
- issue markers

Avoid rich text in the first version. Patent text relies on structure and
accuracy. Rich text raises export and formatting risk.

#### Save Semantics

After saving the internal draft:

- current official draft becomes stale
- old post-draft review becomes stale
- export becomes locked
- next step is official recompile
- then post-draft review

Show this as a persistent status fact, not as a disruptive warning dialog.

### Issues Tab

Purpose: a document risk inbox.

It manages, filters, sorts, assigns, and tracks all issues. It does not edit
the document.

#### Sources

Unify issues from:

- filing readiness
- claim defense
- draft completion
- official compile
- post-draft review
- internal contamination scan
- AI patch result

All sources must map into a shared issue structure.

#### Top Summary

Metrics:

- `阻断`
- `风险`
- `建议`
- `已处理`

Global status:

- `导出锁定`
- `可继续修复`
- `等待重新验证`
- `可导出`

#### Filters

Filter dimensions:

- type: blocking, risk, suggestion
- state: unhandled, in progress, pending revalidation, resolved, unanchored
- section: title, abstract, claims, description, drawing description
- source: readiness, claim defense, completion, compile, post-draft review
- severity: critical, high, medium, low

Default:

```text
未处理 + 阻断优先
```

#### Table

Desktop should use a table for density.

Columns:

- priority
- issue
- section
- source
- status
- updated time
- action

Row actions:

- `定位修复`
- `查看详情`
- `标记暂不处理`

`定位修复` opens `标注修复` with the issue selected.

#### Detail Drawer

Clicking a row opens a right-side drawer.

Contents:

- full issue text
- matched text
- source report
- recommended fix
- impact
- handling history
- action: `进入标注修复`

The drawer preserves inbox context.

#### Issue State Model

Supported states:

- `未处理`
- `处理中`
- `已生成补丁`
- `已应用修正`
- `人工已修改`
- `待重新验证`
- `已解决`
- `暂不处理`
- `无法定位`

Important rule:

```text
已应用修正 != 已解决
```

An issue is resolved only after revalidation confirms it no longer appears.

### Annotated Repair Tab

Purpose: process issues one by one or in sequence.

Mental model:

```text
left decides what to fix
center proves where it is
right decides how to fix
```

#### Top Status

Show:

- current internal draft
- review source
- issue count
- invalidation rule

Example:

```text
当前初稿 - 可编辑
会审来源 - 85e589...
问题 46 项
保存后：正式稿与旧会审失效
```

Primary action:

- `保存初稿`
- after save: `去重新编译正式稿`

#### Desktop Layout

Three fixed columns:

1. Issue queue
2. Document body
3. Repair inspector

#### Issue Queue

Do not use large cards for every issue. Use compact rows.

Row format:

```text
阻断 - 严重 - 权利要求书
C_det 使用 IoU 无法在线计算
```

Queue filters:

- all
- blocking
- risk
- suggestion
- unanchored
- handled

Sort:

- priority
- document order

Default sorting:

```text
blocking > high risk > hit > suggestion
```

Issue states:

- unhandled
- patch generated
- applied
- manual editing
- pending revalidation
- unanchored

#### Document Body

This is not a generic full-document textarea.

Structure:

- section tabs
- current section body
- current issue highlight
- side markers for other issues in the same section
- independent scrolling for long sections

Unanchored issues must not force-scroll the document.

#### Repair Inspector

Sections:

1. Issue explanation
   - source
   - severity
   - target section
   - why it blocks or matters

2. Location evidence
   - matched text
   - surrounding context
   - exact match vs inferred section

3. Recommended fix
   - plain-language recommendation
   - no raw JSON by default

4. Repair actions
   - `生成 AI 修正`
   - `应用修正`
   - `手动修改`
   - `标记暂不处理`

AI repair must preview the diff before applying. No silent write-back.

After applying a patch:

- update the center document
- mark issue `待重新验证`
- show next step: recompile official draft and rerun post-draft review

#### Not Allowed In Annotated Repair

Do not show by default:

- agent selection
- post-draft review start controls
- full review report
- export buttons
- long runtime logs

These can exist as links or collapsed details, but not as primary content.

#### Mobile

Use a staged flow:

```text
问题列表 -> 正文定位 -> 修复面板
```

Bottom actions:

- `保存`
- `下一个问题`

### Versions Tab

Purpose: explain whether artifacts belong to the same version chain.

This is not just an audit log.

#### Top Conclusion

Example:

```text
当前内部初稿已修改，正式稿和成稿会审已失效，需重新编译正式稿。
```

Primary action depends on state:

- `重新编译正式稿`
- `重新成稿会审`
- `查看导出`
- `返回编辑`

#### Version Chain

Show:

```text
内部初稿 v12
-> 质量检查 run 08
-> 正式稿 compile 04
-> 成稿会审 review 02
-> 导出文件 export 01
```

Each node shows:

- state: current, stale, historical, usable
- time
- short hash
- action: view, rerun, open report

The main information is whether it matches, not the full hash.

#### Version Groups

1. Internal draft versions
   - current version
   - last saved
   - modification source: manual, AI repair, safe patch
   - word count change
   - history

2. Official draft versions
   - exists or missing
   - generated from current internal draft or stale
   - cleanup status
   - compile warnings
   - view official draft

3. Review versions
   - quality checks current or stale
   - post-draft review current or stale
   - export allowed or locked
   - report links

4. Export versions
   - latest exported file
   - format
   - path
   - matches current official draft or not

#### Version Detail

Clicking any node opens details:

- upstream binding
- downstream artifacts
- why valid or invalid
- next action

Example:

```text
此会审审查的是正式稿 0ddbcf5a01ba，但当前正式稿已变更，因此不能放行导出。
```

## Export Workspace

Purpose:

Save final files after the gates are understood. Do not make export a repair
surface.

### Top Conclusion

Examples:

```text
正式稿可导出
```

or:

```text
正式稿导出锁定：成稿会审未通过
```

Primary action:

- if allowed: `导出正式稿 DOCX`
- if locked: `查看阻断原因`
- if missing official draft: `生成正式稿`

### File Sections

#### Official Submission Draft

Chinese label:

```text
正式提交稿
```

Files:

- DOCX
- Markdown

State:

- available
- locked

Copy:

```text
只包含可提交正文，不包含内部策略、会审、风险注释。
```

#### Internal Review Materials

Chinese label:

```text
内部复核材料
```

Files:

- internal draft
- review report
- quality report
- claim defense report
- draft completion report

These must be visually separated from official files.

#### Risk And Trace

Chinese label:

```text
风险说明与追溯
```

Files:

- official compile report
- export risk sidecar
- hash/version binding evidence
- recent export record

### Gate Summary

Show compact chain:

```text
质量检查
正式稿编译
成稿会审
版本绑定
```

Each node:

- passed
- locked
- stale
- waiting

Click routes:

- quality failure -> `文稿与修复 / 问题`
- stale official draft -> `文稿与修复 / 版本`
- post-draft block -> `文稿与修复 / 标注修复`

### Export Confirmation

When export is allowed, use a lightweight confirmation:

- current official draft short hash
- post-draft review pass time
- reminder that professional review is still required

Avoid long legal disclaimer text in the primary flow.

### Recent Export

Show:

- format
- file path
- file size
- export time
- matches current official draft or not

Actions:

- `打开文件夹`
- `重新导出`

## Expert Tools

Purpose:

Expose low-frequency or advanced tools without forcing normal users to choose
between the guided flow and the tool center.

Recommended groups:

- `知识输入`
- `发明策略`
- `撰写辅助`
- `质量分析`
- `导出辅助`

Existing tools can remain, but should be framed as advanced routes rather than
the primary way to complete the product workflow.

## Visual Direction

Use light liquid glass selectively.

### Apply Glass To

- sidebar
- topbar
- status chips
- drawers
- overlays
- modals

### Do Not Apply Heavy Glass To

- long document editor
- issue table
- risk explanations
- official draft content
- dense data tables
- long reports

### Base Visual Rules

- Professional, dense, scannable.
- No marketing hero.
- No decorative orbs, bokeh, or abstract background elements.
- No nested cards for page sections.
- 8px radius for cards and controls unless an existing component requires
  otherwise.
- Icons should come from lucide or the existing icon layer.
- Risk colors must remain clear and solid.
- Long text surfaces must maximize readability over visual effect.

## Component Implications

Likely component families:

- `ShellSidebar`
- `ShellTopbar`
- `StatusChip`
- `ProjectSelector`
- `GateChain`
- `NextActionCard`
- `WorkspaceTabs`
- `IssueTable`
- `IssueDetailDrawer`
- `DocumentSectionNav`
- `DocumentSectionEditor`
- `AnnotatedRepairLayout`
- `RepairInspector`
- `VersionChain`
- `ExportFileGroup`
- `SystemHealthDrawer`

Reuse existing primitives where practical:

- `StatusStrip`
- `StatusTile`
- `InfoCard`
- `BoundaryCard`
- `ActionDock`
- shadcn/Radix components already present in `frontend/src/components/ui`

## Routing Implications

Current route concepts should be realigned:

| Current concept | New concept |
| --- | --- |
| `generate` / start flow | `工作台` empty-state start paths |
| guided stepper | project progress inside `工作台` |
| expert post-draft tools | advanced routes or backing actions |
| post-draft review panel | summary plus links into `文稿与修复` |
| export expert tool | `导出` workspace |

The implementation should avoid deleting workflow capability. The change is
mostly product framing, navigation, and page responsibility boundaries.

## Implementation Phases

### Phase 1: Shell IA

Scope:

- left navigation
- topbar
- compact system health
- route naming and page titles

Primary files likely affected:

- `frontend/src/app/AppRoot.tsx`
- `frontend/src/app/routes.tsx`
- `frontend/src/guidedFlow.ts`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- `frontend/src/ui/SystemStatusPanel.tsx`
- `frontend/src/styles.css`

Acceptance:

- sidebar contains the 7 destination items
- guided steps are not sidebar items
- topbar consolidates project, run, export, backend, refresh state
- system health is compact and can expand into diagnostics

### Phase 2: Workbench

Scope:

- default current project dashboard
- empty-state start paths
- next-action card
- compressed 9-step flow
- risk and run summaries

Acceptance:

- user can identify the next action within 5 seconds
- workbench recommends one primary action
- no full reports or long logs are shown by default

### Phase 3: Document And Repair Overview

Scope:

- `文稿与修复` route and tabs
- overview tab
- gate chain
- internal/official draft status cards
- top issues

Acceptance:

- user can understand why export is locked
- internal draft and official draft are clearly separated
- hash and run details are folded under details

### Phase 4: Edit, Issues, Versions

Scope:

- edit tab
- issue inbox tab
- version chain tab

Acceptance:

- editing one document section at a time works
- issue inbox supports filter/sort/detail
- stale artifacts are explained explicitly

### Phase 5: Annotated Repair

Scope:

- three-column repair layout
- compact issue queue
- document section focus
- repair inspector
- AI patch preview and apply flow

Acceptance:

- selecting an issue moves to the right document section
- AI patch application is previewed before write-back
- issue state becomes pending revalidation, not resolved
- long issue lists scroll independently

### Phase 6: Export Simplification

Scope:

- official submission files
- internal review files
- risk and trace files
- recent export

Acceptance:

- official and internal materials cannot be visually confused
- locked export routes back to the right repair/version page
- export page does not contain repair UI

### Phase 7: Expert Tool Reframing

Scope:

- expert tool grouping and copy
- low-frequency positioning
- route links from workbench/document pages

Acceptance:

- expert tools do not compete with normal workflow
- advanced users can still reach all existing capabilities

### Phase 8: Visual QA And Packaging Evidence

Scope:

- responsive layout
- overflow checks
- contrast checks
- Tauri running-app evidence

Acceptance:

- no horizontal overflow on desktop or mobile
- text does not overlap controls
- long document/editor surfaces remain readable
- packaged app evidence comes from the exact artifact being handed off

## Validation Checklist

- [ ] The sidebar has only global destinations.
- [ ] The 9-step process appears inside the workbench, not global navigation.
- [ ] The workbench exposes one recommended next action.
- [ ] `文稿与修复` contains overview, edit, issues, annotated repair, and versions.
- [ ] Internal draft and official draft are visually and semantically distinct.
- [ ] Saving the internal draft invalidates stale official/review/export state.
- [ ] Issue state distinguishes applied from resolved.
- [ ] Annotated repair has independent scrolling for issue queue and document.
- [ ] Export separates official, internal, and trace materials.
- [ ] Raw JSON, full hashes, run IDs, and logs are collapsed by default.
- [ ] Liquid glass is limited to chrome, chips, drawers, and overlays.
- [ ] Dense document and risk surfaces use solid readable backgrounds.
- [ ] Mobile uses staged repair flow instead of forced three columns.
- [ ] Real running app evidence is captured before claiming completion.

## Resolved Decisions

1. `知识库` remains a top-level destination. It owns corpus build, evidence
   intake, retrieval, and prior-art/reference lookup.
2. `导出` remains a top-level destination. Export readiness can appear in
   `文稿与修复 / 总览`, but final file selection, risk confirmation, and handoff
   packaging belong in a distinct export workspace.

## Open Decisions

1. Whether issue history should be persisted as first-class data or derived from
   existing reports and patch events.
2. Whether the edit tab should support paragraph-level editing in the first
   implementation or start with section-level text editing.
3. Whether the version chain should expose full hash details in a drawer or an
   expandable inline region.

## Source Files To Inspect Before Implementation

At minimum:

- `frontend/src/App.tsx`
- `frontend/src/app/AppRoot.tsx`
- `frontend/src/app/routes.tsx`
- `frontend/src/guidedFlow.ts`
- `frontend/src/GuidedPatentFlow.tsx`
- `frontend/src/features/projects/ProjectWorkspace.tsx`
- `frontend/src/features/postDraft/PostDraftWorkspace.tsx`
- `frontend/src/features/quality/QualityWorkspace.tsx`
- `frontend/src/flow/panels/PostDraftReviewPanel.tsx`
- `frontend/src/flow/panels/PostDraftRepairEditor.tsx`
- `frontend/src/flow/panels/DraftRepairInspector.tsx`
- `frontend/src/flow/panels/PostDraftIssueRail.tsx`
- `frontend/src/views/exportView.tsx`
- `frontend/src/ui/ShellSidebar.tsx`
- `frontend/src/ui/ShellTopbar.tsx`
- `frontend/src/ui/SystemStatusPanel.tsx`
- `frontend/src/styles.css`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/glass.css`

## Handoff Notes

- This spec is a product and UI design contract, not implementation evidence.
- Do not dispatch implementation work from this spec until acceptance checks are
  converted into concrete tasks and source files are inspected.
- For UI work, verify production React and the running Tauri app, not only
  screenshots or static prototypes.
- If packaged as a DMG, follow the release guard documents under
  `docs/release/`.
