Task 7 Report: Knowledge Page Source Coverage and Gate Copy

Source identity
- Worktree: /Users/leo/Projects/patents_agent/.worktrees/commercial-evidence-provider-skeleton
- Branch: codex/commercial-evidence-provider-skeleton
- Base HEAD before Task 7: 69bec4b0
- Dirty worktree at start: no

Scope followed
- Modified only:
  - frontend/src/views/projectKnowledgeView.tsx
  - frontend/src/projectKnowledgeView.test.tsx
- Did not modify settings UI or backend code.

TDD record
1. Added failing tests to frontend/src/projectKnowledgeView.test.tsx for:
   - separate source setup coverage cards and warning copy for PatSnap/Wanfang
   - evidence tier and patent-gate labels for a Wanfang candidate
2. Ran:
   - npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx
3. Observed expected red state:
   - missing source coverage status pills
   - missing source setup summary
   - missing evidence/gate labels
4. Implemented the minimal UI changes in frontend/src/views/projectKnowledgeView.tsx.
5. Re-ran the focused suite to green.

Implementation summary
- Added quality flag copy for:
  - source_not_configured
  - source_configured_not_implemented
  - non_patent_only
- Expanded the knowledge status pill grid from 5 to 7 cards:
  - 知识状态
  - 候选文献
  - 入库文献
  - 专利证据覆盖
  - 非专利文献覆盖
  - 权利要求覆盖
  - 全文覆盖
- Rendered source setup summary cards from knowledge.source_statuses with:
  - display name
  - configured/not configured state
  - patent-gate role copy
  - guidance text
  - “未配置不是检索失败。” reminder for unconfigured sources
- Added candidate badges for:
  - evidence tier
  - patent gate eligibility

Test notes
- The brief’s regex assertions for /万方/ and /未配置不是检索失败/ matched multiple rendered nodes once the exact required copy was added.
- Narrow adaptation applied in tests:
  - changed those two assertions to presence checks via getAllByText(...).length > 0
- This preserves the brief’s required values while avoiding false failures caused by intentional duplicated copy.

Verification
- Passed:
  - npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx

Files changed
- /Users/leo/Projects/patents_agent/.worktrees/commercial-evidence-provider-skeleton/frontend/src/views/projectKnowledgeView.tsx
- /Users/leo/Projects/patents_agent/.worktrees/commercial-evidence-provider-skeleton/frontend/src/projectKnowledgeView.test.tsx

Fix follow-up: Task 7 review findings
- Added explicit Wanfang/non-patent copy on the knowledge source summary clarifying that it improves background and creativity support, but does not replace patent prior-art evidence or patent gate evidence.
- Expanded source status labels so the summary distinguishes `configured`, `not_configured`, `unavailable`, and `quota_limited`.
- Tightened `frontend/src/projectKnowledgeView.test.tsx` to assert the Wanfang disclaimer and the four source-state labels in the source summary test.
- Test command:
  - `npm --prefix frontend test -- --run src/projectKnowledgeView.test.tsx`
- Result:
  - PASS (`1 passed`, `14 passed`)
