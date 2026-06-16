---
phase: next-ui
slug: next-version-visual-guidance
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-16
reviewed_at: 2026-06-16
---

# Next Version - UI Design Contract

目标：减少屏幕文字量，用更清楚的视觉层级、轻量动效和统一按钮尺寸，引导用户完成专利生成、质量检查、正式稿编译和导出。

GSD note: 当前仓库没有 `.planning/config.json`，本文件作为 repo-local UI-SPEC fallback。后续若初始化 GSD，可迁移到对应 phase 目录。

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Manual CSS variables in `frontend/src/styles.css` |
| Preset | not applicable |
| Component library | none |
| Icon library | `lucide-react` |
| Font | system UI for text, `var(--font-mono)` only for logs and hashes |

No new UI dependency for this phase. Reuse `ShellSidebar`, `ShellTopbar`, `StatusBadge`, `RiskBanner`, `OperationConsole`, `ScoreTile`, and one unified button contract.

---

## Product Surface

| Screen Area | Contract |
|-------------|----------|
| App shell | Sidebar + topbar remain stable across every page. Do not create page-specific shell variants. |
| Guided workflow | Primary focal point is the current step card. Completed/locked steps are visible but visually quieter. |
| Quality results | Show score, severity, and next action first. Long explanations move behind expandable detail. |
| Formal draft/export | Show lock/pass state before export links. Export actions remain disabled until gates are satisfied. |
| Settings | Use compact grouped controls, not paragraph explanations. |

---

## Visual Guidance

| Element | Rule |
|---------|------|
| Primary focal point | One highlighted current-action panel per screen. No competing primary cards. |
| Stepper | Left or top timeline uses status dots, icons, and progress bar before explanatory text. |
| Action dock | Long-running runs show a sticky compact action/status strip with elapsed time and cancel/retry actions. |
| Empty states | One icon, one heading, one next action. No long instructional copy. |
| Error states | Problem + recovery action + raw detail toggle. Never show raw trace as the first line. |

---

## Motion

| Token | Value | Usage |
|-------|-------|-------|
| instant | 120ms ease | Button hover, nav hover, badge state changes |
| guide | 180ms ease | Progress width, current-step highlight, status dot changes |
| reveal | 240ms ease-out | New result cards and expandable detail reveal |

Rules:
- Use CSS transitions already present in `styles.css`; do not add a JS animation library.
- Respect `prefers-reduced-motion: reduce` by disabling reveal/guide movement and keeping opacity changes only.
- Motion should indicate state progression, not decorate idle surfaces.
- Loading uses `Loader2` spin or the existing `.spin`; one spinner per active area.

---

## Copy Reduction

| Element | Copy Contract |
|---------|---------------|
| Page subtitle | Max 1 short sentence. Remove repeated feature explanations. |
| Workflow hints | Max 1 line in normal state. Use detail toggles for long reasons. |
| Cards | Title + status badge + one metric or action. Move secondary evidence to detail. |
| Buttons | Verb + noun when text is visible. Icon-only buttons require `aria-label` and `title`. |
| Logs | Collapsed by default unless a run is active or failed. |

Copy examples:

| Element | Copy |
|---------|------|
| Primary CTA | `生成正式稿` |
| Secondary CTA | `重新运行检查` |
| Empty state heading | `还没有项目` |
| Empty state body | `选择一种起草入口，系统会创建项目并进入流程。` |
| Error state | `运行失败。请重试，或展开技术详情定位接口/后端问题。` |
| Destructive confirmation | `删除项目：输入项目名称后删除，保留导出文件不自动清理。` |

---

## Spacing Scale

Declared values must stay on the existing 4px grid.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, badge internal gaps |
| sm | 8px | Compact row gaps, inline controls |
| md | 16px | Default card content gap |
| lg | 24px | Panel padding, form groups |
| xl | 32px | Section spacing |
| 2xl | 48px | Major page bands |
| 3xl | 64px | Rare page-level separation |

Exceptions:
- Button heights: 44px default, 36px compact, 32px icon-only.
- Sidebar nav stays minimum 44px for touch and pointer targets.

---

## Button Contract

| Type | Size | Usage |
|------|------|-------|
| Primary | min-height 44px, px 16, gap 8 | One main next action per screen or panel |
| Secondary | min-height 36px or 44px, px 12/16 | Refresh, rerun, open helper tools |
| Danger | min-height 36px or 44px | Cancel run, delete project/source |
| Icon-only | 32px square compact, 40px square prominent | Toolbar actions only |

Rules:
- Unify `.btn`, `.primary`, `.icon-button`, `.project-action-btn`, and `ActionButton` around these dimensions before adding new button styles.
- No inline one-off gradient button classes in new code.
- All icons use 16px inside normal buttons and 18px inside prominent export/action tiles.
- Disabled state uses opacity plus cursor, not color alone.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Label | 12px | 600 | 1.3 |
| Body | 14px | 400 | 1.5 |
| Heading | 18px | 600 | 1.25 |
| Display | 24px | 600 | 1.2 |

Rules:
- Do not add more font sizes for this phase.
- Use tabular numbers for elapsed time, scores, and counts.
- Letter spacing is 0 except existing uppercase micro-labels.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant 60% | `var(--surface-base)` | App background and workspace base |
| Secondary 30% | `var(--surface-raised)`, `var(--surface-subtle)` | Panels, sidebar, cards |
| Accent 10% | `var(--action-primary)` | Primary CTA, active nav, current step, focus ring, selected item |
| Success | `var(--success)` | Completed gates and passed checks |
| Warning | `var(--warn)` | Needs review, partial result, blocking precursor |
| Destructive | `var(--danger)` | Delete, cancel, failed gate |

Accent is reserved for: primary CTA, active nav item, current workflow step, selected patent point, focus ring, progress bar. Do not use accent for every hover state.

---

## Component Rules

| Component | Rule |
|-----------|------|
| `ShellSidebar` | Keep all primary navigation here. Do not duplicate full nav inside pages. |
| `ShellTopbar` | Holds current project, global status, refresh, and theme. Page actions stay compact. |
| `StatusBadge` | Use for state labels. Avoid raw text-only status strings. |
| `RiskBanner` | Use only for blocking or review-needed states. Do not use for normal help text. |
| `OperationConsole` | Active or failed runs only. Collapsed when completed successfully. |
| `ScoreTile` | Scores and maturity metrics only. Do not turn normal cards into score tiles. |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not applicable |

No third-party registry blocks are approved for this phase.

---

## Implementation Checklist

- [ ] Replace new inline button class strings with the unified button contract.
- [ ] Audit existing button heights in guided flow, corpus, patent point, and export panels.
- [ ] Collapse long hints/logs behind detail toggles where a status badge and next action are enough.
- [ ] Add reduced-motion handling for current progress and reveal transitions.
- [ ] Keep DOM smoke selectors `.app-shell`, `.sidebar`, and `.topbar` intact.
- [ ] Verify installed app flow manually after packaging, not just frontend build.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

Approval: approved 2026-06-16
