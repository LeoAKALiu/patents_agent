from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from backend.app.schemas import EvidenceSourceConfig


class NonPatentSearchHit(BaseModel):
    id: str
    source: str
    query: str
    title: str
    url: str = ""
    provider_attempt_id: str = ""
    authors: list[str] = Field(default_factory=list)
    publication_year: str = ""
    abstract: str = ""
    evidence_kind: str = "non_patent_literature"


class NonPatentSearchProvider(Protocol):
    name: str
    source_id: str
    can_satisfy_patent_gate: bool

    def available(self) -> tuple[bool, str | None]: ...

    def search(self, query: str, *, limit: int) -> tuple[list[NonPatentSearchHit], list[str]]: ...


class WanfangLiteratureProvider:
    name = "万方"
    source_id = "wanfang_api"
    can_satisfy_patent_gate = False

    def __init__(self, config: EvidenceSourceConfig) -> None:
        self.config = config

    def available(self) -> tuple[bool, str | None]:
        if self.config.status != "configured" or not self.config.api_key_present:
            return False, "万方 API key 未配置；请在设置页的数据源中配置后启用非专利文献补强。"
        return True, None

    def search(self, query: str, *, limit: int) -> tuple[list[NonPatentSearchHit], list[str]]:
        del query, limit
        return [], ["wanfang_api_live_search_not_implemented"]
