"""Every model has a page and its topics have pages; every topic page has models; front matter is whole (D31)."""

from agmodels.registry import all_models
from web.content import CONTENT, STATUSES, TOPIC_FIELDS, TOPIC_KINDS, model_pages, topics


def test_every_model_has_a_page_and_its_topics_have_pages():
    models = all_models()
    assert set(model_pages()) == set(models), "model pages and specs differ"
    named = {t for m in models.values() for t in m.SPEC.topics}
    assert named - set(topics()) == set(), "topics without a page"
    assert set(topics()) - named == set(), "topic pages no model names"


def test_topic_front_matter():
    for topic in topics().values():
        f = topic.front
        assert set(TOPIC_FIELDS) <= set(f), topic.id
        assert f["kind"] in TOPIC_KINDS and f["status"] in STATUSES, topic.id
        assert f["title"] and topic.body, topic.id
        if f["image"]:
            assert (CONTENT / f["image"]).is_file(), topic.id
            assert f["image_credit"], f"{topic.id}: an image needs a credit (or 'to confirm')"


def test_model_page_front_matter():
    for page in model_pages().values():
        assert page.front["status"] in STATUSES and page.body, page.id


def test_colorado_potato_beetle_is_one_topic_with_three_models():
    cpb = [k for k, m in all_models().items() if m.SPEC.topics == ("colorado-potato-beetle",)]
    assert len(cpb) == 3
