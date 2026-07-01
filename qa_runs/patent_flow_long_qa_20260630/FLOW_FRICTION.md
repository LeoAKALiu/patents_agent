# Flow Friction

### FRICTION-001: Source and product identity are ambiguous before any user-flow test starts

- 用户画像：QA/release owner; indirectly all users if this reaches packaging.
- 所在流程阶段：Environment setup / test target selection.
- 触发步骤：Run source identity checklist and read current README/package metadata.
- 观察到的卡点：Current worktree has unmerged files, while README current-version text says `v1.0.0` and package metadata says `1.1.0`.
- 为什么影响流畅性：A tester or release owner cannot confidently decide whether a failed UI/API behavior belongs to current source, stale installed app, a partially merged branch, or outdated docs.
- 建议改进：Resolve source conflicts before user-facing QA; add a small repo command or script that prints app name, package versions, branch/SHA, data dir, and installed-app identity in one place.
- 当前缓解：`scripts/qa_preflight.py` now prints source identity, dirty entries, unmerged files, and Python/frontend/Tauri version metadata; it exits non-zero when unmerged files are present.
- 严重程度：High
- 是否建议自动化检测：Yes. Add a release/QA preflight that fails on unmerged index entries and version drift.

### FRICTION-002: Material upload boundary behavior is discoverable only by reading code or trial-and-error

- 用户画像：用户 C：企业研发负责人；用户 D：粗心/误操作用户；用户 E：边界/恶意输入用户。
- 所在流程阶段：输入技术交底材料。
- 触发步骤：Scan upload code and user-facing flow; no central declared constraints found for max size, MIME mismatch, repeated names, or partial multi-file status.
- 观察到的卡点：Supported extensions are implemented, but boundary constraints are not documented in README/guided-flow docs and not obvious from UI docs.
- 为什么影响流畅性：Users uploading many large or mixed-format materials may not know what is supported, why an upload failed, or whether a partial success is safe.
- 建议改进：Expose accepted formats, size limits, duplicate handling, and per-file parse status near the upload control; add a batch upload status model if not already present in production UI.
- 严重程度：Medium
- 是否建议自动化检测：Yes. Cover empty, unsupported, corrupt, duplicate, and large-file upload in integration/component tests.

### FRICTION-003: Empty and extremely short marketing-only ideas can create projects without immediate guidance

- 用户画像：用户 A：第一次使用的发明人；用户 D：粗心/误操作用户。
- 所在流程阶段：新建项目 / 输入技术交底材料。
- 触发步骤：Run `python3 qa_runs/patent_flow_long_qa_20260630/explore_incomplete_flow.py`.
- 观察到的卡点：`POST /api/projects` accepts `draft_text=""` and accepts `draft_text="智能仓储助手，提高效率。"`. The incomplete disclosure material uploads as `processed` with no warning. Before draft generation, export readiness says `next_action=generate_draft`; generation then fails at LLM configuration in this no-key environment.
- 为什么影响流畅性：A first-time user can create a project that has no usable technical problem/solution/effects, then may only discover missing prerequisites later. API-level behavior does not distinguish "needs more technical disclosure" from "ready to generate when LLM is configured".
- 建议改进：Add UI/API guidance for empty, extremely short, or marketing-only ideas: allow saving a draft project if desired, but show missing fields and avoid presenting generation as the only next action.
- 当前缓解：`IdeaIntakePanel` now shows frontend guidance for very short ideas and marketing-only descriptions before project creation. API-level readiness still remains permissive.
- 严重程度：Medium
- 是否建议自动化检测：Yes. Add component/integration checks for empty, very short, and marketing-only disclosure guidance.

### FRICTION-004: Duplicate material filename uploads are accepted without visible disambiguation in API results

- 用户画像：用户 C：企业研发负责人；用户 D：粗心/误操作用户。
- 所在流程阶段：输入技术交底材料。
- 触发步骤：Upload `simple_invention.md` twice through `explore_material_uploads.py`.
- 观察到的卡点：Both uploads return 200 and material list contains two rows with identical `file_name` and no warning.
- 为什么影响流畅性：If a user accidentally uploads the same disclosure multiple times, they may not know whether it was deduplicated, duplicated intentionally, or which version downstream extraction used.
- 建议改进：Show duplicate filename/content hash warnings or display upload timestamp/content hash/version suffix in the material list.
- 当前缓解：`MaterialSummary` now warns when duplicate visible file names are present. Content-hash deduplication or version suffixes are still not implemented.
- 严重程度：Low
- 是否建议自动化检测：Yes. Add integration/component test for duplicate filename and duplicate content handling.

### FRICTION-005: Workbench and export workspace can disagree on the next recovery action

- 用户画像：用户 D：粗心/误操作用户；用户 B：专利代理师
- 所在流程阶段：全文审查和 repair / 导出和交付
- 触发步骤：
  1. Seed a project with current internal draft, completed official compile, completed blocking post-draft review, but missing current quality checks.
  2. Open the workbench.
  3. Open the export workspace.
- 观察到的卡点：
  - Workbench next action says `处理成稿会审阻断项` and offers `进入文稿与修复`.
  - Export workspace says official export is locked because quality checks are missing and shows `质量检查未完成`.
  - `export-readiness.json` reports `next_action=run_quality_checks`, while the document/repair state has a repairable post-draft review.
- 为什么影响流畅性：A user can receive two plausible but different recovery priorities depending on workspace. This is especially confusing after a blocking post-draft review exists because the repair editor is available, but export readiness still points first to quality checks.
- 建议改进：
  - Define a single next-action precedence model shared by workbench, document repair, and export.
  - If multiple blockers exist, display an ordered checklist instead of a single competing next action.
  - Consider showing both `quality checks missing` and `post-draft review has repairable blockers`, with a clear recommended order.
- 严重程度：Medium
- 是否建议自动化检测：Yes. Add selector tests for combined missing-quality + repairable-review state and an e2e smoke assertion that workbench/export next actions are consistent.
