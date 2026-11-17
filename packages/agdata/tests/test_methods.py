"""The methods record (`agdata.corrections`, `agdata.provenance`): what `/methods` serves stays true to the code and
to the evidence it cites."""

from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

from agdata import corrections, provenance
from agdata.catalog import DAILY_VARIABLES, VARIABLES
from agdata.computed import DAILY_COMPUTED
from agdata.units import UNITS

ROOT = Path(__file__).parents[3]


def _known(name: str) -> bool:
    return name in VARIABLES or name in DAILY_VARIABLES or name in DAILY_COMPUTED


def test_corrections_name_catalog_variables_and_known_units():
    for c in corrections.CORRECTIONS:
        assert c.title and c.summary, c.id
        assert c.variables and all(_known(v) for v in c.variables), c.id
        assert all(s.unit in UNITS for s in c.scores), c.id


def test_scores_are_the_evidences_numbers_for_the_current_table():
    for c in corrections.CORRECTIONS:
        if not c.scores:
            continue
        # A refit changes the table's version: its scores must be checked against the new evidence and restamped
        assert c.scored_version == c.current_version, f"{c.id}: scores measured on v{c.scored_version}"
        evidence = "".join((ROOT / path.strip()).read_text() for path in c.evidence.split(","))
        for s in c.scores:
            for number in (s.before, s.after):
                assert f"{abs(number):g}" in evidence, f"{c.id}: {s.measure} {number}"


def test_touching_follows_the_variables():
    assert corrections.touching("hours_rh_over_90") == ["gridded-rh-90"]
    assert set(corrections.touching("shortwave_radiation")) == {
        "hrrr-shortwave",
        "nbm-shortwave",
        "openmeteo-shortwave",
    }


def test_sources_name_catalog_variables():
    for u in provenance.USES:
        assert all(_known(v) for v in u.variables), u
        assert u.first is None or u.last is None or u.first <= u.last, u


def test_every_stored_hourly_variable_has_an_archive_source_from_the_first_day_on():
    archive = [u for u in provenance.USES if u.role == "archive"]
    for name, v in VARIABLES.items():
        if v.derived or name == "shortwave_radiation_hrrr":  # computed at ingest; HRRR's before our correction
            continue
        spans = sorted(((u.first, u.last) for u in archive if name in u.variables), key=lambda s: s[0] or date.min)
        assert spans, f"{name}: no archive source"
        assert spans[0][0] is None and spans[-1][1] is None, f"{name}: {spans}"
        for (_, last), (first, _) in pairwise(spans):
            assert last is not None and first == last + timedelta(days=1), f"{name}: a gap or overlap in {spans}"
