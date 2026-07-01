import type { FormEvent } from "react";

import { CorpusView } from "@/views/projectViews";
import { ProjectKnowledgeView } from "@/views/projectKnowledgeView";
import type { CorpusJobForm } from "@/views/corpusBuildView";

import type {
  CnipaQueryPack,
  CorpusImportJob,
  CorpusStats,
  CorpusVersion,
  PatentDocument,
  PriorArtCandidate,
  ProjectKnowledgeImportLedger,
  ProjectKnowledgeOverview,
  ProjectRecord,
  SearchResult,
  SectionType,
} from "@/api";

/**
 * State slice consumed by the "corpus" workspace: corpus build (import jobs)
 * and the corpus search/import tools. The workspace is presentational —
 * handlers are passed in from App.tsx.
 */
export interface CorpusWorkspaceState {
  selectedProject?: ProjectRecord | null;
  projectKnowledge?: ProjectKnowledgeOverview | null;
  cnipaQueryPack?: CnipaQueryPack | null;
  importLedgers?: ProjectKnowledgeImportLedger[];
  /** Import-job form state (build tool). */
  corpusJobForm: CorpusJobForm;
  /** Active import job, if any. */
  corpusJob: CorpusImportJob | null;
  corpusVersions: CorpusVersion[];
  corpusStats: CorpusStats | null;
  documents: PatentDocument[];
  searchText: string;
  searchSection: SectionType | "";
  searchResults: SearchResult[];
  busy: string;
}

export interface CorpusWorkspaceHandlers {
  onCorpusFormChange: (patch: Partial<CorpusJobForm>) => void;
  onCreateCorpusJob: (event: FormEvent) => Promise<void> | void;
  onUploadCorpusJobFile: (event: FormEvent<HTMLFormElement>) => Promise<void> | void;
  onRunCorpusJob: () => Promise<void> | void;
  onGenerateKnowledgePlan: () => Promise<void> | void;
  onRunKnowledgeSearch: () => Promise<void> | void;
  onCandidateDecision: (
    candidateId: string,
    decision: PriorArtCandidate["user_decision"],
  ) => Promise<void> | void;
  onBuildProjectCorpus: () => Promise<void> | void;
  onImportCnipaExport: (file: File) => Promise<void> | void;
  onImport: (event: FormEvent<HTMLFormElement>) => Promise<void> | void;
  onSearch: (event: FormEvent) => Promise<void> | void;
  onSearchText: (text: string) => void;
  onSearchSection: (section: SectionType | "") => void;
}

/**
 * The corpus workspace only renders the build and search sub-tools; the
 * navigation between them is owned by App.tsx which selects the active
 * expert tool. This component routes between the two based on the
 * `tool` prop.
 */
export type CorpusTool = "build" | "corpus";

export interface CorpusWorkspaceProps {
  tool: CorpusTool;
  state: CorpusWorkspaceState;
  handlers: CorpusWorkspaceHandlers;
}

export function CorpusWorkspace({ tool, state, handlers }: CorpusWorkspaceProps) {
  if (tool === "build") {
    return (
      <ProjectKnowledgeView
        selectedProject={state.selectedProject ?? null}
        knowledge={state.projectKnowledge ?? null}
        busy={state.busy}
        cnipaQueryPack={state.cnipaQueryPack ?? null}
        importLedgers={state.importLedgers ?? []}
        onGenerateKnowledgePlan={() => void handlers.onGenerateKnowledgePlan()}
        onRunKnowledgeSearch={() => void handlers.onRunKnowledgeSearch()}
        onCandidateDecision={(candidateId, decision) =>
          void handlers.onCandidateDecision(candidateId, decision)
        }
        onBuildProjectCorpus={() => void handlers.onBuildProjectCorpus()}
        onImportCnipaExport={(file) => void handlers.onImportCnipaExport(file)}
      />
    );
  }
  return (
    <CorpusView
      documents={state.documents}
      searchText={state.searchText}
      searchSection={state.searchSection}
      searchResults={state.searchResults}
      busy={state.busy}
      onImport={(event) => void handlers.onImport(event)}
      onSearch={(event) => void handlers.onSearch(event)}
      onSearchText={handlers.onSearchText}
      onSearchSection={handlers.onSearchSection}
    />
  );
}
