from __future__ import annotations

from pydantic import BaseModel, Field


class Author(BaseModel):
    name: str


class Paper(BaseModel):
    source: str = Field(description="Data source: arxiv|semantic_scholar")
    id: str = Field(description="Source-specific identifier")
    title: str
    abstract: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    doi: str | None = None
    year: int | None = None
    authors: list[Author] = Field(default_factory=list)
