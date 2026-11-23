# Plans

The work, by phase in build order, and the plans that run beside a phase. Formerly PLAN.md §14 and two side plans (moved 2026-11-23): each phase keeps its text and its letters and step numbers, so "Phase 4 E" or "Phase 6 step 7" in code and reports finds its section in the phase's file. [PLAN.md](../../PLAN.md) holds the one handoff, Ben's open choices and the order of the work; [decisions.md](../decisions.md) the D# and Q# cited here.

Each phase ends with an exit gate, which includes the end-of-phase review (CLAUDE.md, "Working here": code, documentation and tests). Phases are sized in working days (Ben with Claude), not dates: S about a day, M 2–3, L 4–6, XL one to two weeks. Phases 1–4 took seven working days (2026-10-27 to 11-02), so the sizes come from that pace. What sets the calendar is mostly outside the build: Ben's answers, papers, IT and the server, and data access. The one fixed date is launch, before April 1, 2027. The old stack runs in parallel throughout.

<!-- prettier-ignore -->
| Plan | Status | |
| --- | --- | --- |
| [Phase 1: Foundations](phase-1-foundations.md) | Done 2026-10-27 (S) | Tooling, the Django skeleton, the grid, catalog and store layout, a one-month pilot, containers |
| [Phase 2: Hourly archive](phase-2-hourly-archive.md) | Built 2026-10-28 (M) | Sources into the hourly store, derived variables, QC and gaps, daily rollups, ingest jobs and the backfill, validation |
| [Phase 3: Model library](phase-3-model-library.md) | Built 2026-10-29 (M) | `agmodels`: the model spec, hourly features, season series, the legacy ports and their parity fixtures |
| [Phase 4: Forecast and blending](phase-4-forecast.md) | Built 2026-10-31 (L) | NBM, IFS and Open-Meteo stitched to the archive; its code review |
| [Phase 5: API v2](phase-5-api.md) | Done 2026-11-06 (L) | The public API and its docs; its code review |
| [Phase 6: Frontend plan and the data behind it](phase-6-frontend-plan-and-data.md) | **Current** (XL) | The frontend's decisions, climatology, climate endpoints, map images; the remaining backend work (steps 1–7) |
| [Models](models.md) | Beside Phase 6 step 4 | More models and a write-up for each: apple, the insects' review (part H), validation reports and topic pages; parts C–G and J open |
| [Humidity outside Wisconsin](humidity.md) | Beside Phase 6 | D100's follow-up: a correction of Open-Meteo's humidity fitted against URMA |
| [Phase 7: Web app, accounts and email](phase-7-web-app.md) | Sketch (XL) | The site, from WISP 3's frontend and [frontend.md](../frontend.md) |
| [Phase 8: Launch](phase-8-launch.md) | Sketch (M) | Before April 1, 2027: the server, DNS, the old stack in parallel |
| [Phase 9: Refinement and CONUS](phase-9-refinement.md) | Sketch | From the 2027 season; the validation backlog, station networks, ALIVE, the model review |

A phase's plan is detailed when it starts and ticked as work lands. When a phase is done, its file is a record: what's still current goes into [architecture.md](../architecture.md) or the code's docs. A new piece of work that needs a plan of its own gets a file here and a row above.
