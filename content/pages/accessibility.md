---
id: accessibility
title: Accessibility
summary: How AgWeather works toward the Web Content Accessibility Guidelines (WCAG) 2.1 at level AA, what we test, the limits we know of, and how to tell us about a problem.
status: draft
updated: 2026-11-25
---

We want everyone to be able to use AgWeather, including people who use a screen reader, a keyboard instead of a mouse, magnified text or other assistive technology. We aim to meet the Web Content Accessibility Guidelines (WCAG) 2.1 at level AA, the standard set by the [University of Wisconsin–Madison's Digital Accessibility policy](https://policy.wisc.edu/library/UW-519).

## What we test

- **Automated checks on every page.** Each page is checked against WCAG 2.1 A and AA rules with the axe accessibility checker, in light and in dark mode, at desktop and phone sizes, every time we change the site.
- **Keyboard use.** Everything works from the keyboard. "Skip to main content" is the first stop on each page, and the map's controls, its date slider and the place search are tested with the keyboard alone.
- **Text size and narrow screens.** Pages are tested with text enlarged to 200% and on screens 320 pixels wide, with no sideways scrolling of the page.
- **Color and motion.** Text meets the contrast the guidelines ask for in both light and dark mode. Pages follow your system's dark mode and reduced motion settings. Risk levels are named in words as well as shown in color.

Automated checks find only some problems, so we also check pages by hand as we build them.

## Known limits

- **Maps.** A map shows its values as colors, which a screen reader can't read. The same values are available in other forms: choose a location on the map to read its values in the panel beside it, use the table of counties below the map, or download the data from the [data page](/data).
- **Charts.** Each chart has a "Summary and data" link that describes the chart in words and lists its values as a table.
- **Outside map layers.** The optional layers on the map, such as radar, are images from outside services. They are described by their legends and credits, and we can't check them ourselves.
- **Downloads.** The data files (CSV, NetCDF and GeoTIFF) are meant for spreadsheets and analysis software, and how accessible they are depends on that software.

## Report a problem

If something in AgWeather is hard to use with your browser, screen reader or other assistive technology, please email us at [agweather@cals.wisc.edu](mailto:agweather@cals.wisc.edu). Tell us the page's address, what you were trying to do, what happened, and the browser and assistive technology you use. We will fix the problem, or help you get the same information another way.

You can also report a digital accessibility barrier to UW–Madison through [its accessibility website](https://accessible.wisc.edu/).

## Last reviewed

We last reviewed this statement on November 25, 2026.
