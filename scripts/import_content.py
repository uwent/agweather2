"""Seed `content/` (PLAN.md Phase 3 E) with draft topic and model pages from the Crop Risk Tool's docs and VDIFN's seed
texts, and copy their images. Pages that exist are left alone (rewrites happen in place in Phase 6); pass --force to
rebuild them all.

Sources: `tmp/shiny/crop-risk-tool/docs/` (Markdown: the text before "Model details" seeds the topic, the model
sections the model page, "References"/"More information" go to the topic) and VDIFN's `db/seeds.rb`, dumped to JSON
by `scripts/dump_vdifn_seeds.rb` (HTML `info` seeds the topic, `severity_info` the model page).

Run: `ruby scripts/dump_vdifn_seeds.rb ../ag-vdifn/db/seeds.rb > tmp/content-import/vdifn_seeds.json`
then `uv run python scripts/import_content.py` and `pnpm format` (CI checks `content/` with Prettier).
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

from agmodels.registry import all_models

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CRT_DOCS = ROOT / "tmp" / "shiny" / "crop-risk-tool" / "docs"
VDIFN_SEEDS = ROOT / "tmp" / "content-import" / "vdifn_seeds.json"
VDIFN_IMAGES = ROOT.parent / "ag-vdifn" / "public" / "images" / "pests"

CRT_DOC = {  # model id: the Crop Risk Tool's doc
    "early-blight-pdays": "early-blight.md",
    "late-blight-dsv": "late-blight.md",
    "carrot-foliar-dsv": "alternaria.md",
    "cercospora-beet-div": "cercospora-beet.md",
    "botrytis-onion-botcast": "botrytis.md",
    "tar-spot": "tar-spot.md",
    "gray-leaf-spot": "gray-leaf-spot.md",
    "gibberella-ear-rot-don": "don.md",
    "white-mold": "white-mold.md",
    "frogeye-leaf-spot": "frogeye.md",
    "soybean-cercospora": "cercospora-soybean.md",
    "red-crown-rot": "red-crown-rot.md",
    "wheat-scab": "wheat-scab.md",
    "pecan-scab": "pecan-scab.md",
    "cotton-planting": "cotton-planting.md",
    "rye-biomass": "rye-biomass.md",
    "seedcorn-maggot": "insects/scm.md",
    "alfalfa-weevil": "insects/alfalfa-weevil.md",
    "colorado-potato-beetle": "insects/cpb.md",
}
VDIFN_NAME = {  # model id: VDIFN's local_name, where they differ
    "early-blight-pdays": "early-blight",
    "late-blight-dsv": "late-blight",
    "carrot-foliar-dsv": "carrot-foliar",
    "cercospora-beet-div": "cercospora-leaf-spot",
    "botrytis-onion-botcast": "botrytis-leaf-blight",
    "aphid-pvy-vectors": "pvy-vectors",
    "colorado-potato-beetle": "cpb",
    "colorado-potato-beetle-adults": "cpbad",
    "colorado-potato-beetle-larvae": "cpbl",
    "oak-wilt-vectors": "oak-wilt",
}
KIND = {"disease": "disease", "insect": "insect", "crop": "crop", "agronomic": "agronomic", "degree_days": "weather"}
CREDITS = {"pecan-scab.jpg": "APS / Hoefnagels and Mason"}  # the only image credit the sources give


def main(force: bool) -> None:
    vdifn = {r["local_name"]: r for r in json.loads(VDIFN_SEEDS.read_text())}
    topics: dict[str, dict] = {}
    for model_id, model in sorted(all_models().items()):
        spec = model.SPEC
        doc = _crt_sections(CRT_DOCS / CRT_DOC[model_id]) if model_id in CRT_DOC else None
        seed = vdifn.get(VDIFN_NAME.get(model_id, model_id))
        for topic_id in spec.topics:
            t = topics.setdefault(
                topic_id,
                {"kind": KIND[spec.group], "crops": set(), "title": None, "body": [], "image": None, "sources": set()},
            )
            t["crops"] |= set(spec.crops)
            if doc:
                t["title"] = t["title"] or doc["title"]
                t["body"].append(doc["topic"])
                t["image"] = t["image"] or doc["image"]
                t["sources"].add(f"Crop Risk Tool docs/{CRT_DOC[model_id]}")
            if seed:
                t["title"] = t["title"] or seed["name"]
                if not doc:
                    t["body"].append(_markdown(seed.get("info") or ""))
                t["image"] = t["image"] or (VDIFN_IMAGES / seed["photo"] if seed.get("photo") else None)
                t["sources"].add(f"VDIFN db/seeds.rb ({seed['local_name']})")
                if seed.get("link"):
                    t["body"].append(f"- More: <{seed['link']}>")
        model_body = (doc and doc["model"]) or (seed and _markdown(seed.get("severity_info") or "")) or ""
        sources = ([f"Crop Risk Tool docs/{CRT_DOC[model_id]}"] if doc else []) + (
            [f"VDIFN db/seeds.rb ({seed['local_name']})"] if seed else []
        )
        _write(
            CONTENT / "models" / f"{model_id}.md",
            {"id": model_id, "status": "draft", "sources": sources},
            model_body or "To write: how the model works, how to read it, its validation and caveats.",
            force,
        )

    for topic_id, t in sorted(topics.items()):
        image = _copy_image(t["image"], topic_id) if t["image"] else None
        front = {
            "id": topic_id,
            "title": t["title"] or topic_id.replace("-", " ").capitalize(),
            "kind": t["kind"],
            "crops": sorted(t["crops"]),
            "scientific_name": "",
            "summary": "",
            "image": image,
            "image_credit": CREDITS.get(Path(t["image"]).name, "to confirm") if t["image"] else None,
            "status": "draft",
            "sources": sorted(t["sources"]),
        }
        body = "\n\n".join(_dedupe(b for b in t["body"] if b.strip())) or "To write: the subject, and how to manage it."
        _write(CONTENT / "topics" / f"{topic_id}.md", front, body, force)


def _crt_sections(path: Path) -> dict:
    """The doc's title, first image, topic text (before the model sections, plus links) and model text."""
    text = path.read_text()
    title = re.search(r"^#+\s*(.+)$", text, re.M)
    image = re.search(r"!\[[^\]]*\]\(([^)\s]+)", text)
    parts = re.split(r"^(#{2,3} .+)$", text, flags=re.M)
    topic, model, heading = [], [], None
    for part in parts:
        if re.match(r"^#{2,3} ", part):
            heading = part.strip("# ").strip()
            continue
        part = re.sub(r"!\[[^\]]*\]\([^)]*\)\s*", "", part).strip()
        if not part or heading is None or heading == (title[1].strip() if title else None):
            if part:
                topic.append(part)
            continue
        if heading.lower().startswith("model"):
            model.append(f"## {heading}\n\n{part}")
        elif heading.lower().startswith(("references", "more information")):
            topic.append(f"## More information\n\n{part}")
        else:
            topic.append(f"## {heading}\n\n{part}")
    return {
        "title": title[1].strip() if title else path.stem,
        "image": (path.parent / image[1]) if image else None,
        "topic": "\n\n".join(topic),
        "model": "\n\n".join(model),
    }


def _markdown(source: str) -> str:
    """VDIFN's small HTML (p, b, i, a, ul/li, br) as Markdown."""
    s = re.sub(r"\s+", " ", source)
    s = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"[\2](\1)", s)
    s = re.sub(r"</?(b|strong)>", "**", s)
    s = re.sub(r"</?(i|em)>", "*", s)
    s = re.sub(r"<li>\s*", "\n- ", s)
    s = re.sub(r"</p>|<br\s*/?>|</ul>|</ol>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(s)).strip()


def _copy_image(source: Path, topic_id: str) -> str:
    target = CONTENT / "images" / f"{topic_id}{Path(source).suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return f"images/{target.name}"


def _dedupe(parts) -> list[str]:
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _write(path: Path, front: dict, body: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(f"---\n{front_matter}---\n\n{body.strip()}\n")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
