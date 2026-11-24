#!/usr/bin/env python3
"""Discover publication candidates and build the approved Jekyll bibliography.

No network request is made by ``list``, ``approve``, ``exclude``, ``add``, or
``build``. ``discover`` never changes approvals or the published bibliography.
"""

from __future__ import annotations

import argparse
import copy
from datetime import date, timedelta
from difflib import SequenceMatcher
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = Path("_publication_review")
OUTPUT = Path("_data/publications.json")
OPENALEX = "https://api.openalex.org"
CROSSREF = "https://api.crossref.org"
ARXIV = "https://export.arxiv.org/api/query"
WORK_FIELDS = "id,ids,doi,title,authorships,publication_year,primary_location,type"
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
AUTHOR_RE = re.compile(r"^A\d+$")
WORK_RE = re.compile(r"^W\d+$")
ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$")
ALLOWED_TYPES = {"journal", "preprint", "other"}
CORRECTABLE_FIELDS = {"title", "authors", "venue", "year", "doi", "landing_page_url"}
ARXIV_RE = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z-]+)?/\d{7})(?:v(\d+))?$", re.I)
CHEMRXIV_RE = re.compile(r"^(10\.26434/chemrxiv-[a-z0-9-]+)-v(\d+)$", re.I)
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
           "opensearch": "http://a9.com/-/spec/opensearch/1.1/"}


class WorkflowError(Exception):
    """A safe, actionable error for the local publication workflow."""


def read_json(path: Path, default):
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkflowError(f"Cannot read {path}: {error}") from error


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def clean_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", value)).split())


def normalize_doi(value) -> str | None:
    if not isinstance(value, str):
        return None
    doi = unquote(value.strip()).lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", doi)
    return doi if DOI_RE.fullmatch(doi) else None


def normalize_arxiv_id(value) -> tuple[str, int | None] | None:
    if not isinstance(value, str):
        return None
    identifier = value.strip().lower()
    identifier = re.sub(r"^(?:https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/|arxiv:|10\.48550/arxiv\.)", "", identifier)
    identifier = identifier.removesuffix(".pdf").rstrip("/")
    match = ARXIV_RE.fullmatch(identifier)
    if not match:
        return None
    version = int(match.group(1)) if match.group(1) else None
    base = identifier[:identifier.rfind("v")] if version else identifier
    return base, version


def arxiv_from_record(record: dict) -> str | None:
    for value in [record.get("arxiv_id"), record.get("doi"), record.get("landing_page_url"),
                  *record.get("identifiers", [])]:
        normalized = normalize_arxiv_id(value)
        if normalized:
            return normalized[0]
    return None


def canonical_arxiv_url(value: str | None) -> str | None:
    normalized = normalize_arxiv_id(value)
    return f"https://arxiv.org/abs/{normalized[0]}" if normalized else value


def short_openalex_id(value, prefix: str) -> str | None:
    if not isinstance(value, str):
        return None
    identifier = value.rstrip("/").rsplit("/", 1)[-1]
    pattern = AUTHOR_RE if prefix == "A" else WORK_RE
    return identifier if pattern.fullmatch(identifier) else None


def external_identifier(value, kind: str) -> str | None:
    if not value:
        return None
    text = str(value).rstrip("/").rsplit("/", 1)[-1].strip().lower()
    if kind == "pmid" and text.isdigit():
        return f"pmid:{text}"
    if kind == "pmcid" and re.fullmatch(r"pmc\d+", text):
        return f"pmcid:{text}"
    return None


def unique(values):
    return list(dict.fromkeys(value for value in values if value))


def unique_relations(values):
    seen, result = set(), []
    for value in values:
        if not isinstance(value, dict):
            continue
        key = (value.get("type"), value.get("doi"))
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def title_fingerprint(title: str, year) -> str:
    normalized = re.sub(r"\W+", "", title.casefold())
    digest = hashlib.sha256(f"{normalized}|{year or ''}".encode()).hexdigest()[:16]
    return f"title:{digest}"


def aliases(record: dict) -> set[str]:
    return set(record.get("identifiers", [])) | {record["id"]}


def missing_warnings(record: dict) -> list[str]:
    return [f"Missing {field}" for field in ("title", "authors", "venue", "year") if not record.get(field)]


def normalize_openalex_work(work: dict, researcher: str) -> dict | None:
    if not isinstance(work, dict):
        return None
    ids = work.get("ids") or {}
    if not isinstance(ids, dict):
        ids = {}
    doi = normalize_doi(work.get("doi") or ids.get("doi"))
    arxiv = normalize_arxiv_id(doi or "") or normalize_arxiv_id((work.get("primary_location") or {}).get("landing_page_url") if isinstance(work.get("primary_location"), dict) else None)
    work_id = short_openalex_id(work.get("id") or ids.get("openalex"), "W")
    title = clean_text(work.get("title"))
    year = work.get("publication_year")
    year = year if isinstance(year, int) and not isinstance(year, bool) else None
    identifiers = unique([
        f"doi:{doi}" if doi else None,
        f"openalex:{work_id}" if work_id else None,
        external_identifier(ids.get("pmid"), "pmid"),
        external_identifier(ids.get("pmcid"), "pmcid"),
        f"arxiv:{arxiv[0]}" if arxiv else None,
    ])
    if not identifiers and not title:
        return None
    if not identifiers:
        identifiers = [title_fingerprint(title, year)]
    authors = []
    authorships = work.get("authorships")
    for authorship in authorships if isinstance(authorships, list) else []:
        if isinstance(authorship, dict):
            author = authorship.get("author") or {}
            if not isinstance(author, dict):
                author = {}
            name = clean_text(author.get("display_name") or authorship.get("raw_author_name"))
            if name:
                authors.append(name)
    location = work.get("primary_location")
    location = location if isinstance(location, dict) else {}
    source = location.get("source")
    source = source if isinstance(source, dict) else {}
    venue = clean_text(source.get("display_name"))
    work_type = work.get("type")
    source_type = source.get("type")
    suggested = "preprint" if work_type == "preprint" else "journal" if work_type == "article" and source_type == "journal" else "other"
    record = {
        "id": identifiers[0],
        "identifiers": identifiers,
        "doi": doi,
        "title": title,
        "authors": unique(authors),
        "venue": venue,
        "year": year,
        "suggested_type": suggested,
        "landing_page_url": canonical_arxiv_url(location.get("landing_page_url")) if isinstance(location.get("landing_page_url"), str) else None,
        "discovered_from": [researcher],
        "metadata_warnings": [],
        "crossref_status": "not_checked",
    }
    if arxiv:
        record["arxiv_id"] = arxiv[0]
        record["arxiv_versions"] = [arxiv[1]] if arxiv[1] else []
    record["metadata_warnings"] = missing_warnings(record)
    return record


def merge_record(old: dict, new: dict) -> dict:
    merged = copy.deepcopy(old)
    old_doi, new_doi = normalize_doi(old.get("doi")), normalize_doi(new.get("doi"))
    warnings = list(old.get("metadata_warnings", [])) + list(new.get("metadata_warnings", []))
    if old_doi and new_doi and old_doi != new_doi:
        warnings.append("Conflicting DOIs for matching identifiers; review before approval")
    for key, value in new.items():
        if key not in {"id", "identifiers", "discovered_from", "metadata_warnings", "arxiv_versions", "version_relations"} and value not in (None, "", []):
            merged[key] = copy.deepcopy(value)
    merged["identifiers"] = unique([*old.get("identifiers", []), old["id"], *new.get("identifiers", []), new["id"]])
    merged["discovered_from"] = unique([*old.get("discovered_from", []), *new.get("discovered_from", [])])
    versions = sorted(set(old.get("arxiv_versions", []) + new.get("arxiv_versions", [])))
    relations = unique_relations([*old.get("version_relations", []), *new.get("version_relations", [])])
    if versions:
        merged["arxiv_versions"] = versions
    else:
        merged.pop("arxiv_versions", None)
    if relations:
        merged["version_relations"] = relations
    else:
        merged.pop("version_relations", None)
    doi = normalize_doi(merged.get("doi"))
    merged["id"] = f"doi:{doi}" if doi else old["id"]
    merged["identifiers"] = unique([merged["id"], *merged["identifiers"]])
    merged["metadata_warnings"] = unique([
        warning for warning in warnings if not (warning.startswith("Missing ") and merged.get(warning.removeprefix("Missing ")))
    ] + missing_warnings(merged))
    return merged


def same_version(first: dict, second: dict) -> bool:
    shared = aliases(first) & aliases(second)
    if not shared:
        return False
    if any(value.startswith(("doi:", "arxiv:")) for value in shared):
        return True
    first_doi, second_doi = normalize_doi(first.get("doi")), normalize_doi(second.get("doi"))
    if first.get("suggested_type") != second.get("suggested_type"):
        # OpenAlex can reclassify a DOI-free work between "article" and
        # "other". Its unchanged work ID still denotes the same record.
        # Keep preprint/journal versions separate for work-level review.
        types = {first.get("suggested_type"), second.get("suggested_type")}
        if not ("other" in types and types <= {"journal", "other"} and
                any(value.startswith("openalex:") for value in shared)):
            return False
    return not (first_doi and second_doi and first_doi != second_doi)


def deduplicate(records: list[dict]) -> list[dict]:
    result: list[dict] = []
    for source in records:
        if not isinstance(source, dict):
            raise WorkflowError("Publication records must be objects")
        record = copy.deepcopy(source)
        if (not isinstance(record.get("id"), str) or not record["id"] or
                not isinstance(record.get("identifiers", []), list) or
                not all(isinstance(identifier, str) for identifier in record.get("identifiers", []))):
            raise WorkflowError("A publication record has no stable id")
        matches = [index for index, current in enumerate(result) if same_version(current, record)]
        for index in reversed(matches):
            record = merge_record(result.pop(index), record)
        result.append(record)
    if len({item["id"] for item in result}) != len(result):
        raise WorkflowError("Multiple candidate versions have the same ID; review their source metadata")
    return sorted(result, key=lambda item: item["id"])


def _first_text(value) -> str:
    if isinstance(value, list):
        return clean_text(value[0]) if value else ""
    return clean_text(value)


def enrich_crossref(record: dict, message: dict | None, checked_on: str) -> dict:
    enriched = copy.deepcopy(record)
    enriched["crossref_checked_on"] = checked_on
    if message is None:
        enriched["crossref_status"] = "not_found"
        return enriched
    if not isinstance(message, dict):
        raise WorkflowError("Crossref returned malformed metadata")
    enriched["crossref_status"] = "verified"
    relations = []
    relation_data = message.get("relation") or {}
    if isinstance(relation_data, dict):
        for relation_type in ("is-preprint-of", "has-preprint", "is-version-of", "has-version"):
            for item in relation_data.get(relation_type, []):
                if isinstance(item, dict) and item.get("id-type") == "doi":
                    related_doi = normalize_doi(item.get("id"))
                    if related_doi:
                        relations.append({"type": relation_type, "doi": related_doi})
    enriched["version_relations"] = unique_relations([*enriched.get("version_relations", []), *relations])
    cross_doi = normalize_doi(message.get("DOI"))
    if cross_doi and record.get("doi") and cross_doi != record["doi"]:
        enriched["metadata_warnings"] = unique([*record.get("metadata_warnings", []), "Crossref DOI differs from OpenAlex DOI"])
    cross_title = _first_text(message.get("title"))
    if cross_title and record.get("title") and re.sub(r"\W+", "", cross_title.casefold()) != re.sub(r"\W+", "", record["title"].casefold()):
        enriched["metadata_warnings"] = unique([*enriched.get("metadata_warnings", []), "Crossref title differs from OpenAlex title"])
    cross_authors = []
    crossref_authors = message.get("author")
    for author in crossref_authors if isinstance(crossref_authors, list) else []:
        if isinstance(author, dict):
            name = clean_text(author.get("name") or " ".join(str(author.get(part, "")) for part in ("given", "family")))
            if name:
                cross_authors.append(name)
    published = message.get("published") or message.get("issued") or {}
    parts = published.get("date-parts") if isinstance(published, dict) else []
    cross_year = parts[0][0] if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0] else None
    cross_year = cross_year if isinstance(cross_year, int) else None
    if cross_year and record.get("year") and cross_year != record["year"]:
        enriched["metadata_warnings"] = unique([*enriched.get("metadata_warnings", []), "Crossref publication year differs from OpenAlex year"])
    for field, value in {
        "title": cross_title,
        "authors": cross_authors,
        "venue": _first_text(message.get("container-title")),
        "year": cross_year,
        "landing_page_url": message.get("URL"),
    }.items():
        if not enriched.get(field) and value:
            enriched[field] = value
    if enriched.get("suggested_type") == "other":
        if message.get("type") == "journal-article":
            enriched["suggested_type"] = "journal"
        elif message.get("type") == "posted-content":
            enriched["suggested_type"] = "preprint"
    enriched["metadata_warnings"] = unique([
        warning for warning in enriched.get("metadata_warnings", [])
        if not (warning.startswith("Missing ") and enriched.get(warning.removeprefix("Missing ")))
    ] + missing_warnings(enriched))
    return enriched


class HttpClient:
    def __init__(self, contact_email: str | None, opener=urlopen, sleeper=time.sleep, clock=time.monotonic):
        self.contact_email = contact_email
        self.opener = opener
        self.sleeper = sleeper
        self.clock = clock
        self.last_request = None

    def get_json(self, url: str, *, allow_404: bool = False):
        path = urlparse(url).path
        for attempt in range(4):
            if self.last_request is not None:
                self.sleeper(max(0, 0.25 - (self.clock() - self.last_request)))
            self.last_request = self.clock()
            agent = "AutoDIAL-publications/1.0"
            if self.contact_email:
                agent += f" (mailto:{self.contact_email})"
            request = Request(url, headers={"User-Agent": agent, "Accept": "application/json"})
            try:
                with self.opener(request, timeout=20) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code == 404 and allow_404:
                    return None
                if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise WorkflowError(f"HTTP {error.code} from {path}; no publication files changed") from error
                retry_after = error.headers.get("Retry-After") if error.headers else None
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                self.sleeper(min(delay, 60))
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                if attempt == 3:
                    raise WorkflowError(f"Request or JSON failure from {path}; no publication files changed: {error}") from error
                self.sleeper(2**attempt)
        raise AssertionError("retry loop ended unexpectedly")

    def get_text(self, url: str) -> str:
        path = urlparse(url).path
        for attempt in range(4):
            if self.last_request is not None:
                self.sleeper(max(0, 3 - (self.clock() - self.last_request)))
            self.last_request = self.clock()
            request = Request(url, headers={"User-Agent": "AutoDIAL-publications/1.0", "Accept": "application/atom+xml"})
            try:
                with self.opener(request, timeout=30) as response:
                    return response.read().decode("utf-8")
            except HTTPError as error:
                if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                    raise WorkflowError(f"HTTP {error.code} from {path}; no publication files changed") from error
                retry_after = error.headers.get("Retry-After") if error.headers else None
                self.sleeper(min(int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt, 60))
            except (URLError, TimeoutError, UnicodeDecodeError) as error:
                if attempt == 3:
                    raise WorkflowError(f"Request failure from {path}; no publication files changed: {error}") from error
                self.sleeper(2**attempt)
        raise AssertionError("retry loop ended unexpectedly")


def validate_researchers(config: dict) -> list[dict]:
    researchers = config.get("researchers") if isinstance(config, dict) else None
    if not isinstance(researchers, list) or not researchers:
        raise WorkflowError("No verified researchers configured. See docs/PUBLICATIONS_WORKFLOW.md")
    for researcher in researchers:
        if not isinstance(researcher, dict):
            raise WorkflowError("Researcher entries must be objects")
        author_id = researcher.get("openalex_author_id")
        if not isinstance(author_id, str) or not AUTHOR_RE.fullmatch(author_id):
            raise WorkflowError("Each researcher needs a verified OpenAlex author ID (A followed by digits)")
        if researcher.get("verified") is not True or not researcher.get("verified_by"):
            raise WorkflowError(f"{author_id}: record who verified the author profile before discovery")
        if not clean_text(researcher.get("name")) or not str(researcher.get("verification_url", "")).startswith("https://"):
            raise WorkflowError(f"{author_id}: name and HTTPS verification_url are required")
        if researcher.get("relationship") not in {"pi", "current", "former"}:
            raise WorkflowError(f"{author_id}: relationship must be pi, current, or former")
        orcid = researcher.get("orcid")
        if orcid and not ORCID_RE.fullmatch(orcid):
            raise WorkflowError(f"{author_id}: invalid ORCID format")
    return researchers


def fetch_author_works(client: HttpClient, researcher: dict, api_key: str | None, *, per_page: int = 100) -> list[dict]:
    author_id = researcher["openalex_author_id"]
    key_params = {"api_key": api_key} if api_key else {}
    profile = client.get_json(f"{OPENALEX}/authors/{author_id}?{urlencode(key_params)}")
    if not isinstance(profile, dict) or short_openalex_id(profile.get("id"), "A") != author_id:
        raise WorkflowError(f"OpenAlex returned the wrong author profile for {author_id}")
    expected_orcid = researcher.get("orcid")
    if expected_orcid:
        found = [profile.get("orcid"), *(profile.get("observed_orcids") or [])]
        if not any(value and str(value).rstrip("/").endswith(expected_orcid) for value in found):
            raise WorkflowError(f"{author_id}: configured ORCID does not match the OpenAlex profile")

    works = []
    seen_cursors = set()
    cursor = "*"
    page = 1
    while True:
        params = {"filter": f"author.id:{author_id}", "per_page": per_page, "select": WORK_FIELDS, **key_params}
        if api_key:
            params["cursor"] = cursor
        else:
            params["page"] = page
        payload = client.get_json(f"{OPENALEX}/works?{urlencode(params)}")
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list) or not isinstance(payload.get("meta"), dict):
            raise WorkflowError(f"OpenAlex returned malformed works data for {author_id}")
        results, meta = payload["results"], payload["meta"]
        if not api_key and isinstance(meta.get("count"), int) and meta["count"] > 10_000:
            raise WorkflowError(f"{author_id} has over 10,000 works; set OPENALEX_API_KEY for cursor paging")
        works.extend(results)
        if api_key:
            next_cursor = meta.get("next_cursor")
            if not results or not next_cursor:
                break
            if next_cursor in seen_cursors:
                raise WorkflowError(f"OpenAlex repeated a cursor for {author_id}")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            if len(results) < per_page:
                break
            page += 1
            if page * per_page > 10_000:
                raise WorkflowError(f"{author_id} reached the basic paging limit; set OPENALEX_API_KEY")
    return works


def parse_arxiv_feed(xml_text: str) -> tuple[list[ET.Element], int]:
    try:
        feed = ET.fromstring(xml_text)
        total = int(feed.findtext("opensearch:totalResults", default="0", namespaces=ATOM_NS))
    except (ET.ParseError, ValueError) as error:
        raise WorkflowError(f"arXiv returned malformed Atom data: {error}") from error
    return feed.findall("atom:entry", ATOM_NS), total


def normalize_arxiv_entry(entry: ET.Element, discovered_from: str) -> dict:
    identifier = normalize_arxiv_id(entry.findtext("atom:id", namespaces=ATOM_NS))
    if not identifier:
        raise WorkflowError("arXiv returned an entry with an invalid identifier")
    arxiv_id, version = identifier
    authors = [clean_text(author.findtext("atom:name", namespaces=ATOM_NS)) for author in entry.findall("atom:author", ATOM_NS)]
    published = clean_text(entry.findtext("atom:published", namespaces=ATOM_NS))
    year = int(published[:4]) if re.match(r"^\d{4}-", published) else None
    repository_doi = f"10.48550/arxiv.{arxiv_id}"
    supplied_doi = normalize_doi(entry.findtext("arxiv:doi", namespaces=ATOM_NS))
    relations = ([{"type": "is-preprint-of", "doi": supplied_doi}]
                 if supplied_doi and supplied_doi != repository_doi else [])
    record = {
        "id": f"doi:{repository_doi}",
        "identifiers": [f"doi:{repository_doi}", f"arxiv:{arxiv_id}"],
        "doi": repository_doi,
        "arxiv_id": arxiv_id,
        "arxiv_versions": [version] if version else [],
        "arxiv_updated": clean_text(entry.findtext("atom:updated", namespaces=ATOM_NS)),
        "title": clean_text(entry.findtext("atom:title", namespaces=ATOM_NS)),
        "authors": unique(authors), "venue": "arXiv", "year": year,
        "suggested_type": "preprint",
        "landing_page_url": f"https://arxiv.org/abs/{arxiv_id}",
        "discovered_from": [discovered_from], "identity_status": "needs_review",
        "metadata_warnings": [], "crossref_status": "not_required",
        "version_relations": relations,
    }
    record["metadata_warnings"] = missing_warnings(record)
    return record


def arxiv_query(client: HttpClient, params: dict) -> tuple[list[ET.Element], int]:
    return parse_arxiv_feed(client.get_text(f"{ARXIV}?{urlencode(params)}"))


def discover_arxiv_records(root: Path, client: HttpClient) -> list[dict]:
    config = read_json(root / REVIEW_DIR / "arxiv_sources.json", {"known_ids": [], "author_searches": []})
    if not isinstance(config, dict) or not isinstance(config.get("known_ids"), list) or not isinstance(config.get("author_searches"), list):
        raise WorkflowError("arxiv_sources.json needs known_ids and author_searches arrays")
    researchers = validate_researchers(read_json(root / REVIEW_DIR / "researchers.json", {"researchers": []}))
    researcher_names = {item["name"] for item in researchers}
    found = []
    known = {}
    for source in config["known_ids"]:
        if (not isinstance(source, dict) or source.get("researcher") not in researcher_names or
                not source.get("verified_by") or not str(source.get("verification_url", "")).startswith("https://")):
            raise WorkflowError("Each known arXiv ID needs a configured researcher, HTTPS verification_url, and verified_by")
        normalized = normalize_arxiv_id(source.get("arxiv_id"))
        if not normalized:
            raise WorkflowError("Invalid known arXiv ID")
        known[normalized[0]] = source
    ids = list(known)
    for offset in range(0, len(ids), 20):
        batch = ids[offset:offset + 20]
        entries, _ = arxiv_query(client, {"id_list": ",".join(batch), "max_results": len(batch)})
        returned = set()
        for entry in entries:
            normalized = normalize_arxiv_id(entry.findtext("atom:id", namespaces=ATOM_NS))
            if normalized and normalized[0] in known:
                source = known[normalized[0]]
                record = normalize_arxiv_entry(entry, f"arXiv known ID: {source['researcher']}")
                if source["researcher"].casefold() not in {name.casefold() for name in record["authors"]}:
                    raise WorkflowError(f"arXiv {normalized[0]} does not list configured researcher {source['researcher']}")
                found.append(record)
                returned.add(normalized[0])
        if returned != set(batch):
            raise WorkflowError(f"arXiv did not return configured IDs: {', '.join(sorted(set(batch) - returned))}")
    for source in config["author_searches"]:
        if (not isinstance(source, dict) or source.get("researcher") not in researcher_names or
                not source.get("verified_by") or not str(source.get("verification_url", "")).startswith("https://")):
            raise WorkflowError("Each arXiv author search needs a configured researcher, HTTPS verification_url, and verified_by")
        name = clean_text(source.get("name"))
        if not name or len(name.split()) < 2:
            raise WorkflowError("arXiv author searches need a full author name")
        limit = source.get("max_results", 200)
        if not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise WorkflowError("arXiv max_results must be between 1 and 1000")
        start = 0
        while start < limit:
            entries, total = arxiv_query(client, {"search_query": f'au:"{name}"', "start": start,
                                                   "max_results": min(100, limit - start), "sortBy": "submittedDate",
                                                   "sortOrder": "descending"})
            if not entries:
                break
            for entry in entries:
                record = normalize_arxiv_entry(entry, f"arXiv author search: {source['researcher']}")
                if name.casefold() in {author.casefold() for author in record["authors"]}:
                    found.append(record)
            start += len(entries)
            if start >= total:
                break
        if total > limit:
            raise WorkflowError(f"arXiv search for {name} exceeds max_results={limit}; increase the reviewed limit")
    path = root / REVIEW_DIR / "candidates.json"
    data = read_json(path, {"records": []})
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise WorkflowError("candidates.json must contain a records array")
    merged = deduplicate([*data["records"], *found])
    write_json(path, {"records": merged})
    return merged


def find_match(records: list[dict], record: dict) -> dict | None:
    return next((item for item in records if same_version(item, record)), None)


def recent_crossref_check(record: dict | None) -> bool:
    if not record or record.get("crossref_status") not in {"verified", "not_found"}:
        return False
    try:
        return date.fromisoformat(record["crossref_checked_on"]) >= date.today() - timedelta(days=30)
    except (KeyError, TypeError, ValueError):
        return False


def discover_records(root: Path, client: HttpClient, api_key: str | None, contact_email: str | None, *, crossref: bool = True, refresh_crossref: bool = False) -> list[dict]:
    researchers = validate_researchers(read_json(root / REVIEW_DIR / "researchers.json", {"researchers": []}))
    if crossref and not contact_email:
        raise WorkflowError("Set PUBLICATIONS_CONTACT_EMAIL or pass --contact-email for Crossref's polite pool")
    cached_data = read_json(root / REVIEW_DIR / "candidates.json", {"records": []})
    if not isinstance(cached_data, dict) or not isinstance(cached_data.get("records"), list):
        raise WorkflowError("candidates.json must contain a records array")
    cache = cached_data["records"]
    discovered = []
    for researcher in researchers:
        for work in fetch_author_works(client, researcher, api_key):
            record = normalize_openalex_work(work, researcher["name"])
            if record is None:
                continue
            previous = find_match([*cache, *discovered], record)
            reuse_crossref = previous and recent_crossref_check(previous) and (not crossref or not refresh_crossref)
            if reuse_crossref:
                record = merge_record(previous, record)
                record["crossref_status"] = previous["crossref_status"]
                record["crossref_checked_on"] = previous["crossref_checked_on"]
            if crossref and record.get("doi") and not reuse_crossref:
                doi_path = quote(record["doi"], safe="/")
                query = urlencode({"mailto": contact_email})
                response = client.get_json(f"{CROSSREF}/works/{doi_path}?{query}", allow_404=True)
                message = response.get("message") if isinstance(response, dict) else None
                if response is not None and not isinstance(message, dict):
                    raise WorkflowError(f"Crossref returned malformed metadata for {record['doi']}")
                record = enrich_crossref(record, message, date.today().isoformat())
            discovered.append(record)
    merged = deduplicate([*cache, *discovered])
    write_json(root / REVIEW_DIR / "candidates.json", {"records": merged})
    return merged


def verify_candidate_doi(root: Path, identifier: str, client: HttpClient, contact_email: str | None) -> dict:
    path = root / REVIEW_DIR / "candidates.json"
    data = read_json(path, {"records": []})
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        raise WorkflowError("candidates.json must contain a records array")
    records = data["records"]
    record = find_record(records, identifier)
    doi = normalize_doi(record.get("doi"))
    if not doi:
        raise WorkflowError(f"{identifier}: Crossref verification needs a DOI")
    query = f"?{urlencode({'mailto': contact_email})}" if contact_email else ""
    response = client.get_json(f"{CROSSREF}/works/{quote(doi, safe='/')}{query}", allow_404=True)
    message = response.get("message") if isinstance(response, dict) else None
    if response is not None and not isinstance(message, dict):
        raise WorkflowError(f"Crossref returned malformed metadata for {doi}")
    enriched = enrich_crossref(record, message, date.today().isoformat())
    records[records.index(record)] = enriched
    write_json(path, data)
    return enriched


def normalize_manual(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise WorkflowError("Manual publication entries must be objects")
    doi = normalize_doi(raw.get("doi"))
    if raw.get("doi") and not doi:
        raise WorkflowError("Manual DOI is invalid")
    manual_id = raw.get("id")
    if manual_id and (not isinstance(manual_id, str) or not re.fullmatch(r"manual:[a-z0-9-]+", manual_id)):
        raise WorkflowError("Manual id must look like manual:short-slug")
    if not doi and not manual_id:
        raise WorkflowError("A manual publication needs a DOI or manual:slug id")
    identifiers = unique([f"doi:{doi}" if doi else None, manual_id])
    raw_authors = raw.get("authors", [])
    if not isinstance(raw_authors, list):
        raise WorkflowError("Manual authors must be an array")
    record = {
        "id": identifiers[0], "identifiers": identifiers, "doi": doi,
        "title": clean_text(raw.get("title")),
        "authors": [clean_text(author) for author in raw_authors if clean_text(author)],
        "venue": clean_text(raw.get("venue")),
        "year": raw.get("year"),
        "suggested_type": "other", "landing_page_url": raw.get("landing_page_url"),
        "discovered_from": ["manual"], "metadata_warnings": [],
    }
    record["metadata_warnings"] = missing_warnings(record)
    return record


def load_records(root: Path) -> list[dict]:
    candidate_data = read_json(root / REVIEW_DIR / "candidates.json", {"records": []})
    manual_data = read_json(root / REVIEW_DIR / "manual.json", {"records": []})
    if not isinstance(candidate_data, dict) or not isinstance(manual_data, dict):
        raise WorkflowError("Candidate and manual files must contain records arrays")
    candidates, manual = candidate_data.get("records"), manual_data.get("records")
    if not isinstance(candidates, list) or not isinstance(manual, list):
        raise WorkflowError("Candidate and manual files must contain records arrays")
    return deduplicate([*candidates, *(normalize_manual(item) for item in manual)])


def load_decisions(root: Path) -> dict:
    decision_data = read_json(root / REVIEW_DIR / "decisions.json", {"decisions": {}})
    if not isinstance(decision_data, dict):
        raise WorkflowError("decisions.json must contain a decisions object")
    decisions = decision_data.get("decisions")
    if not isinstance(decisions, dict):
        raise WorkflowError("decisions.json must contain a decisions object")
    if any(not isinstance(value, dict) for value in decisions.values()):
        raise WorkflowError("Each publication decision must be an object")
    return decisions


def work_seed(identifier: str) -> dict:
    digest = hashlib.sha256(identifier.encode()).hexdigest()[:12]
    return {"id": f"work-{digest}", "site_id": f"publication-{digest}",
            "version_ids": [identifier], "matches": []}


def group_for_record(groups: list[dict], record: dict) -> dict | None:
    found = [group for group in groups if any(identifier in aliases(record) for identifier in group["version_ids"])]
    if len(found) > 1:
        raise WorkflowError(f"{record['id']}: version belongs to multiple work groups")
    return found[0] if found else None


def load_work_groups(root: Path, records: list[dict]) -> list[dict]:
    data = read_json(root / REVIEW_DIR / "works.json", {"works": []})
    if not isinstance(data, dict) or not isinstance(data.get("works"), list):
        raise WorkflowError("works.json needs a works array")
    groups = copy.deepcopy(data["works"])
    if any(not isinstance(group, dict) or not isinstance(group.get("version_ids"), list) or
           not group.get("id") or not group.get("site_id") for group in groups):
        raise WorkflowError("Malformed work group in works.json")
    if len({group["id"] for group in groups}) != len(groups) or len({group["site_id"] for group in groups}) != len(groups):
        raise WorkflowError("Duplicate work or site ID in works.json")
    for record in records:
        if group_for_record(groups, record) is None:
            groups.append(work_seed(record["id"]))
    for group in groups:
        for identifier in group["version_ids"]:
            find_record(records, identifier)
    return groups


def strong_match_reasons(first: dict, second: dict) -> list[str]:
    reasons = []
    shared_openalex = {value for value in aliases(first) & aliases(second) if value.startswith("openalex:")}
    if shared_openalex and "preprint" in {first.get("suggested_type"), second.get("suggested_type")} and not same_version(first, second):
        reasons.append("shared OpenAlex work identity")
    first_doi, second_doi = normalize_doi(first.get("doi")), normalize_doi(second.get("doi"))
    for record, target in ((first, second_doi), (second, first_doi)):
        if target and any(relation.get("doi") == target for relation in record.get("version_relations", [])):
            reasons.append("explicit repository or Crossref version relationship")
    if first_doi and second_doi:
        first_chem, second_chem = CHEMRXIV_RE.fullmatch(first_doi), CHEMRXIV_RE.fullmatch(second_doi)
        if first_chem and second_chem and first_chem.group(1) == second_chem.group(1):
            reasons.append("same ChemRxiv manuscript identifier")
    return unique(reasons)


def possible_match(first: dict, second: dict) -> dict | None:
    types = {first.get("suggested_type"), second.get("suggested_type")}
    if "preprint" not in types or not types <= {"journal", "preprint"}:
        return None
    years = first.get("year"), second.get("year")
    if all(isinstance(year, int) for year in years) and abs(years[0] - years[1]) > 3:
        return None
    title_a, title_b = clean_text(first.get("title")).casefold(), clean_text(second.get("title")).casefold()
    if not title_a or not title_b:
        return None
    similarity = SequenceMatcher(None, title_a, title_b).ratio()
    authors_a = {re.sub(r"\W+", "", name.casefold()) for name in first.get("authors", [])}
    authors_b = {re.sub(r"\W+", "", name.casefold()) for name in second.get("authors", [])}
    overlap = len(authors_a & authors_b) / min(len(authors_a), len(authors_b)) if authors_a and authors_b else 0
    if similarity < 0.86 or overlap < 0.25:
        return None
    return {"version_ids": [first["id"], second["id"]], "title_similarity": round(similarity, 3),
            "author_overlap": round(overlap, 3), "reason": "possible match; manual review required"}


def group_approved_ids(group: dict, records: list[dict], decisions: dict) -> list[str]:
    return [record["id"] for record in records if group_for_record([group], record) and
            (find_decision(record, decisions)[1] or {}).get("status") == "approved"]


def join_groups(groups: list[dict], first: dict, second: dict, evidence: dict,
                records: list[dict], decisions: dict, *, keep_work: str | None = None) -> dict:
    if first is second:
        return first
    first_approved = group_approved_ids(first, records, decisions)
    second_approved = group_approved_ids(second, records, decisions)
    if first_approved and second_approved and not keep_work:
        raise WorkflowError("Both works have approvals; use --keep-work to choose the stable site ID")
    if keep_work and keep_work not in {first["id"], second["id"]}:
        raise WorkflowError("--keep-work must name one of the two work IDs")
    keeper = (first if first["id"] == keep_work else second) if keep_work else (
        first if first_approved or (not second_approved and first["id"] < second["id"]) else second)
    other = second if keeper is first else first
    keeper["version_ids"] = unique([*keeper["version_ids"], *other["version_ids"]])
    keeper["matches"] = [*keeper.get("matches", []), *other.get("matches", []), evidence]
    keeper["retired_work_ids"] = unique([*keeper.get("retired_work_ids", []), *other.get("retired_work_ids", []), other["id"]])
    groups.remove(other)
    return keeper


def sync_work_registry(root: Path, records: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    records = records if records is not None else load_records(root)
    decisions = load_decisions(root)
    validate_decision_targets(records, decisions)
    persisted = read_json(root / REVIEW_DIR / "works.json", {"works": []})
    if not isinstance(persisted, dict) or not isinstance(persisted.get("works"), list):
        raise WorkflowError("works.json needs a works array")
    existing_group_ids = {group["id"] for group in persisted["works"] if isinstance(group, dict) and isinstance(group.get("id"), str)}
    groups = load_work_groups(root, records)
    assignments = {record["id"]: group_for_record(groups, record) for record in records}
    conflicts = []
    for index, first in enumerate(records):
        for second in records[index + 1:]:
            reasons = strong_match_reasons(first, second)
            if not reasons:
                continue
            first_group, second_group = assignments[first["id"]], assignments[second["id"]]
            if first_group is second_group:
                continue
            evidence = {"from": first["id"], "to": second["id"], "method": "metadata",
                        "note": "; ".join(reasons)}
            try:
                keep_work = None
                if not group_approved_ids(first_group, records, decisions) and not group_approved_ids(second_group, records, decisions):
                    if first_group["id"] in existing_group_ids and second_group["id"] not in existing_group_ids:
                        keep_work = first_group["id"]
                    elif second_group["id"] in existing_group_ids and first_group["id"] not in existing_group_ids:
                        keep_work = second_group["id"]
                keeper = join_groups(groups, first_group, second_group, evidence, records, decisions, keep_work=keep_work)
                for record_id, assignment in assignments.items():
                    if assignment in (first_group, second_group):
                        assignments[record_id] = keeper
            except WorkflowError as error:
                conflicts.append({"version_ids": [first["id"], second["id"]], "reason": str(error)})
    suggestions = list(conflicts)
    rejected = read_json(root / REVIEW_DIR / "rejected_matches.json", {"matches": []})
    rejected_pairs = {frozenset(item["version_ids"]) for item in rejected.get("matches", [])}
    seen_group_pairs = set()
    for index, first in enumerate(records):
        for second in records[index + 1:]:
            first_group, second_group = assignments[first["id"]], assignments[second["id"]]
            if first_group is second_group:
                continue
            if frozenset((first["id"], second["id"])) in rejected_pairs:
                continue
            suggestion = possible_match(first, second)
            group_pair = frozenset((first_group["id"], second_group["id"]))
            if suggestion and group_pair not in seen_group_pairs:
                suggestions.append(suggestion)
                seen_group_pairs.add(group_pair)
    write_json(root / REVIEW_DIR / "works.json", {"works": sorted(groups, key=lambda group: group["id"])})
    write_json(root / REVIEW_DIR / "possible_matches.json", {"matches": suggestions})
    return groups, suggestions


def find_decision(record: dict, decisions: dict) -> tuple[str | None, dict | None]:
    matches = [(key, value) for key, value in decisions.items() if key in aliases(record)]
    if len(matches) > 1:
        raise WorkflowError(f"Multiple decisions refer to {record['id']}; consolidate them before building")
    return matches[0] if matches else (None, None)


def validate_decision_targets(records: list[dict], decisions: dict) -> None:
    for identifier in decisions:
        matches = [record["id"] for record in records if identifier in aliases(record)]
        if len(matches) > 1:
            raise WorkflowError(f"Decision {identifier} matches multiple versions: {', '.join(matches)}; resolve before building")


def find_record(records: list[dict], identifier: str) -> dict:
    matches = [record for record in records if identifier in aliases(record)]
    if len(matches) != 1:
        raise WorkflowError(f"Publication id {identifier!r} is unknown or ambiguous; run list first")
    return matches[0]


def validate_url(value, label: str) -> str:
    if not isinstance(value, str) or urlparse(value).scheme != "https" or not urlparse(value).netloc:
        raise WorkflowError(f"{label} must be an HTTPS URL")
    return value


def publication_from_record(record: dict, decision: dict, root: Path) -> dict:
    if decision.get("status") != "approved" or decision.get("type") not in ALLOWED_TYPES:
        raise WorkflowError(f"{record['id']}: approval needs an explicit journal, preprint, or other type")
    if not clean_text(decision.get("reviewer")) or not clean_text(decision.get("note")):
        raise WorkflowError(f"{record['id']}: approval needs reviewer and evidence note")
    if decision["type"] == "preprint" and arxiv_from_record(record) and not clean_text(decision.get("identity_evidence")):
        raise WorkflowError(f"{record['id']}: arXiv preprint approval needs verified author identity evidence")
    overrides = decision.get("overrides") or {}
    if not isinstance(overrides, dict) or set(overrides) - (CORRECTABLE_FIELDS | {"image", "software_url", "dataset_url", "extra_links"}):
        raise WorkflowError(f"{record['id']}: unsupported editorial override")
    data = copy.deepcopy(record)
    for field in CORRECTABLE_FIELDS:
        if field in overrides:
            data[field] = overrides[field]
    title, venue = clean_text(data.get("title")), clean_text(data.get("venue"))
    authors = data.get("authors")
    year = data.get("year")
    if not title or not venue or not isinstance(authors, list) or not authors or not all(clean_text(author) for author in authors):
        raise WorkflowError(f"{record['id']}: title, authors, and venue are required; correct the decision overrides")
    if not isinstance(year, int) or isinstance(year, bool) or not 1800 <= year <= 2100:
        raise WorkflowError(f"{record['id']}: a valid publication year is required")
    raw_doi = data.get("doi")
    doi = normalize_doi(raw_doi)
    if raw_doi and not doi:
        raise WorkflowError(f"{record['id']}: DOI is invalid")
    landing = canonical_arxiv_url(data.get("landing_page_url"))
    if landing:
        landing = validate_url(landing, "landing_page_url")
    links = []
    arxiv_id = arxiv_from_record(record)
    arxiv_doi_is_primary = decision["type"] == "preprint" and doi == f"10.48550/arxiv.{arxiv_id}"
    if landing and not arxiv_doi_is_primary and (not doi or normalize_doi(landing) != doi):
        label = "arXiv preprint" if decision["type"] == "preprint" and arxiv_from_record(record) else (
            "Preprint" if decision["type"] == "preprint" else "Publication")
        links.append({"label": label, "url": landing})
    for field, label in (("software_url", "Software"), ("dataset_url", "Dataset")):
        if overrides.get(field):
            links.append({"label": label, "url": validate_url(overrides[field], field)})
    extra_links = overrides.get("extra_links", [])
    if not isinstance(extra_links, list):
        raise WorkflowError(f"{record['id']}: extra_links must be an array")
    for link in extra_links:
        if not isinstance(link, dict) or not clean_text(link.get("label")):
            raise WorkflowError(f"{record['id']}: extra_links need label and HTTPS url")
        links.append({"label": clean_text(link["label"]), "url": validate_url(link.get("url"), "extra link")})
    image = overrides.get("image")
    if image is not None:
        if not isinstance(image, dict) or not isinstance(image.get("src"), str) or not image["src"].startswith("/assets/images/"):
            raise WorkflowError(f"{record['id']}: image must use a local /assets/images/ path")
        if not clean_text(image.get("alt")) or not all(isinstance(image.get(key), int) and not isinstance(image[key], bool) and image[key] > 0 for key in ("width", "height")):
            raise WorkflowError(f"{record['id']}: image needs alt text and positive width/height")
        image_path = (root / image["src"].lstrip("/")).resolve()
        if not image_path.is_relative_to((root / "assets/images").resolve()) or not image_path.is_file():
            raise WorkflowError(f"{record['id']}: image file does not exist in assets/images")
        image = {key: image[key] for key in ("src", "alt", "width", "height")}
        if overrides["image"].get("caption"):
            image["caption"] = clean_text(overrides["image"]["caption"])
    if not doi and not landing:
        raise WorkflowError(f"{record['id']}: provide a DOI or reviewed publication link")
    slug = hashlib.sha256(record["id"].encode()).hexdigest()[:12]
    return {
        "id": f"publication-{slug}", "title": title,
        "authors": [clean_text(author) for author in authors],
        "venue": venue, "year": year, "type": decision["type"],
        "doi": doi, "doi_url": f"https://doi.org/{quote(doi, safe='/')}" if doi else None,
        "links": links, "image": image,
    }


def build_publications(root: Path) -> list[dict]:
    records, decisions = load_records(root), load_decisions(root)
    validate_decision_targets(records, decisions)
    groups = load_work_groups(root, records)
    publications = []
    seen = set()
    for record in records:
        key, decision = find_decision(record, decisions)
        if key:
            seen.add(key)
    for group in groups:
        versions = [record for record in records if group_for_record([group], record)]
        approved = [(record, find_decision(record, decisions)[1]) for record in versions
                    if (find_decision(record, decisions)[1] or {}).get("status") == "approved"]
        if not approved:
            continue
        journals = [(record, decision) for record, decision in approved if decision.get("type") == "journal"]
        primary_record, primary_decision = sorted(journals or approved,
            key=lambda item: (-item[0].get("year", 0), item[0]["id"]))[0]
        publication = publication_from_record(primary_record, primary_decision, root)
        publication["id"] = group["site_id"]
        existing_links = {(link["label"], link["url"]) for link in publication["links"]}
        for record, decision in approved:
            if record is primary_record:
                continue
            for link in publication_from_record(record, decision, root)["links"]:
                if decision.get("type") == "preprint" and link["label"] in {"Preprint", "arXiv preprint"}:
                    continue
                if (link["label"], link["url"]) not in existing_links:
                    publication["links"].append(link)
                    existing_links.add((link["label"], link["url"]))
        # The journal DOI is the reader-facing paper link. Keep version history
        # in the review registry without adding a second preprint link.
        preprints = [] if publication["type"] == "journal" and publication["doi"] else [
            record for record in versions if (record.get("suggested_type") == "preprint" or
            (find_decision(record, decisions)[1] or {}).get("type") == "preprint") and
            (find_decision(record, decisions)[1] or {}).get("status") != "excluded"]
        # A repository's revisions share one manuscript link; prefer the newest DOI version.
        latest = {}
        for record in preprints:
            doi = normalize_doi(record.get("doi")) or ""
            chemrxiv = CHEMRXIV_RE.fullmatch(doi)
            repository = chemrxiv.group(1) if chemrxiv else arxiv_from_record(record) or record["id"]
            revision = int(chemrxiv.group(2)) if chemrxiv else max(record.get("arxiv_versions", []) or [0])
            previous = latest.get(repository)
            previous_doi = normalize_doi(previous.get("doi")) if previous else None
            previous_chem = CHEMRXIV_RE.fullmatch(previous_doi or "") if previous else None
            previous_revision = (int(previous_chem.group(2)) if previous_chem else
                                 max(previous.get("arxiv_versions", []) or [0])) if previous else -1
            if revision > previous_revision:
                latest[repository] = record
        for record in latest.values():
            arxiv_id = arxiv_from_record(record)
            doi = normalize_doi(record.get("doi"))
            if (record is primary_record and publication["type"] == "preprint" and
                    doi == f"10.48550/arxiv.{arxiv_id}"):
                continue
            url = (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else
                   record.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else None))
            if url:
                label = "arXiv preprint" if arxiv_id else "Preprint"
                link = (label, validate_url(url.replace("http://", "https://", 1), "preprint URL"))
                if link not in existing_links:
                    publication["links"].append({"label": link[0], "url": link[1]})
                    existing_links.add(link)
        publications.append(publication)
    orphaned = [key for key, value in decisions.items() if value.get("status") == "approved" and key not in seen]
    if orphaned:
        raise WorkflowError(f"Approved decision has no candidate or manual record: {', '.join(orphaned)}")
    publications.sort(key=lambda item: (-item["year"], item["title"].casefold()))
    write_json(root / OUTPUT, publications)
    return publications


def update_decision(root: Path, identifier: str, status: str, *, publication_type=None, reviewer=None, note=None,
                    identity_evidence=None) -> None:
    records = load_records(root)
    record = find_record(records, identifier)
    decisions = load_decisions(root)
    validate_decision_targets(records, decisions)
    key, existing = find_decision(record, decisions)
    key = key or record["id"]
    updated = copy.deepcopy(existing or {})
    updated["status"] = status
    if status == "approved":
        if publication_type not in ALLOWED_TYPES or not clean_text(reviewer) or not clean_text(note):
            raise WorkflowError("Approval requires --type, --reviewer, and --note")
        updated.update({"type": publication_type, "reviewer": reviewer, "note": note, "reviewed_on": date.today().isoformat()})
        if identity_evidence:
            updated["identity_evidence"] = identity_evidence
        publication_from_record(record, updated, root)
    elif note:
        updated["note"] = note
    decisions[key] = updated
    write_json(root / REVIEW_DIR / "decisions.json", {"decisions": decisions})


def add_manual(root: Path, raw: dict) -> dict:
    record = normalize_manual(raw)
    if find_match(load_records(root), record):
        raise WorkflowError("Manual record duplicates an existing publication; use decision overrides instead")
    path = root / REVIEW_DIR / "manual.json"
    manual = read_json(path, {"records": []})
    manual["records"].append(raw)
    write_json(path, manual)
    return record


def link_versions(root: Path, first_id: str, second_id: str, reviewer: str, note: str,
                  *, keep_work: str | None = None) -> dict:
    if not clean_text(reviewer) or not clean_text(note):
        raise WorkflowError("Linking versions needs reviewer and evidence note")
    records, decisions = load_records(root), load_decisions(root)
    validate_decision_targets(records, decisions)
    first, second = find_record(records, first_id), find_record(records, second_id)
    if first is second:
        raise WorkflowError("Those IDs already refer to the same version")
    groups = load_work_groups(root, records)
    first_group, second_group = group_for_record(groups, first), group_for_record(groups, second)
    evidence = {"from": first["id"], "to": second["id"], "method": "manual",
                "reviewer": reviewer, "note": note, "reviewed_on": date.today().isoformat()}
    if first_group is second_group:
        first_group.setdefault("matches", []).append(evidence)
        write_json(root / REVIEW_DIR / "works.json", {"works": sorted(groups, key=lambda item: item["id"])})
        return first_group
    if not keep_work and not group_approved_ids(first_group, records, decisions) and not group_approved_ids(second_group, records, decisions):
        keep_work = first_group["id"]
    group = join_groups(groups, first_group, second_group,
                        evidence,
                        records, decisions, keep_work=keep_work)
    write_json(root / REVIEW_DIR / "works.json", {"works": sorted(groups, key=lambda item: item["id"])})
    return group


def reject_match(root: Path, first_id: str, second_id: str, note: str) -> None:
    if not clean_text(note):
        raise WorkflowError("Rejecting a match needs a reason")
    records = load_records(root)
    first, second = find_record(records, first_id), find_record(records, second_id)
    if first is second:
        raise WorkflowError("Those IDs already refer to the same version")
    groups = load_work_groups(root, records)
    if group_for_record(groups, first) is group_for_record(groups, second):
        raise WorkflowError("Those versions are already linked; inspect works.json before rejecting")
    path = root / REVIEW_DIR / "rejected_matches.json"
    data = read_json(path, {"matches": []})
    pair = sorted([first["id"], second["id"]])
    if pair not in [item["version_ids"] for item in data["matches"]]:
        data["matches"].append({"version_ids": pair, "note": note, "reviewed_on": date.today().isoformat()})
    write_json(path, data)


def work_report(root: Path) -> dict:
    records, decisions = load_records(root), load_decisions(root)
    validate_decision_targets(records, decisions)
    groups = load_work_groups(root, records)
    counts = {"unique_works": len(groups), "journal_works": 0, "preprint_only_works": 0,
              "works_with_both_versions": 0, "other_only_works": 0, "approved_website_entries": 0}
    for group in groups:
        versions = [record for record in records if group_for_record([group], record)]
        types = {record.get("suggested_type") for record in versions}
        if "journal" in types:
            counts["journal_works"] += 1
        if "preprint" in types and "journal" not in types:
            counts["preprint_only_works"] += 1
        if "preprint" in types and "journal" in types:
            counts["works_with_both_versions"] += 1
        if "preprint" not in types and "journal" not in types:
            counts["other_only_works"] += 1
        if any((find_decision(record, decisions)[1] or {}).get("status") == "approved" for record in versions):
            counts["approved_website_entries"] += 1
    suggestions = read_json(root / REVIEW_DIR / "possible_matches.json", {"matches": []})
    counts["unresolved_possible_matches"] = len(suggestions.get("matches", []))
    counts["metadata_warning_records"] = sum(bool(record.get("metadata_warnings")) for record in records)
    counts["arxiv_identity_review_candidates"] = sum(
        record.get("identity_status") == "needs_review" and
        not clean_text((find_decision(record, decisions)[1] or {}).get("identity_evidence"))
        for record in records
    )
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover", help="retrieve candidates; never publish them")
    discover.add_argument("--contact-email", default=os.environ.get("PUBLICATIONS_CONTACT_EMAIL"))
    discover.add_argument("--no-crossref", action="store_true")
    discover.add_argument("--refresh-crossref", action="store_true")
    commands.add_parser("discover-arxiv", help="retrieve configured arXiv IDs and author searches without publishing")
    commands.add_parser("sync-works", help="migrate work IDs, group strong matches, and suggest uncertain matches")
    commands.add_parser("report", help="count unique works and unresolved version matches")
    verify = commands.add_parser("verify-doi", help="check one discovered DOI against Crossref")
    verify.add_argument("id")
    verify.add_argument("--contact-email", default=os.environ.get("PUBLICATIONS_CONTACT_EMAIL"))
    listing = commands.add_parser("list", help="show candidates, newest first, without network access")
    listing.add_argument("--all", action="store_true", help="include approved and excluded records")
    listing.add_argument("--status", choices=("pending", "approved", "excluded"))
    listing.add_argument("--year", type=int)
    listing.add_argument("--limit", type=int)
    approve = commands.add_parser("approve", help="approve one reviewed candidate")
    approve.add_argument("id")
    approve.add_argument("--type", choices=sorted(ALLOWED_TYPES), required=True)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--note", required=True)
    approve.add_argument("--identity-evidence", help="independent author identity check for arXiv preprints")
    exclude = commands.add_parser("exclude", help="exclude one candidate")
    exclude.add_argument("id")
    exclude.add_argument("--note", required=True)
    link = commands.add_parser("link-versions", help="confirm two candidate versions as one work")
    link.add_argument("first_id")
    link.add_argument("second_id")
    link.add_argument("--reviewer", required=True)
    link.add_argument("--note", required=True)
    link.add_argument("--keep-work", help="required if both work groups already have approvals")
    reject = commands.add_parser("reject-match", help="mark two similar records as distinct works")
    reject.add_argument("first_id")
    reject.add_argument("second_id")
    reject.add_argument("--note", required=True)
    manual = commands.add_parser("add", help="add a manual candidate; approval is separate")
    manual.add_argument("--id")
    manual.add_argument("--doi")
    manual.add_argument("--title", required=True)
    manual.add_argument("--author", action="append", required=True)
    manual.add_argument("--venue", required=True)
    manual.add_argument("--year", type=int, required=True)
    manual.add_argument("--url")
    commands.add_parser("build", help="write Jekyll data from approved records only")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "discover":
            api_key = os.environ.get("OPENALEX_API_KEY")
            records = discover_records(root, HttpClient(args.contact_email), api_key, args.contact_email,
                                       crossref=not args.no_crossref, refresh_crossref=args.refresh_crossref)
            groups, suggestions = sync_work_registry(root, records)
            print(f"Stored {len(records)} candidates in {len(groups)} works; {len(suggestions)} possible matches; public data unchanged")
        elif args.command == "discover-arxiv":
            records = discover_arxiv_records(root, HttpClient(None))
            groups, suggestions = sync_work_registry(root, records)
            print(f"Stored {len(records)} candidates in {len(groups)} works; {len(suggestions)} possible matches; public data unchanged")
        elif args.command == "sync-works":
            groups, suggestions = sync_work_registry(root)
            print(f"Grouped {len(groups)} works; {len(suggestions)} possible matches need review")
        elif args.command == "report":
            for label, count in work_report(root).items():
                print(f"{label}: {count}")
        elif args.command == "verify-doi":
            record = verify_candidate_doi(root, args.id, HttpClient(args.contact_email), args.contact_email)
            sync_work_registry(root)
            print(f"Crossref {record['crossref_status']} for {record['id']}; approvals and public data unchanged")
        elif args.command == "list":
            records, decisions = load_records(root), load_decisions(root)
            rows = []
            for record in records:
                _, decision = find_decision(record, decisions)
                status = decision.get("status", "pending") if decision else "pending"
                if args.year is not None and record.get("year") != args.year:
                    continue
                if args.status and status != args.status:
                    continue
                if not args.status and not args.all and status != "pending":
                    continue
                rows.append((record, status))
            rows.sort(key=lambda item: (-item[0].get("year") if isinstance(item[0].get("year"), int) else 0,
                                        clean_text(item[0].get("title")).casefold(), item[0]["id"]))
            if args.limit is not None and args.limit < 1:
                raise WorkflowError("--limit must be a positive number")
            displayed = rows[:args.limit] if args.limit else rows
            for record, status in displayed:
                warning = f" [review: {'; '.join(record.get('metadata_warnings', []))}]" if record.get("metadata_warnings") else ""
                print(f"{status:8} {record['id']:34} {record.get('year') or '?'} {record.get('title') or '[title missing]'}{warning}")
            print(f"Showing {len(displayed)} of {len(rows)} matching records")
        elif args.command == "approve":
            update_decision(root, args.id, "approved", publication_type=args.type, reviewer=args.reviewer,
                            note=args.note, identity_evidence=args.identity_evidence)
            print(f"Approved {args.id}; run build to update the local site")
        elif args.command == "exclude":
            update_decision(root, args.id, "excluded", note=args.note)
            print(f"Excluded {args.id}")
        elif args.command == "link-versions":
            group = link_versions(root, args.first_id, args.second_id, args.reviewer, args.note, keep_work=args.keep_work)
            sync_work_registry(root)
            print(f"Linked versions in {group['id']}; approvals and public data unchanged")
        elif args.command == "reject-match":
            reject_match(root, args.first_id, args.second_id, args.note)
            sync_work_registry(root)
            print("Recorded distinct works; public data unchanged")
        elif args.command == "add":
            record = add_manual(root, {"id": args.id, "doi": args.doi, "title": args.title, "authors": args.author,
                                       "venue": args.venue, "year": args.year, "landing_page_url": args.url})
            print(f"Added pending manual candidate {record['id']}; review and approve separately")
        elif args.command == "build":
            publications = build_publications(root)
            print(f"Wrote {len(publications)} approved publications to {OUTPUT}")
    except WorkflowError as error:
        print(f"Publication workflow error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
