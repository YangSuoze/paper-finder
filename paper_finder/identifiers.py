from __future__ import annotations

import re
from enum import StrEnum
from urllib.parse import unquote, urlparse

from .errors import InputError

_ARXIV_PATTERN = re.compile(
    r"^(?:(?P<prefix>arxiv:)?)"
    r"(?P<identifier>(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?))$",
    re.IGNORECASE,
)
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_DOI_URL_PREFIX = "https://doi.org/"
_DOI_URL_PREFIX_HTTP = "http://doi.org/"
_DOI_DX_PREFIX = "http://dx.doi.org/"
_DOI_DX_PREFIX_HTTPS = "https://dx.doi.org/"
_DOI_PREFIX = "doi:"


class IdentifierKind(StrEnum):
    ARXIV = "arxiv"
    DOI = "doi"


def _normalize_arxiv_candidate(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("arxiv.org"):
        path = unquote(parsed.path).strip("/")
        lowered_path = path.lower()
        if lowered_path.startswith("abs/"):
            return path[4:]
        if lowered_path.startswith("pdf/"):
            candidate = path[4:]
            if candidate.lower().endswith(".pdf"):
                return candidate[:-4]
            return candidate
    return raw


def normalize_arxiv_id(value: str) -> str:
    raw = _normalize_arxiv_candidate(value.strip())
    match = _ARXIV_PATTERN.fullmatch(raw)
    if not match:
        raise InputError(f'Invalid arXiv id: "{value}".')
    return match.group("identifier")


def normalize_doi(value: str) -> str:
    raw = value.strip().strip("<>")
    lowered = raw.lower()
    if lowered.startswith(_DOI_PREFIX):
        raw = raw[len(_DOI_PREFIX) :].strip()
        lowered = raw.lower()
    if lowered.startswith(_DOI_URL_PREFIX):
        raw = raw[len(_DOI_URL_PREFIX) :]
    elif lowered.startswith(_DOI_URL_PREFIX_HTTP):
        raw = raw[len(_DOI_URL_PREFIX_HTTP) :]
    elif lowered.startswith(_DOI_DX_PREFIX):
        raw = raw[len(_DOI_DX_PREFIX) :]
    elif lowered.startswith(_DOI_DX_PREFIX_HTTPS):
        raw = raw[len(_DOI_DX_PREFIX_HTTPS) :]

    if not _DOI_PATTERN.fullmatch(raw):
        raise InputError(f'Invalid DOI: "{value}".')
    return raw


def detect_identifier_kind(value: str) -> IdentifierKind:
    try:
        normalize_arxiv_id(value)
    except InputError:
        pass
    else:
        return IdentifierKind.ARXIV

    try:
        normalize_doi(value)
    except InputError as exc:
        raise InputError(
            "Could not infer identifier type. Provide a valid arXiv id or DOI, or specify --source."
        ) from exc

    return IdentifierKind.DOI
