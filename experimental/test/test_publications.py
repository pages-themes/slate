"""Offline tests for the publication discovery and approval workflow."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "script"))
import publications as workflow  # noqa: E402


def work(identifier="W1", doi="10.1234/example", *, title="Example study", year=2025, pmid=None):
    return {
        "id": f"https://openalex.org/{identifier}",
        "ids": {"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None},
        "doi": f"https://doi.org/{doi}" if doi else None,
        "title": title,
        "publication_year": year,
        "authorships": [{"author": {"display_name": "Researcher One"}}],
        "primary_location": {"source": {"display_name": "Example Journal", "type": "journal"}},
        "type": "article",
    }


def version_record(doi, title, year, kind, *, authors=None, relations=None):
    return {
        "id": f"doi:{doi}", "identifiers": [f"doi:{doi}"], "doi": doi,
        "title": title, "authors": authors or ["Researcher One", "Researcher Two"],
        "venue": "Example Journal" if kind == "journal" else "Preprint repository",
        "year": year, "suggested_type": kind,
        "landing_page_url": f"https://doi.org/{doi}",
        "version_relations": relations or [], "metadata_warnings": [],
    }


def arxiv_feed(*entries):
    body = "".join(entries)
    return ("<feed xmlns='http://www.w3.org/2005/Atom' "
            "xmlns:arxiv='http://arxiv.org/schemas/atom' "
            "xmlns:opensearch='http://a9.com/-/spec/opensearch/1.1/'>"
            f"<opensearch:totalResults>{len(entries)}</opensearch:totalResults>{body}</feed>")


def arxiv_entry(identifier, title, *, doi=None, author="Jason Hattrick-Simpers"):
    extra = f"<arxiv:doi>{doi}</arxiv:doi>" if doi else ""
    return (f"<entry><id>http://arxiv.org/abs/{identifier}</id><title>{title}</title>"
            "<published>2026-04-01T00:00:00Z</published><updated>2026-11-01T00:00:00Z</updated>"
            f"<author><name>{author}</name></author>{extra}</entry>")


class FakeOpenAlex:
    def __init__(self, pages, *, orcid="https://orcid.org/0000-0002-0000-0000"):
        self.pages = pages
        self.orcid = orcid
        self.urls = []

    def get_json(self, url, **_kwargs):
        self.urls.append(url)
        parsed = urlparse(url)
        if parsed.path.startswith("/authors/"):
            return {"id": "https://openalex.org/A123", "orcid": self.orcid}
        params = parse_qs(parsed.query)
        key = params.get("cursor", params.get("page", ["1"]))[0]
        return self.pages[key]


class PublicationWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "_publication_review").mkdir()
        (self.root / "_data").mkdir()

    def write(self, name, value):
        path = self.root / "_publication_review" / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_normalization_and_deduplication_use_doi_and_other_ids(self):
        first = workflow.normalize_openalex_work(work("W1", "10.1234/Example", pmid=42), "PI")
        second = workflow.normalize_openalex_work(work("W2", "10.1234/example"), "Former member")
        third = workflow.normalize_openalex_work(work("W3", None, pmid=42), "Current member")
        merged = workflow.deduplicate([first, second, third])
        self.assertEqual(1, len(merged))
        self.assertEqual("doi:10.1234/example", merged[0]["id"])
        self.assertIn("openalex:W3", merged[0]["identifiers"])
        self.assertIn("pmid:42", merged[0]["identifiers"])
        self.assertEqual(["PI", "Former member", "Current member"], merged[0]["discovered_from"])
        self.assertEqual("10.1234/example", workflow.normalize_doi("https://doi.org/10.1234/EXAMPLE"))

    def test_openalex_reclassification_keeps_one_doi_free_candidate(self):
        old = workflow.normalize_openalex_work(work("W42", None), "PI")
        current_work = work("W42", None)
        current_work["type"] = "report"
        current = workflow.normalize_openalex_work(current_work, "PI")
        self.assertEqual("journal", old["suggested_type"])
        self.assertEqual("other", current["suggested_type"])
        merged = workflow.deduplicate([old, current])
        self.assertEqual(1, len(merged))
        self.assertEqual("openalex:W42", merged[0]["id"])
        self.assertEqual("other", merged[0]["suggested_type"])
        self.assertNotIn("arxiv_versions", merged[0])
        self.assertNotIn("version_relations", merged[0])

    def test_crossref_enriches_missing_fields_and_flags_disagreement(self):
        record = workflow.normalize_openalex_work(work(title="", year=None), "PI")
        record["authors"] = []
        record["venue"] = ""
        message = {
            "DOI": "10.1234/example", "title": ["Verified <i>study</i>"],
            "author": [{"given": "First", "family": "Author"}],
            "container-title": ["Verified Journal"],
            "published": {"date-parts": [[2024, 8, 1]]},
            "type": "journal-article",
            "relation": {"has-preprint": [{"id-type": "doi", "id": "10.5555/preprint"}]},
        }
        enriched = workflow.enrich_crossref(record, message, "2026-11-14")
        self.assertEqual("Verified study", enriched["title"])
        self.assertEqual(["First Author"], enriched["authors"])
        self.assertEqual("Verified Journal", enriched["venue"])
        self.assertEqual(2024, enriched["year"])
        self.assertEqual("verified", enriched["crossref_status"])
        self.assertEqual([], enriched["metadata_warnings"])
        self.assertEqual([{"type": "has-preprint", "doi": "10.5555/preprint"}], enriched["version_relations"])

        mismatch = workflow.enrich_crossref(workflow.normalize_openalex_work(work(), "PI"),
                                            {"DOI": "10.1234/example", "title": ["Different title"],
                                             "published": {"date-parts": [[2023]]}}, "2026-11-14")
        self.assertIn("Crossref title differs from OpenAlex title", mismatch["metadata_warnings"])
        self.assertIn("Crossref publication year differs from OpenAlex year", mismatch["metadata_warnings"])

    def test_openalex_basic_paging_and_orcid_verification(self):
        client = FakeOpenAlex({
            "1": {"meta": {"count": 3}, "results": [work("W1"), work("W2")]},
            "2": {"meta": {"count": 3}, "results": [work("W3")]},
        })
        researcher = {"openalex_author_id": "A123", "orcid": "0000-0002-0000-0000"}
        self.assertEqual(3, len(workflow.fetch_author_works(client, researcher, None, per_page=2)))
        self.assertIn("page=2", client.urls[-1])

        wrong = FakeOpenAlex({"1": {"meta": {"count": 0}, "results": []}}, orcid=None)
        with self.assertRaisesRegex(workflow.WorkflowError, "ORCID does not match"):
            workflow.fetch_author_works(wrong, researcher, None, per_page=2)

    def test_openalex_cursor_paging_and_basic_limit(self):
        client = FakeOpenAlex({
            "*": {"meta": {"next_cursor": "next"}, "results": [work("W1"), work("W2")]},
            "next": {"meta": {"next_cursor": None}, "results": [work("W3")]},
        })
        self.assertEqual(3, len(workflow.fetch_author_works(client, {"openalex_author_id": "A123"}, "secret", per_page=2)))
        self.assertIn("cursor=next", client.urls[-1])
        limited = FakeOpenAlex({"1": {"meta": {"count": 10_001}, "results": [work("W1")]}})
        with self.assertRaisesRegex(workflow.WorkflowError, "OPENALEX_API_KEY"):
            workflow.fetch_author_works(limited, {"openalex_author_id": "A123"}, None, per_page=2)

    def test_http_client_retries_rate_limit_without_leaking_query(self):
        calls, pauses = [], []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 429, "rate limited", {"Retry-After": "2"}, None)
            return BytesIO(b'{"results": []}')

        client = workflow.HttpClient(None, opener=opener, sleeper=pauses.append, clock=lambda: 10)
        self.assertEqual({"results": []}, client.get_json("https://api.openalex.org/works?api_key=secret"))
        self.assertEqual(2, len(calls))
        self.assertIn(2, pauses)

    def test_discovery_failure_does_not_replace_candidate_cache(self):
        config = {"researchers": [{"name": "Verified person", "relationship": "pi", "openalex_author_id": "A123",
                                   "verified": True, "verified_by": "Reviewer", "verification_url": "https://example.org/profile"}]}
        self.write("researchers.json", config)
        cache = self.write("candidates.json", {"records": [{"id": "manual:existing", "identifiers": ["manual:existing"]}]})
        before = cache.read_bytes()

        class FailingClient:
            def get_json(self, url, **_kwargs):
                if "/authors/" in url:
                    return {"id": "https://openalex.org/A123"}
                raise workflow.WorkflowError("OpenAlex unavailable")

        with self.assertRaisesRegex(workflow.WorkflowError, "unavailable"):
            workflow.discover_records(self.root, FailingClient(), None, None, crossref=False)
        self.assertEqual(before, cache.read_bytes())

    def test_only_approved_records_render_and_overrides_survive_status_updates(self):
        first = workflow.normalize_openalex_work(work("W1", "10.1234/example"), "PI")
        second = workflow.normalize_openalex_work(work("W2", "10.1234/unrelated", year=2024), "Former member")
        self.write("candidates.json", {"records": [first, second]})
        self.write("decisions.json", {"decisions": {
            first["id"]: {"status": "pending", "overrides": {"title": "Editorially corrected title",
                         "software_url": "https://example.org/code", "dataset_url": "https://example.org/data"}}
        }})
        workflow.update_decision(self.root, first["id"], "approved", publication_type="journal",
                                 reviewer="Reviewer", note="Paper checked against lab record")
        workflow.update_decision(self.root, second["id"], "excluded", note="Unrelated work")
        approved = workflow.build_publications(self.root)
        self.assertEqual(1, len(approved))
        self.assertEqual("Editorially corrected title", approved[0]["title"])
        self.assertEqual(["Software", "Dataset"], [link["label"] for link in approved[0]["links"]])
        self.assertEqual("journal", approved[0]["type"])
        self.assertEqual(1, len(json.loads((self.root / "_data/publications.json").read_text())))
        decisions = workflow.load_decisions(self.root)
        self.assertEqual("Editorially corrected title", decisions[first["id"]]["overrides"]["title"])

    def test_manual_addition_needs_separate_approval(self):
        raw = {"id": "manual:missing-paper", "title": "Reviewed title", "authors": ["A. Researcher"],
               "venue": "Reviewed venue", "year": 2022, "landing_page_url": "https://example.org/paper"}
        manual = workflow.add_manual(self.root, raw)
        self.assertEqual([], workflow.build_publications(self.root))
        workflow.update_decision(self.root, manual["id"], "approved", publication_type="other",
                                 reviewer="Reviewer", note="Verified lab publication")
        self.assertEqual("Reviewed title", workflow.build_publications(self.root)[0]["title"])

    def test_orphaned_approval_and_incomplete_metadata_cannot_replace_public_data(self):
        output = self.root / "_data/publications.json"
        output.write_text('[{"old": true}]\n', encoding="utf-8")
        self.write("decisions.json", {"decisions": {"doi:10.1234/missing": {"status": "approved", "type": "journal",
                                                                 "reviewer": "Reviewer", "note": "Reviewed"}}})
        with self.assertRaisesRegex(workflow.WorkflowError, "no candidate"):
            workflow.build_publications(self.root)
        self.assertEqual('[{"old": true}]\n', output.read_text())

        sparse = workflow.normalize_openalex_work(work(title="", year=None), "PI")
        self.write("candidates.json", {"records": [sparse]})
        self.write("decisions.json", {"decisions": {}})
        with self.assertRaisesRegex(workflow.WorkflowError, "title, authors, and venue"):
            workflow.update_decision(self.root, sparse["id"], "approved", publication_type="journal",
                                     reviewer="Reviewer", note="Reviewed")
        self.assertEqual({}, workflow.load_decisions(self.root))

    def test_software_link_cannot_replace_publication_link(self):
        manual = workflow.normalize_manual({"id": "manual:no-paper-link", "title": "Reviewed title",
                                            "authors": ["A. Researcher"], "venue": "Reviewed venue", "year": 2022})
        with self.assertRaisesRegex(workflow.WorkflowError, "DOI or reviewed publication link"):
            workflow.publication_from_record(manual, {"status": "approved", "type": "other",
                                              "reviewer": "Reviewer", "note": "Checked",
                                              "overrides": {"software_url": "https://example.org/code"}}, self.root)

    def test_researcher_configuration_rejects_unverified_ids(self):
        with self.assertRaisesRegex(workflow.WorkflowError, "No verified researchers"):
            workflow.validate_researchers({"researchers": []})
        with self.assertRaisesRegex(workflow.WorkflowError, "record who verified"):
            workflow.validate_researchers({"researchers": [{"name": "Unknown", "openalex_author_id": "A123"}]})

    def test_malformed_source_fields_and_review_files_fail_safely(self):
        malformed = work()
        malformed["authorships"] = [{"author": "wrong shape"}]
        malformed["primary_location"] = "wrong shape"
        record = workflow.normalize_openalex_work(malformed, "PI")
        self.assertEqual([], record["authors"])
        self.assertEqual("", record["venue"])
        with self.assertRaisesRegex(workflow.WorkflowError, "Manual DOI is invalid"):
            workflow.normalize_manual({"id": "manual:test", "doi": "invalid"})
        self.write("decisions.json", {"decisions": {"doi:10.1234/example": "invalid"}})
        with self.assertRaisesRegex(workflow.WorkflowError, "decision must be an object"):
            workflow.load_decisions(self.root)
        self.write("candidates.json", ["wrong shape"])
        with self.assertRaisesRegex(workflow.WorkflowError, "records array"):
            workflow.load_records(self.root)

    def test_discovery_reuses_crossref_result_for_same_work_from_two_members(self):
        self.write("researchers.json", {"researchers": [
            {"name": name, "relationship": relationship, "openalex_author_id": "A123",
             "verified": True, "verified_by": "Reviewer", "verification_url": "https://example.org/profile"}
            for name, relationship in (("PI", "pi"), ("Member", "current"))
        ]})

        class Client:
            def __init__(self):
                self.crossref_calls = 0

            def get_json(self, url, **_kwargs):
                if "/authors/" in url:
                    return {"id": "https://openalex.org/A123"}
                if "/works?" in url:
                    return {"meta": {"count": 1}, "results": [work()]}
                self.crossref_calls += 1
                return {"message": {"DOI": "10.1234/example", "title": ["Example study"]}}

        client = Client()
        records = workflow.discover_records(self.root, client, None, "reviewer@example.org")
        self.assertEqual(1, client.crossref_calls)
        self.assertEqual(1, len(records))
        self.assertEqual(["PI", "Member"], records[0]["discovered_from"])

    def test_discovery_keeps_fresh_openalex_fields_with_cached_crossref_check(self):
        self.write("researchers.json", {"researchers": [{
            "name": "PI", "relationship": "pi", "openalex_author_id": "A123",
            "verified": True, "verified_by": "Reviewer", "verification_url": "https://example.org/profile"
        }]})
        cached = workflow.normalize_openalex_work(work(title="Old title"), "PI")
        cached.update(crossref_status="verified", crossref_checked_on=workflow.date.today().isoformat())
        self.write("candidates.json", {"records": [cached]})

        class Client:
            def get_json(self, url, **_kwargs):
                if "/authors/" in url:
                    return {"id": "https://openalex.org/A123"}
                if "/works?" in url:
                    return {"meta": {"count": 1}, "results": [work(title="Corrected title")]}
                raise AssertionError("Recent Crossref result should be reused")

        records = workflow.discover_records(self.root, Client(), None, "reviewer@example.org")
        self.assertEqual("Corrected title", records[0]["title"])
        self.assertEqual("verified", records[0]["crossref_status"])

    def test_verify_one_doi_preserves_approval_and_public_data(self):
        candidate = workflow.normalize_openalex_work(work(), "PI")
        self.write("candidates.json", {"records": [candidate]})
        self.write("decisions.json", {"decisions": {candidate["id"]: {"status": "pending"}}})
        output = self.root / "_data/publications.json"
        output.write_text("[]\n", encoding="utf-8")

        class CrossrefClient:
            def get_json(self, url, **kwargs):
                self_url = url
                assert "10.1234/example" in self_url
                assert kwargs["allow_404"]
                return {"message": {"DOI": "10.1234/example", "title": ["Example study"],
                                    "type": "journal-article"}}

        record = workflow.verify_candidate_doi(self.root, candidate["id"], CrossrefClient(), None)
        self.assertEqual("verified", record["crossref_status"])
        self.assertEqual("pending", workflow.load_decisions(self.root)[candidate["id"]]["status"])
        self.assertEqual("[]\n", output.read_text())

    def test_review_list_filters_and_orders_pending_candidates(self):
        records = [
            workflow.normalize_openalex_work(work("W1", "10.1234/old", title="Old", year=2024), "PI"),
            workflow.normalize_openalex_work(work("W2", "10.1234/new", title="New", year=2025), "PI"),
            workflow.normalize_openalex_work(work("W3", "10.1234/approved", title="Approved", year=2025), "PI"),
        ]
        self.write("candidates.json", {"records": records})
        self.write("decisions.json", {"decisions": {records[2]["id"]: {"status": "approved"}}})
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, workflow.main(["--root", str(self.root), "list", "--year", "2025", "--limit", "1"]))
        self.assertIn("New", output.getvalue())
        self.assertNotIn("Approved", output.getvalue())
        self.assertIn("Showing 1 of 1 matching records", output.getvalue())

    def test_arxiv_known_ids_merge_with_existing_autorec_and_eis_candidates(self):
        self.write("researchers.json", {"researchers": [{
            "name": "Jason Hattrick-Simpers", "relationship": "pi", "openalex_author_id": "A123",
            "verified": True, "verified_by": "Reviewer", "verification_url": "https://example.org/profile"
        }]})
        ids = ["2604.27266", "2607.19307"]
        self.write("arxiv_sources.json", {"known_ids": [
            {"arxiv_id": identifier, "researcher": "Jason Hattrick-Simpers",
             "verified_by": "Reviewer", "verification_url": f"https://arxiv.org/abs/{identifier}"}
            for identifier in ids], "author_searches": []})
        existing = [version_record(f"10.48550/arxiv.{identifier}", title, 2026, "preprint") for identifier, title in (
            (ids[0], "AutoREC: A reinforcement learning platform for equivalent circuit model generation"),
            (ids[1], "Accelerating Electrochemical Impedance Spectroscopy Measurements by Reducing Reliance on Noisy Low-Frequency Data"))]
        self.write("candidates.json", {"records": existing})
        self.write("decisions.json", {"decisions": {existing[0]["id"]: {"status": "pending", "note": "Keep for review"}}})

        class Client:
            def get_text(self, url):
                assert "id_list=2604.27266%2C2607.19307" in url
                return arxiv_feed(arxiv_entry("2604.27266v4", existing[0]["title"]),
                                  arxiv_entry("2607.19307v1", existing[1]["title"]))

        records = workflow.discover_arxiv_records(self.root, Client())
        self.assertEqual(2, len(records))
        self.assertEqual({"pending"}, {item["status"] for item in workflow.load_decisions(self.root).values()})
        self.assertEqual([4], next(item for item in records if item["arxiv_id"] == ids[0])["arxiv_versions"])
        self.assertEqual("https://arxiv.org/abs/2607.19307",
                         next(item for item in records if item["arxiv_id"] == ids[1])["landing_page_url"])
        self.assertTrue(all(item["crossref_status"] == "not_required" for item in records))
        self.assertEqual([], workflow.build_publications(self.root))
        self.assertEqual(("2604.27266", 4), workflow.normalize_arxiv_id("https://arxiv.org/abs/2604.27266v4"))
        first = ET.fromstring(arxiv_feed(arxiv_entry("2604.27266v1", "AutoREC example"))).find("atom:entry", workflow.ATOM_NS)
        revised = ET.fromstring(arxiv_feed(arxiv_entry("2604.27266v4", "AutoREC example"))).find("atom:entry", workflow.ATOM_NS)
        revisions = workflow.deduplicate([workflow.normalize_arxiv_entry(first, "known ID"),
                                          workflow.normalize_arxiv_entry(revised, "known ID")])
        self.assertEqual(1, len(revisions))
        self.assertEqual([1, 4], revisions[0]["arxiv_versions"])

    def test_arxiv_author_search_keeps_identity_pending_and_needs_evidence_to_approve(self):
        self.write("researchers.json", {"researchers": [{
            "name": "Jason Hattrick-Simpers", "relationship": "pi", "openalex_author_id": "A123",
            "verified": True, "verified_by": "Reviewer", "verification_url": "https://example.org/profile"
        }]})
        self.write("arxiv_sources.json", {"known_ids": [], "author_searches": [{
            "name": "Jason Hattrick-Simpers", "researcher": "Jason Hattrick-Simpers",
            "verified_by": "Reviewer", "verification_url": "https://example.org/profile", "max_results": 2
        }]})

        class Client:
            def get_text(self, url):
                assert "search_query=" in url
                return arxiv_feed(arxiv_entry("2604.27266v1", "AutoREC example"),
                                  arxiv_entry("2605.00001v1", "Namesake example", author="Other Person"))

        records = workflow.discover_arxiv_records(self.root, Client())
        self.assertEqual(1, len(records))
        self.assertEqual("needs_review", records[0]["identity_status"])
        self.assertEqual(1, workflow.work_report(self.root)["arxiv_identity_review_candidates"])
        with self.assertRaisesRegex(workflow.WorkflowError, "identity evidence"):
            workflow.update_decision(self.root, records[0]["id"], "approved", publication_type="preprint",
                                     reviewer="Reviewer", note="Lab work")
        workflow.update_decision(self.root, records[0]["id"], "approved", publication_type="preprint",
                                 reviewer="Reviewer", note="Lab work", identity_evidence="Verified author profile")
        output = workflow.build_publications(self.root)
        self.assertEqual("preprint", output[0]["type"])
        self.assertEqual([], output[0]["links"])
        self.assertEqual("https://doi.org/10.48550/arxiv.2604.27266", output[0]["doi_url"])
        self.assertEqual(0, workflow.work_report(self.root)["arxiv_identity_review_candidates"])
        entry = ET.fromstring(arxiv_feed(arxiv_entry("2604.27266v2", "AutoREC example", doi="10.1234/final"))).find("atom:entry", workflow.ATOM_NS)
        metadata = workflow.normalize_arxiv_entry(entry, "known ID")
        self.assertEqual("10.48550/arxiv.2604.27266", metadata["doi"])
        self.assertEqual([{"type": "is-preprint-of", "doi": "10.1234/final"}], metadata["version_relations"])

    def test_cantor_preprint_to_journal_keeps_work_anchor_and_review_data(self):
        title = "High-throughput validation of phase formability and simulation accuracy of Cantor alloys"
        preprint = version_record("10.2139/ssrn.5744656", title, 2025, "preprint")
        journal = version_record("10.1016/j.apmt.2026.103178", title, 2026, "journal")
        self.write("candidates.json", {"records": [preprint, journal]})
        self.write("decisions.json", {"decisions": {preprint["id"]: {
            "status": "approved", "type": "preprint", "reviewer": "Reviewer", "note": "Verified preprint",
            "overrides": {"software_url": "https://example.org/code"}
        }, journal["id"]: {"status": "pending", "note": "Await journal check"}}})
        workflow.sync_work_registry(self.root)
        original = workflow.build_publications(self.root)[0]
        self.assertEqual("preprint", original["type"])
        workflow.link_versions(self.root, preprint["id"], journal["id"], "Reviewer", "Publisher and preprint checked")
        self.assertEqual(original["id"], workflow.build_publications(self.root)[0]["id"])
        workflow.update_decision(self.root, journal["id"], "approved", publication_type="journal",
                                 reviewer="Reviewer", note="Verified journal version")
        built = workflow.build_publications(self.root)
        self.assertEqual(1, len(built))
        self.assertEqual(original["id"], built[0]["id"])
        self.assertEqual(("journal", 2026, journal["doi"]), (built[0]["type"], built[0]["year"], built[0]["doi"]))
        self.assertNotIn("Preprint", [link["label"] for link in built[0]["links"]])
        self.assertIn("Software", [link["label"] for link in built[0]["links"]])
        self.assertEqual("Verified preprint", workflow.load_decisions(self.root)[preprint["id"]]["note"])

    def test_chemrxiv_revisions_group_but_journal_needs_manual_link(self):
        title = "Roadmap on Data-Centric Materials Science"
        versions = [version_record(f"10.26434/chemrxiv-2024-m9sk0-v{version}", title, 2024, "preprint")
                    for version in (2, 3, 4)]
        versions[-1]["version_relations"] = [{"type": "has-version", "doi": versions[0]["doi"]}]
        journal = version_record("10.1088/1361-651x/ad4d0d", title, 2024, "journal")
        self.write("candidates.json", {"records": [*versions, journal]})
        groups, suggestions = workflow.sync_work_registry(self.root)
        self.assertEqual(2, len(groups))
        self.assertEqual(1, len(suggestions))
        workflow.link_versions(self.root, versions[-1]["id"], journal["id"], "Reviewer", "ChemRxiv manuscript names journal")
        workflow.update_decision(self.root, journal["id"], "approved", publication_type="journal",
                                 reviewer="Reviewer", note="Verified journal DOI")
        built = workflow.build_publications(self.root)
        self.assertEqual(1, len(built))
        self.assertEqual(journal["doi"], built[0]["doi"])
        self.assertEqual([],
                         [link["url"] for link in built[0]["links"] if link["label"] == "Preprint"])

    def test_title_similarity_only_suggests_and_rejection_preserves_distinct_works(self):
        first = version_record("10.1234/one", "Electrochemical impedance spectroscopy for alloys", 2025, "preprint")
        second = version_record("10.1234/two", "Electrochemical impedance spectroscopy for alloy", 2026, "journal")
        self.write("candidates.json", {"records": [first, second]})
        groups, suggestions = workflow.sync_work_registry(self.root)
        self.assertEqual(2, len(groups))
        self.assertEqual(1, len(suggestions))
        workflow.reject_match(self.root, first["id"], second["id"], "Different experiments and results")
        groups, suggestions = workflow.sync_work_registry(self.root)
        self.assertEqual(2, len(groups))
        self.assertEqual([], suggestions)
        self.assertEqual("Different experiments and results",
                         workflow.read_json(self.root / "_publication_review/rejected_matches.json", {})["matches"][0]["note"])

    def test_explicit_relationship_groups_versions_without_promoting_pending_journal(self):
        preprint = version_record("10.48550/arxiv.2604.27266", "Versioned study", 2025, "preprint",
                                  relations=[{"type": "is-preprint-of", "doi": "10.1234/journal"}])
        preprint["arxiv_id"] = "2604.27266"
        journal = version_record("10.1234/journal", "Versioned study", 2026, "journal")
        self.write("candidates.json", {"records": [preprint, journal]})
        self.write("decisions.json", {"decisions": {preprint["id"]: {
            "status": "approved", "type": "preprint", "reviewer": "Reviewer", "note": "Lab preprint checked",
            "identity_evidence": "Checked institutional author profile", "overrides": {
                "extra_links": [{"label": "Code", "url": "https://example.org/code"}]
            }
        }, journal["id"]: {"status": "pending", "note": "Needs journal verification"}}})
        groups, suggestions = workflow.sync_work_registry(self.root)
        self.assertEqual((1, []), (len(groups), suggestions))
        before = workflow.build_publications(self.root)[0]
        self.assertEqual(("preprint", 2025, preprint["doi"]), (before["type"], before["year"], before["doi"]))
        self.assertEqual(["Code"], [link["label"] for link in before["links"]])
        workflow.update_decision(self.root, journal["id"], "approved", publication_type="journal",
                                 reviewer="Reviewer", note="Journal DOI checked")
        after = workflow.build_publications(self.root)[0]
        self.assertEqual(before["id"], after["id"])
        self.assertEqual(("journal", 2026, journal["doi"]), (after["type"], after["year"], after["doi"]))
        self.assertEqual({"Code"}, {link["label"] for link in after["links"]})

    def test_shared_openalex_identity_does_not_merge_versions_or_reassign_a_decision(self):
        preprint = version_record("10.48550/arxiv.2604.27266", "Same work", 2025, "preprint")
        preprint["identifiers"].append("openalex:W1")
        journal = version_record("10.1234/journal", "Same work", 2026, "journal")
        journal["identifiers"].append("openalex:W1")
        self.assertEqual(2, len(workflow.deduplicate([preprint, journal])))
        self.write("candidates.json", {"records": [preprint, journal]})
        self.write("decisions.json", {"decisions": {"openalex:W1": {"status": "approved", "type": "preprint",
                                                                   "reviewer": "Reviewer", "note": "Reviewed"}}})
        with self.assertRaisesRegex(workflow.WorkflowError, "matches multiple versions"):
            workflow.sync_work_registry(self.root)

    def test_pending_preprint_work_id_survives_later_journal_discovery(self):
        preprint = version_record("10.48550/arxiv.2607.19307", "A reviewed topic", 2026, "preprint")
        self.write("candidates.json", {"records": [preprint]})
        original_groups, _ = workflow.sync_work_registry(self.root)
        original = original_groups[0]["id"]
        preprint["version_relations"] = [{"type": "is-preprint-of", "doi": "10.1234/final"}]
        journal = version_record("10.1234/final", "A reviewed topic", 2027, "journal")
        self.write("candidates.json", {"records": [preprint, journal]})
        groups, _ = workflow.sync_work_registry(self.root)
        self.assertEqual(1, len(groups))
        self.assertEqual(original, groups[0]["id"])


if __name__ == "__main__":
    unittest.main()
