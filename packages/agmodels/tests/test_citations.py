"""Every model's citations: a paper with a DOI carries it (bare, in `doi`), and the DOI is that paper's."""

import re

import pytest
import requests

from agmodels.registry import all_models

CITATIONS = sorted({c for m in all_models().values() for c in m.SPEC.citations if c.doi}, key=lambda c: c.doi)


def test_dois_are_bare_and_urls_are_not_dois():
    for model in all_models().values():
        for citation in model.SPEC.citations:
            assert not citation.doi or re.fullmatch(r"10\.\d{4,}/\S+", citation.doi), citation
            assert "doi.org" not in citation.url, f"{model.SPEC.id}: put the DOI in `doi`, not `url`"


def test_doi_url():
    assert CITATIONS[0].doi_url == f"https://doi.org/{CITATIONS[0].doi}"


@pytest.mark.network
@pytest.mark.enable_socket
@pytest.mark.parametrize("citation", CITATIONS, ids=lambda c: c.doi)
def test_doi_is_the_cited_paper(citation):
    # Crossref's year and first page should be in the citation's text (a wrong DOI was once a 1961 notice)
    work = requests.get(f"https://api.crossref.org/works/{citation.doi}", timeout=30).json()["message"]
    assert f"({work['issued']['date-parts'][0][0]})" in citation.text
    if first_page := (work.get("page") or "").split("-")[0]:
        assert first_page in citation.text
