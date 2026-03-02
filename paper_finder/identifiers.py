from __future__ import annotations

import re
from enum import StrEnum

from .errors import InputError

_ARXIV_PATTERN = re.compile(
    r"^(?:(?P<prefix>arxiv:)?)"
    r"(?P<identifier>(?:\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?))$",
    re.IGNORECASE,
)
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_DOI_URL_PREFIX = "https://doi.org/"
_DOI_DX_PREFIX = "http://dx.doi.org/"


class IdentifierKind(StrEnum):
    ARXIV = "arxiv"
    DOI = "doi"


def normalize_arxiv_id(value: str) -> str:
    raw = value.strip()
    match = _ARXIV_PATTERN.fullmatch(raw)
    if not match:
        raise InputError(f'Invalid arXiv id: "{value}".')
    return match.group("identifier")


def normalize_doi(value: str) -> str:
    raw = value.strip()
    lowered = raw.lower()
    if lowered.startswith(_DOI_URL_PREFIX):
        raw = raw[len(_DOI_URL_PREFIX) :]
    elif lowered.startswith(_DOI_DX_PREFIX):
        raw = raw[len(_DOI_DX_PREFIX) :]

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
