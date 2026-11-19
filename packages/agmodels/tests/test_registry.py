"""The registry and model pages: lookups by id, the page beside each module, and what a bad page says."""

import pytest

from agmodels import registry
from agmodels.pages import Page, read_page, source_problems
from agmodels.registry import all_models, model, page_path


def test_an_unknown_model_names_the_id():
    with pytest.raises(ValueError, match="unknown model 'no-such-model'"):
        model("no-such-model")
    with pytest.raises(ValueError, match="unknown model"):
        page_path("no-such-model")


def test_every_model_has_a_page_whose_front_matter_id_is_its_id():
    for model_id in all_models():
        path = page_path(model_id)
        assert path.suffix == ".md" and path.exists(), model_id
        assert read_page(path, page_id=model_id).body, model_id


def test_two_models_with_one_id_are_refused(monkeypatch):
    class Twin:
        SPEC = model("tar-spot").SPEC
        __file__ = "twin.py"

    monkeypatch.setattr(
        registry, "_modules", lambda package: iter([Twin, Twin]) if package is registry.models else iter(())
    )
    registry._found.cache_clear()
    try:
        with pytest.raises(ValueError, match="two models have the id 'tar-spot'"):
            registry._found()
    finally:
        monkeypatch.undo()
        registry._found.cache_clear()


def test_a_page_needs_front_matter_with_its_own_id(tmp_path):
    bare = tmp_path / "bare.md"
    bare.write_text("Just prose.\n")
    with pytest.raises(ValueError, match="no front matter"):
        read_page(bare)
    wrong = tmp_path / "wrong.md"
    wrong.write_text("---\nid: other\n---\nBody\n")
    with pytest.raises(ValueError, match="isn't 'wrong'"):
        read_page(wrong)
    right = tmp_path / "right.md"
    right.write_text("---\nid: right\nsummary: S\n---\n\nBody text\n")
    page = read_page(right)
    assert page.id == "right" and page.front == {"id": "right", "summary": "S"} and page.body == "Body text"


def _page(sources, body):
    return Page(id="x", front={"sources": sources}, body=body)


def test_a_pages_citations_name_its_keyed_sources():
    keyed = [
        {"key": "smith-2020", "text": "Smith 2020."},
        {"key": "guide", "text": "A guide.", "url": "https://g.example"},
    ]
    assert source_problems(_page(keyed, "Said.[^smith-2020] See the [guide](https://g.example).")) == []
    assert source_problems(_page(keyed, "Said.[^smith-2020][^jones]")) == [
        "cites [^jones], which isn't a listed source",
        "lists 'guide' but never cites it",
    ]
    assert source_problems(_page(["Smith 2020"], "Plain sources, no markers.")) == []
    assert source_problems(_page(["Smith 2020"], "Said.[^smith-2020]")) == [
        "cites ['smith-2020'] but its sources aren't keyed"
    ]
    assert source_problems(_page([{"key": "Bad Key", "text": "x"}], "[^Bad Key]"))[0].startswith("source key")
