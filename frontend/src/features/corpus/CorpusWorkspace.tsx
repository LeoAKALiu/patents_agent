import type { FormEvent } from "react";

import { CorpusBuildView, type CorpusJobForm } from "@/views/corpusBuildView";
import { CorpusView } from "@/views/projectViews";

import type {
  CorpusImportJob,
  CorpusStats,
  CorpusVersion,
  PatentDocument,
  SearchResult,
  SectionType,
} from "@/api";

/**
 * State slice consumed by the "corpus" workspace: corpus build (import jobs)
 * and the corpus search/import tools. The workspace is presentational —
 * handlers are passed in from App.tsx.
 */
export interface CorpusWorkspaceState {
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
      <CorpusBuildView
        form={state.corpusJobForm}
        job={state.corpusJob}
        versions={state.corpusVersions}
        stats={state.corpusStats}
        busy={state.busy}
        onFormChange={handlers.onCorpusFormChange}
        onCreateJob={(event) => void handlers.onCreateCorpusJob(event)}
        onUploadFile={(event) => void handlers.onUploadCorpusJobFile(event)}
        onRunJob={() => void handlers.onRunCorpusJob()}
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
