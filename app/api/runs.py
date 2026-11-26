"""Model runs at a point from a request's parameters (docs/api.md, "Models"; D64): the model's options, the crop's
planting date and options, and the biofix, checked and resolved into `series.RunSpec`s, one per option set.

A model's own options and its crop model's options are plain parameters named as in `GET /models/{id}`
(`maturity_group=2.5`); Ninja passes on only what a route declares, so they're read from `request.GET`. Each takes
one of its choices; an option whose choices are all numbers also takes any number (a rating from the seed bag), with
a warning outside their range. `all` runs every choice (and `planting_date=all` the three typical dates), each run
an option set; up to `MAX_OPTION_SETS`.

No planting date, no crop: a disease runs all season without the crop's susceptible window (D33, D64), and a
model whose biofix is a crop stage (the blights' emergence, red crown rot's R1) uses its spec's default date.
`planting_date=early|mid|late` takes the typical dates for the point (`agdata.planting`), and fails where there
are none rather than guessing."""

import itertools
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from django.conf import settings

from agdata.planting import CROPS, TIERS, PlantingDate, planting_crop, typical_planting
from agdata.series import RunSpec
from agmodels.registry import all_models
from agmodels.registry import model as find_model
from agmodels.runner import FixedBiofixError, check_biofix, stage_date_option
from agmodels.spec import Model, ModelSpec, Option
from api.errors import ApiError, quoted

MAX_OPTION_SETS = 20
ALL = "all"


@dataclass(kw_only=True)
class Plan:
    """What to run: one `RunSpec` per option set, and how to describe them."""

    model: Model
    runs: list[RunSpec]
    option_sets: list[dict[str, Any]]  # per run, the values that vary between sets (empty with one set)
    request: dict[str, Any]  # the run's choices as computed, for `meta.request`
    warnings: list[str] = field(default_factory=list)


def model_or_404(model_id: str) -> Model:
    if model_id not in all_models():
        raise ApiError(
            "not_found",
            f"We don't have a model with the id {quoted(model_id)}. GET /api/v2/models lists every model and its id.",
            "model",
            status=404,
        )
    return find_model(model_id)


def plan(
    m: Model,
    params: Mapping[str, str],
    lat: float,
    lng: float,
    season: int,
    biofix: date | None,
    planting: str | None,
    lenient: bool = False,
) -> Plan:
    """The runs a request asks for. `season` is the year a typical planting date falls in. `lenient` (several models
    in one request): a planting date is ignored by a model without a crop or whose gate's crop is only some of its
    own (`Susceptibility.planting_given_only`), and a crop without typical dates here runs without one, with a
    warning."""
    spec = m.SPEC
    warnings: list[str] = []
    crop = planting_crop(spec)
    if lenient and planting:
        if crop is None or (spec.susceptible is not None and spec.susceptible.planting_given_only):
            planting = None  # wheat scab's gate is spring wheat's: a date given for several models isn't its
        elif planting in (*TIERS, ALL) and (
            crop[1] not in CROPS or typical_planting(crop[1], lat, lng, data_dir=settings.DATA_DIR) is None
        ):
            warnings.append(
                f"We have no typical {crop[1]} planting dates for this location, so it runs without a planting date."
            )
            planting = None
    if not lenient and biofix is not None and crop is not None and crop[0] == spec.id:
        # A crop model counting from planting (`GET /models/{id}` lists its biofix as the planting date): 'biofix'
        # is its planting date, as for the models with a biofix of their own
        if planting not in (None, "", biofix.isoformat()):
            raise ApiError(
                "conflict",
                f"The {spec.name} model's biofix is its planting date, and this request gives two different ones. Give only {quoted('planting_date')}.",
                "planting_date",
            )
        planting, biofix = biofix.isoformat(), None
    crop_spec = find_model(crop[0]).SPEC if crop and crop[0] != spec.id else None
    own = {o.name: option_values(o, params.get(o.name), warnings) for o in spec.options}
    _check_stage_date(spec, own, season)
    crop_opts = (
        {} if crop_spec is None else {o.name: option_values(o, params.get(o.name), warnings) for o in crop_spec.options}
    )
    plantings, planting_echo = _plantings(spec, crop, planting, lat, lng, season)
    given = [o.name for o in (crop_spec.options if crop_spec else ()) if params.get(o.name)]
    if given and planting_echo is None:
        # The crop's stages run only from a planting date: its options would only repeat the same run
        warnings.append(
            f"{', '.join(quoted(g) for g in given)} set the crop's stages, which run only from a planting date, so we left them out. Add 'planting_date' to use them."
        )
        crop_opts = {o.name: [o.default] for o in crop_spec.options} if crop_spec else {}
    if biofix is not None and spec.biofix is None:
        raise ApiError(
            "not_applicable", f"The {spec.name} model doesn't take a biofix date. Leave out 'biofix'.", "biofix"
        )
    try:  # the runner refuses it too (`runner.check_biofix`), whatever calls it; this says so in the API's words
        check_biofix(spec, biofix)
    except FixedBiofixError:
        assert spec.biofix is not None
        month, day = (int(p) for p in spec.biofix.default.split("-"))
        raise ApiError(
            "not_applicable",
            f"The {spec.name} model always counts from {date(2001, month, day):%B} {day}, so it doesn't take a biofix date. Leave out {quoted('biofix')}.",
            "biofix",
        ) from None

    axes: list[tuple[str, list[Any]]] = [("planting_date", plantings)]
    axes += [*own.items(), *crop_opts.items()]
    count = 1
    for _, values in axes:
        count *= len(values)
    if count > MAX_OPTION_SETS:
        raise ApiError(
            "too_many",
            f"This request asks for {count} combinations of options; a request can run up to {MAX_OPTION_SETS}. Choose fewer options with 'all'.",
            ALL,
        )
    varying = [name for name, values in axes if len(values) > 1]
    runs, sets = [], []
    for combo in itertools.product(*(values for _, values in axes)):
        chosen = dict(zip([name for name, _ in axes], combo, strict=True))
        sowing = chosen.pop("planting_date")
        is_crop_model = crop is not None and crop[0] == spec.id
        runs.append(
            RunSpec(
                model_id=spec.id,
                biofix=sowing if is_crop_model else biofix,
                planting=None if is_crop_model else sowing,
                options={name: chosen[name] for name in own},
                crop_options={name: chosen[name] for name in crop_opts},
            )
        )
        sets.append({name: (sowing if name == "planting_date" else chosen[name]) for name in varying})
    request = {
        "model": spec.id,
        "version": spec.version,
        "biofix": biofix,
        "planting_date": planting_echo,
        "options": {name: values if len(values) > 1 else values[0] for name, values in own.items()},
    }
    if crop_spec is not None:
        request["crop"] = {
            "model": crop_spec.id,
            "options": {name: values if len(values) > 1 else values[0] for name, values in crop_opts.items()},
        }
    return Plan(model=m, runs=runs, option_sets=sets if len(runs) > 1 else [], request=request, warnings=warnings)


def _check_stage_date(spec: ModelSpec, own: dict[str, list[str]], season: int) -> None:
    """The date for a susceptible window (wheat scab's flowering date) must be a date, if given."""
    name = stage_date_option(spec)
    for value in own.get(name, []) if name is not None else []:
        if not value:
            continue
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ApiError(
                "invalid",
                f"Give {quoted(name)} as a date (YYYY-MM-DD), such as {quoted(f'{season}-06-10')}.",
                name,
            ) from None


def option_values(option: Option, raw: str | None, warnings: list[str]) -> list[str]:
    """The values an option runs with: its default, the one given, or every choice for `all`."""
    choices = [value for value, _ in option.choices]
    if raw is None or raw == "":
        return [option.default]
    if raw == ALL:
        if not choices:
            raise ApiError(
                "invalid",
                f"{quoted(option.name)} has no list of choices, so it can't be set to 'all'. Give one value.",
                option.name,
            )
        return choices
    if not choices or raw in choices:
        return [raw]
    numbers = _numbers(choices)
    if numbers is not None:
        try:
            value = float(raw)
        except ValueError:
            pass
        else:
            if not min(numbers) <= value <= max(numbers):
                warnings.append(
                    f"{quoted(f'{option.name}={raw}')} is outside its usual range of {min(numbers):g} to {max(numbers):g}. The model runs with it as given, so check that it's the value you meant."
                )
            return [raw]
    listed = ", ".join(quoted(c) for c in choices)
    hint = " or a number" if numbers is not None else ""
    raise ApiError(
        "invalid", f"{quoted(option.name)} must be one of {listed}{hint}, or 'all' to run every choice.", option.name
    )


def _numbers(choices: list[str]) -> list[float] | None:
    try:
        return [float(c) for c in choices]
    except ValueError:
        return None


def _plantings(
    spec: ModelSpec, crop: tuple[str, str] | None, raw: str | None, lat: float, lng: float, season: int
) -> tuple[list[date | None], dict[str, Any] | None]:
    """The planting dates to run (None: none given) and their echo: the date, and for a typical one its tier and
    source."""
    if raw is None or raw == "":
        return [None], None
    if crop is None:
        raise ApiError(
            "not_applicable",
            f"The {spec.name} model doesn't take a planting date. Leave out 'planting_date'.",
            "planting_date",
        )
    if raw not in (*TIERS, ALL):
        try:
            return [date.fromisoformat(raw)], {"date": raw}
        except ValueError:
            raise ApiError(
                "invalid",
                "Give 'planting_date' as a date (YYYY-MM-DD), or as 'early', 'mid' or 'late' for this location's typical dates, or 'all' for all three.",
                "planting_date",
            ) from None
    crop_name = crop[1]
    found = typical_planting(crop_name, lat, lng, data_dir=settings.DATA_DIR) if crop_name in CROPS else None
    if found is None:
        raise ApiError(
            "no_estimate",
            f"We have no typical {crop_name} planting dates for this location. Give 'planting_date' as a date (YYYY-MM-DD).",
            "planting_date",
        )
    tiers = list(TIERS) if raw == ALL else [raw]
    dates = [_in_season(found, TIERS[t], season) for t in tiers]
    echo = {
        "tier": raw,
        "date": [d.isoformat() for d in dates] if raw == ALL else dates[0].isoformat(),
        "typical": {"early": found.early, "mid": found.typical, "late": found.late},
        "level": found.level,
        "area": found.area,
        "source": found.source,
    }
    return list(dates), echo


def _in_season(found: PlantingDate, field_name: str, season: int) -> date:
    """A typical MM-DD in the season's year; one before the early date (winter wheat's late, in January) the next."""
    text = getattr(found, field_name)
    month, day = (int(p) for p in text.split("-"))
    early_month, early_day = (int(p) for p in found.early.split("-"))
    year = season + 1 if (month, day) < (early_month, early_day) else season
    return date(year, month, day)
