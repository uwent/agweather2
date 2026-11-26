# Accessibility

AgWeather aims at WCAG 2.1 AA (docs/frontend.md, Accessibility and testing). This file records the audit: what was checked, what was found, and how it was fixed. Its format is WISP 3's (`../wisp3/docs/accessibility.md`), whose findings the ported components already carry.

## Automated checks

`e2e/accessibility.spec.ts` (WISP 3's `scan()`) runs axe (`@axe-core/playwright`, WCAG 2.1 A and AA rules) on every page in light (the desktop project) and dark (the phone project), and again in the other theme through the theme toggle; on desktop it also checks reflow (320 px wide, and text at 200%, with no sideways page scroll). It opens collapsed sections first and waits for transitions to finish. It runs with the rest of `bin/e2e` and fails on any violation. Add each new page to a group of its `PAGES` (or a test of its own when the page needs stubbed answers).

Axe finds roughly a third of WCAG problems; manual checks (keyboard, screen reader, zoom) follow as the pages are built, as WISP 3's did.

### First run (2026-11-26, Phase 7 wave 1): nothing found

The home page, the changelog and the API use form, with the new header, footer and settings dialog, in light and dark at desktop and phone sizes: no violations, and no sideways scroll at 320 px or with 200% text.

Choices made while porting, so they don't become findings:

- **Danger as text** (`danger-ink`): an error under a field uses a darker red in light mode (48% lightness, for the tan surfaces) and a lighter one in dark mode, where the fill color (`danger`, WISP 3's `status-irrigate`) is too dark to read as text. WISP 3's `status-irrigate-ink`.
- **Tints a step darker than the raised surface** (`brand-50`, `brand-100`): our raised surface is the old site's tan, so the light tints moved one palette step darker (sand-200, sand-300) to stay visible as a chosen pill, a highlighted menu item and the current section.
- **A term's "See the glossary" link** (`Term.svelte`, track 7 step 7.4) is a pointer's shortcut with `tabindex="-1"`: the popup is a tooltip that never takes focus, so a link in it couldn't be reached in order anyway. The keyboard reaches every definition in place (the popup opens on Enter or Space) and the glossary page from the footer. The glossary page (`/glossary`), About, Accessibility and Contact joined the axe scan's `PAGES` with no violations, light and dark, and reflow at 320 px and 200% text.
- **The header's sections on phones** scroll sideways with a fade at the edge that has more (WISP 3's nav); at 375 px all six fit, and at 320 px the last ones scroll.
