from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Iterable

import httpx

from ..models import Author, Paper

ARXIV_API = "https://export.arxiv.org/api/query"


def _strip(text: str | None) -> str | None:
    if text is None:
        return None
    t = re.sub(r"\s+", " ", text).strip()
    return t or None


def search(query: str, limit: int = 10, *, timeout: float = 20.0) -> list[Paper]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
    }
    with httpx.Client(timeout=timeout, headers={"User-Agent": "paper-finder/0.1"}) as client:
        r = client.get(ARXIV_API, params=params)
        r.raise_for_status()

    root = ET.fromstring(r.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}

    papers: list[Paper] = []
    for entry in root.findall("a:entry", ns):
        entry_id = _strip(entry.findtext("a:id", default="", namespaces=ns))
        title = _strip(entry.findtext("a:title", default="", namespaces=ns)) or ""
        abstract = _strip(entry.findtext("a:summary", default="", namespaces=ns))
        authors: list[Author] = []
        for a in entry.findall("a:author", ns):
            name = _strip(a.findtext("a:name", default="", namespaces=ns))
            if name:
                authors.append(Author(name=name))

        # try pdf link
        pdf_url = None
        for link in entry.findall("a:link", ns):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href")
                break

        arxiv_id = None
        if entry_id:
            m = re.search(r"arxiv\.org/abs/(.+)$", entry_id)
            if m:
                arxiv_id = m.group(1)

        papers.append(
            Paper(
                source="arxiv",
                id=arxiv_id or entry_id or title,
                title=title,
                abstract=abstract,
                url=entry_id,
                pdf_url=pdf_url,
                authors=authors,
            )
        )

    return papers
