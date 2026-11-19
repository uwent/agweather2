"""Each model's checks (D98): a validation report under docs/validation/models/, and every number a check's public
summary gives found in the report section it links to."""

import re
from pathlib import Path

import pytest

from agmodels.registry import all_models

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "docs" / "validation" / "models"

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def anchor(heading: str) -> str:
    """GitHub's anchor for a Markdown heading."""
    text = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s", "-", text)


def sections(path: Path) -> dict[str, str]:
    """Each heading's anchor and the text under it, to the next heading of the same or a higher level."""
    lines = path.read_text().splitlines()
    heads = [(k, len(m.group(1)), m.group(2)) for k, line in enumerate(lines) if (m := re.match(r"^(#+) (.+)$", line))]
    out = {}
    for n, (k, level, title) in enumerate(heads):
        end = next((j for j, lv, _ in heads[n + 1 :] if lv <= level), len(lines))
        out[anchor(title)] = "\n".join(lines[k:end])
    return out


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_every_model_has_a_report_and_checks(model_id):
    spec = all_models()[model_id].SPEC
    report = REPORTS / f"{model_id}.md"
    assert report.exists(), f"{model_id} needs its validation report, {report.relative_to(ROOT)} (D98)"
    assert spec.checks, f"{model_id} needs checks in its spec (D98)"


@pytest.mark.parametrize("model_id", sorted(all_models()))
def test_each_checks_numbers_are_in_its_report_section(model_id):
    for check in all_models()[model_id].SPEC.checks:
        path, _, section = check.report.partition("#")
        assert section, f"{model_id}: {check.report} names no section"
        found = sections(ROOT / path)
        assert section in found, f"{model_id}: no section #{section} in {path}"
        text = found[section].replace(",", "")
        for number in NUMBER.findall(check.result):
            assert number.replace(",", "") in text, f"{model_id}: {number} isn't in {check.report}"
