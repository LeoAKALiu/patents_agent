/**
 * Official-draft contamination scanner — extracted from App.tsx (M3-B').
 * Detects residual internal markers (log lines, prompt fragments, review
 * memos, mermaid fences, etc.) in an official package so the export UI can
 * warn before hand-off.
 */
import type { OfficialDraftPackage } from "@/api";

export type ContaminationMatch = { section: string; pattern: string };

const OFFICIAL_CONTAMINATION_PATTERNS: ReadonlyArray<{ pattern: string; label: string }> = [
  { pattern: "support_gap", label: "support_gap" },
  { pattern: "support_gaps", label: "support_gaps" },
  { pattern: "generation_logs", label: "generation_logs" },
  { pattern: "image_prompt", label: "image_prompt" },
  { pattern: "attorney_memo", label: "attorney_memo" },
  { pattern: "system_trace", label: "system_trace" },
  { pattern: "official_safe_patches", label: "official_safe_patches" },
  { pattern: "根据会审策略", label: "根据会审策略" },
  { pattern: "多 Agent 会审", label: "多 Agent 会审" },
  { pattern: "多Agent会审", label: "多Agent会审" },
  { pattern: "主席汇总", label: "主席汇总" },
  { pattern: "可能不具备创造性", label: "可能不具备创造性" },
  { pattern: "禁止直接提交", label: "禁止直接提交" },
  { pattern: "存在充分公开风险", label: "存在充分公开风险" },
];

const OFFICIAL_INTERNAL_FIELD_RE = /(?:^|\n)\s*(image_prompt|prompt|diagram|generation_logs|attorney_memo|system_trace|official_safe_patches)\s*[:：=]/i;
const OFFICIAL_MERMAID_RE = /^(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt)\b/i;
const OFFICIAL_FENCE_RE = /```/;
const CHINESE_LABEL_RE = /^\s*["']?(撰写说明(?:与支撑不足提示)?|支撑不足提示)["']?\s*[:：]/;

export function findOfficialContaminationMarkers(
  packageValue: OfficialDraftPackage,
): ContaminationMatch[] {
  const sections: Array<[string, string]> = [
    ["title", packageValue.title],
    ["abstract", packageValue.abstract],
    ["claims", packageValue.claims],
    ["description", packageValue.description],
    ["drawing_description", packageValue.drawing_description],
    ["compile_warnings", packageValue.compile_warnings.join("\n")],
  ];
  const matches: ContaminationMatch[] = [];
  for (const [section, text] of sections) {
    if (!text) continue;
    for (const { pattern } of OFFICIAL_CONTAMINATION_PATTERNS) {
      if (text.includes(pattern)) {
        matches.push({ section, pattern });
      }
    }
    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (OFFICIAL_INTERNAL_FIELD_RE.test(line)) {
        matches.push({ section, pattern: "internal_field" });
      }
      if (OFFICIAL_FENCE_RE.test(trimmed)) {
        matches.push({ section, pattern: "markdown_fence" });
      }
      if (OFFICIAL_MERMAID_RE.test(trimmed)) {
        matches.push({ section, pattern: "mermaid" });
      }
      if (CHINESE_LABEL_RE.test(line)) {
        matches.push({ section, pattern: "撰写说明与支撑不足提示" });
      }
    }
  }
  return matches;
}

export function formatBytes(byteCount: number): string {
  if (byteCount < 1024) return `${byteCount} B`;
  if (byteCount < 1024 * 1024) return `${(byteCount / 1024).toFixed(1)} KB`;
  return `${(byteCount / (1024 * 1024)).toFixed(2)} MB`;
}
