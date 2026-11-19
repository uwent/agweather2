---
id: mint-flea-beetle
title: Flea Beetle (Mint)
kind: insect
crops:
  - mint
scientific_name: Longitarsus waterhousei
summary: A tiny flea beetle of peppermint and spearmint whose larvae feed on roots and rhizomes in spring; sprays target the adults in summer, after they emerge and before they lay eggs.
image: null
image_credit: null
status: draft
updated: 2026-11-19
sources:
  - key: a3422-2026
    text: 'Bradford, B. Z., J. B. Colquhoun, S. A. Chapman, A. J. Gevens, R. L. Groves, D. J. Heider, G. R. W. Nice, M. D. Ruark, Y. Wang and R. Dewerff. Commercial Vegetable Production in Wisconsin—2026 (A3422). UW–Madison Division of Extension, 2026.'
    url: https://vegpath.plantpath.wisc.edu/resources/a3422/
  - key: uw-vegento-crops
    text: 'UW–Madison Vegetable Entomology. Pests by Crop: Mint. Updated 2026.'
    url: https://vegento.russell.wisc.edu/crops/
  - key: pnw
    text: 'Mint-Mint flea beetle. In Pacific Northwest Pest Management Handbooks: Insect Management Handbook. Oregon State University, Washington State University and University of Idaho, 2026.'
    url: https://pnwhandbooks.org/insect/agronomic/mint/mint-mint-flea-beetle
  - key: uspest-mfb
    text: 'Berry, R. E. and others. Mint flea beetle degree-day model. Oregon State University, USPest.org.'
    url: https://uspest.org/cgi-bin/ddmodel2.pl?spp=mfb&uco=1&shd=1&mkg=0
  - key: agweather-mint-flea-beetle
    text: 'AgWeather. Mint flea beetle model: validation report. UW–Madison, 2026.'
    url: https://github.com/uwent/agweather2/blob/main/docs/validation/models/mint-flea-beetle.md
---

The mint flea beetle (_Longitarsus waterhousei_) is a small leaf beetle that feeds on peppermint and spearmint. The adults chew small holes in the leaves, but the larvae do the real harm, feeding on the roots and rhizomes in spring.[^pnw] UW–Madison's Vegetable Entomology lab counts it among the major pests of mint in Wisconsin, where mint is grown on muck and other high-organic soils or on fine-textured soils.[^uw-vegento-crops] Much of the published guidance on it comes from the Pacific Northwest's mint, so timings from there may not fit Wisconsin exactly.[^pnw][^uspest-mfb]

## Identification

- **Adults** are pale brown to brownish yellow and about 2 millimeters (1/12 inch) long. Like other flea beetles, they jump when disturbed.[^pnw][^a3422-2026]
- **Larvae** are small, about 3 millimeters (⅛ inch) long, and live in the soil, feeding on roots and tunneling in rhizomes.[^pnw]

## Life cycle

The mint flea beetle has one generation a year. It spends the winter as eggs in the soil, which hatch from early April through May. The larvae feed on roots and tunnel into rhizomes until early June, then leave the rhizomes to pupate.[^pnw][^uspest-mfb] In the Pacific Northwest, adults emerge in late June and July; Commercial Vegetable Production in Wisconsin puts their emergence in late July, at about 1,100 [degree days](/topics/degree-days) above 40 °F counted from soil temperatures 6 inches deep.[^pnw][^a3422-2026] Females feed for two to three weeks before they start to lay eggs, in or on the soil, in July and August.[^pnw][^a3422-2026]

The beetles move from field to field mainly in infested rootstock, usually as eggs in the soil around it.[^pnw]

## Damage

- **Larvae** damage roots and rhizomes from late April through June. Infested mint is stunted and turns purple in June.[^pnw][^a3422-2026]
- **Adults** chew small, round holes in the leaves, giving them a shot-hole look, from late June into August.[^pnw]

Infestations usually begin at field edges, and adults tend to be spotty and localized within a field.[^pnw]

## Monitoring

- **Larvae:** in late April through June, dig up roots and rhizomes with the soil around them, and look for larvae and their tunnels.[^pnw]
- **Adults:** from late June through early August, look for shot-hole feeding and sweep the foliage with a net. Sweep in the early morning, below about 60 °F, when the beetles stay on the leaves and are easiest to catch.[^pnw]
- Check the whole field, starting at the margins.[^pnw]
- **Thresholds** in Commercial Vegetable Production in Wisconsin: treat adults before they lay eggs if larval damage (stunting, purpling in June) was visible; or if there was no larval damage but sweeps of standing mint catch more than 25 adults per 100 sweeps; or if standing mint has fewer but stubble after harvest has more than 25 per 100 sweeps.[^a3422-2026]

## Management

**Nonchemical controls:**

- **Clean rootstock:** plant new fields with rootstock dug from fields free of the beetle.[^pnw]
- **Field practices:** Wisconsin growers usually plow mint shallowly once the first killing frost has come, partly to control pests that would otherwise survive the winter on the stubble, and mint is grown in short rotations of about three years in mint and three in another crop.[^uw-vegento-crops]

**Insecticides** are aimed at the adults, because no product is registered for the larvae in the soil. The goal is to spray after most adults have emerged but before females start laying eggs.[^a3422-2026][^pnw] Commercial Vegetable Production in Wisconsin lists an organophosphate (IRAC group 1B; malathion), a carbamate (group 1A; methomyl) and a neonicotinoid (group 4A; thiamethoxam).[^a3422-2026] The Pacific Northwest handbook also lists azadirachtin, with some formulations allowed in organic production, and suggests spraying in the early morning, when the beetles are on the foliage.[^pnw]

For products, rates and current registrations, see UW–Madison's [Commercial Vegetable Production in Wisconsin (A3422)](https://vegpath.plantpath.wisc.edu/resources/a3422/). The Pacific Northwest Insect Management Handbook's [mint flea beetle page](https://pnwhandbooks.org/insect/agronomic/mint/mint-mint-flea-beetle) has more detail, and UW Vegetable Entomology's [Pests by Crop](https://vegento.russell.wisc.edu/crops/) covers mint growing in Wisconsin.

## AgWeather's models

The [mint flea beetle model](/models/mint-flea-beetle) counts degree days in air from January 1 at a base of 41 °F with no upper limit, and rates risk from 0 to 4 in one window of adult activity: from emergence at 1,475 degree days, through a peak at 1,675, to its end at 1,880. It comes from VDIFN, the forecasting tool AgWeather replaces, and gives the same ratings as VDIFN for the same degree days. It was developed for the Pacific Northwest's mint and hasn't been compared with field counts in Wisconsin.[^agweather-mint-flea-beetle] Its start matches Oregon State's mint flea beetle model on USPest.org, which puts the beginning of adult emergence at 1,475 degree days from January 1 and lists itself as partly validated for the Pacific Northwest; Oregon State's model has no events for the peak or the end, so where the model's 1,675 and 1,880 come from isn't known.[^uspest-mfb][^agweather-mint-flea-beetle]

The model's timing runs ahead of Wisconsin's guide. We worked out what the window means on the calendar from AgWeather's long-term averages (degree days for 1996 to 2025): in an average year it runs from about June 25 to July 9 at Arlington, and from about July 8 to July 23 at Rhinelander. That fits the Pacific Northwest's late June and July emergence, but it ends before or around the late July emergence that Commercial Vegetable Production in Wisconsin gives.[^pnw][^a3422-2026] Use the model as a reminder to start sweeping for adults, and time sprays from your own sweep counts, before egg laying begins.
