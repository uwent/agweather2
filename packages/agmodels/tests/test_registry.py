"""The registry and model pages: lookups by id, the page beside each module, and what a bad page says."""

import pytest

from agmodels import registry
from agmodels.pages import read_page
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
