"""Events on a model's results at points (PLAN.md Phase 6 step 3): `first=`, `last=` and `since=` on a model run.

`first=high` finds the first day the model's risk is High or above; on a crop model `first=R1` the first day at R1
or later; any output takes bounds after its name, `first=dd_total:above_450` (in the units the output is shown in),
and the default output (the risk level, or a crop model's stage) takes them alone (`first=above_3` on an insect's
risk level). Insects' life stages are numbers for now (`first=stage:above_3`). The days are the run's rows, from the
request's start (its biofix or January 1 by default) through the forecast; `since=` counts to the end asked for, or
to today when it's left out. Days are found as `api.events` finds a weather variable's.

With a projection, a `first=` not found by the end of the forecast is looked for in each earlier year's path, and
the answer gives in how many years it's reached and the 10th, 50th and 90th percentile dates (`agmodels.scenarios`).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from django.http import HttpRequest

from agdata.modelgrid import OUTPUT_STEPS
from agdata.projection import PROJECTION
from agdata.seasonal import level_key
from agmodels.runner import ModelRun
from agmodels.scenarios import reached
from agmodels.spec import Model
from api import counts, events
from api.envelope import SYSTEMS, Column, shown_unit, unit_overrides
from api.errors import ApiError, quoted

RISK_LEVEL, RISK_VALUE = "risk_level", "risk_value"


@dataclass(frozen=True, kw_only=True)
class ModelEvent:
    """One `first=`, `last=` or `since=` on a model's output: the bounds in the output's stored unit."""

    kind: events.Kind
    asked: str  # as given, `first=high`
    output: str
    low: float | None
    high: float | None


def default_output(m: Model) -> str:
    return RISK_LEVEL if m.SPEC.risk is not None else "stage"


def outputs(m: Model) -> dict[str, str]:
    """The outputs an event can look at, with their stored units."""
    spec = m.SPEC
    found: dict[str, str] = {}
    if spec.risk is not None:
        found[RISK_LEVEL] = "index"
        if spec.risk.thresholds:
            found[RISK_VALUE] = "index"
    return found | {q.name: q.unit for q in spec.outputs}


def named(m: Model, output: str) -> dict[str, int]:
    """The names an output's values take: a risk level's (`high`), a crop stage's code (`r1`), as each one's index."""
    spec = m.SPEC
    if output == RISK_LEVEL and spec.risk is not None:
        return {level_key(label): k for k, label in enumerate(spec.risk.levels)}
    if output == "stage" and spec.group == "crop":
        return {s.code.lower(): k for k, s in enumerate(m.stages())}  # type: ignore[attr-defined]
    return {}


def named_words(m: Model, output: str, kind: events.Kind, value: str) -> str:
    """`first day at High risk or higher`, `days since the last day at stage R1 or later`."""
    spec = m.SPEC
    k = named(m, output)[value.lower()]
    if output == RISK_LEVEL and spec.risk is not None:
        what = f"day at {spec.risk.levels[k]} risk or higher"
    else:
        what = f"day at stage {m.stages()[k].code} or later"  # type: ignore[attr-defined]
    return f"days since the last {what}" if kind == "since" else f"{kind} {what}"


def map_event(m: Model, output: str, kind: events.Kind, text: str) -> events.Event:
    """A map's `first=`, `last=` or `since=` on the output it shows (`output=`): a named risk level or crop stage, or
    bounds as on a weather layer (`api.events.parse`)."""
    value = text.strip()
    if ":" in value:
        name = value.split(":", 1)[0]
        raise ApiError(
            "invalid",
            f"A map looks for days in the result it shows. Give {quoted(f'output={name}')} and {quoted(f'{kind}={value.split(":", 1)[1]}')}.",
            kind,
        )
    names = named(m, output)
    if value.lower() in names:
        low = names[value.lower()] - 0.25
        return events.Event(
            kind=kind,
            low=low,
            high=None,
            named=None,
            name=value.lower().replace(".", "p"),
            stored=(low, None),
            title=named_words(m, output, kind, value),
        )
    try:
        return events.parse(kind=kind, text=value)
    except ApiError as error:
        if not names:
            raise
        some = " or ".join(quoted(f"{kind}={n}") for n in list(names)[1:3])
        raise ApiError(
            "invalid",
            f"We can't read {quoted(f'{kind}={text}')}. Give a name such as {some}, or bounds such as {quoted(f'{kind}=above_2')}.",
            kind,
        ) from error


def parse(m: Model, kind: events.Kind, text: str, request: HttpRequest, units: str) -> ModelEvent:
    """`high`, `R1`, `above_3` or `dd_total:above_450` → a ModelEvent; ApiError naming the forms otherwise."""
    spec = m.SPEC
    asked = f"{kind}={text}"
    name, colon, given = text.partition(":")
    output = name.strip() if colon else default_output(m)
    value = (given if colon else text).strip()
    known = outputs(m)
    if output not in known:
        listed = ", ".join(quoted(o) for o in known)
        raise ApiError(
            "invalid", f"{spec.name} has no result named {quoted(output)} to look for. Choose one of: {listed}.", kind
        )
    names = named(m, output)
    if value.lower() in names:
        return ModelEvent(kind=kind, asked=asked, output=output, low=names[value.lower()] - 0.25, high=None)
    if value.lower() in events.NAMED_F:
        raise ApiError(
            "invalid",
            f"{quoted(value)} is a temperature, which a model's results aren't. Give bounds such as {quoted(f'{kind}={output}:above_10')}.",
            kind,
        )
    examples = _examples(kind, output, names)
    low, high = counts.parse_bounds(value.lower(), text, kind, examples)
    stored = known[output]
    step = OUTPUT_STEPS.get(stored, 0.001)
    column = Column(name=output, values=[], unit=stored, step=step, variable=output)
    shown = shown_unit(column, SYSTEMS.get(units, "imperial"), unit_overrides(request))
    low, high = counts.stored_bounds(low, high, shown, stored, step)
    return ModelEvent(kind=kind, asked=asked, output=output, low=low, high=high)


def _examples(kind: str, output: str, names: dict[str, int]) -> str:
    if names:
        some = list(names)[1:3] or list(names)[:1]
        return " or ".join(quoted(f"{kind}={n}") for n in some) + f", or bounds such as {quoted(f'{kind}=above_2')}"
    return f"bounds such as {quoted(f'{kind}={output}:above_10')} or {quoted(f'{kind}={output}:between_10_20')}"


def asked(m: Model, request: HttpRequest, units: str, given: dict[str, Any] | None = None) -> list[ModelEvent]:
    """Every `first=`, `last=` and `since=` (repeated, or separated by commas), from the query or `given` (a posted
    body's: a string or a list of them each)."""
    found: dict[str, ModelEvent] = {}
    for kind in events.KINDS:
        if given is None:
            raw = request.GET.getlist(kind)
        else:
            sent = given.get(kind, [])
            raw = sent if isinstance(sent, list) else [sent]
        for text in (part.strip() for item in raw for part in str(item).split(",")):
            if text:
                event = parse(m, kind, text, request, units)
                found[event.asked] = event
    return list(found.values())


def series_of(run: ModelRun, output: str) -> np.ndarray | None:
    if output == RISK_LEVEL:
        return run.level
    if output == RISK_VALUE:
        return run.risk if run.level is not None else None
    return run.outputs.get(output)


def _found(e: ModelEvent, run: ModelRun, n: int) -> tuple[float, int]:
    """The day found in the run's first `n` rows (days since 1970, or days since for `since`; NaN if none), and the
    rows without a value."""
    values = series_of(run, e.output)
    if values is None or n == 0 or not run.dates:
        return float("nan"), n
    value, _, missing = events.find(
        np.asarray(values, dtype=float)[:n, None], low=e.low, high=e.high, kind=e.kind, first_day=run.dates[0]
    )
    return float(value[0]), int(missing[0])


def answer(e: ModelEvent, paths: list[ModelRun], n: int, since_end: date | None) -> dict[str, Any]:
    """`meta.summary.events`' entry: the day found in the first path's first `n` rows (observed and forecast), with
    its kind, and with several paths (a projection's years), where a `first=` not found by then falls in each."""
    run = paths[0]
    shown = [k for k, kind in enumerate(run.kinds[:n]) if kind != PROJECTION]
    known = len(shown)
    if e.kind == "since" and since_end is not None:
        known = min(known, sum(d <= since_end for d in run.dates[:known]))
    value, missing = _found(e, run, known)
    out: dict[str, Any] = {"event": e.asked, "kind": e.kind, "output": e.output}
    if e.kind == "since":
        out["days"] = None if np.isnan(value) else int(value)
    else:
        day = None if np.isnan(value) else events.to_date(value)
        out["date"] = day
        out["day_kind"] = None if day is None else run.kinds[(day - run.dates[0]).days]
        out["before_start"] = bool(day is not None and day == run.dates[0] and _started_before(run))
    out["missing_days"] = missing
    if e.kind == "first" and len(run.dates) > known and any(k == PROJECTION for k in run.kinds):
        days = []
        for path in paths:
            found, _ = _found(e, path, len(path.dates))
            days.append(None if np.isnan(found) else events.to_date(found))
        r = reached("event", e.asked, days)
        out["projection"] = {"reached": r.reached, "of": r.of, "p10": r.p10, "p50": r.p50, "p90": r.p90}
    return out


def _started_before(run: ModelRun) -> bool:
    """Whether the model was running before the run's first row, so a day found on it may have come earlier: its
    biofix is earlier, or it has none and the rows don't start on January 1."""
    first = run.dates[0]
    return run.biofix < first if run.biofix is not None else (first.month, first.day) != (1, 1)


def milestone_now(r, run: ModelRun) -> dict[str, Any]:
    """A milestone (`agmodels.scenarios.milestones` on one run) as `meta.summary.milestones` gives it."""
    day = r.p50
    kind = None if day is None else run.kinds[(day - run.dates[0]).days]
    return {
        "what": r.what,
        "name": r.name,
        "date": day,
        "day_kind": kind,
        "before_start": bool(day is not None and day == run.dates[0] and _started_before(run)),
    }
