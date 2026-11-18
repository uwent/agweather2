# DATCP apple pest trap network: codling moth, 2020–2025

The Wisconsin Department of Agriculture, Trade and Consumer Protection (DATCP) runs a network of pheromone traps in 25–29 cooperating apple orchards a year and publishes each site's weekly codling moth count. We use them to check `codling-moth`'s default first catch ([report](../../models/codling-moth.md)).

## Files

- `codling-moth-weekly.json`: each year, site and week (the reporting period's last day, ISO date) and the count as published (a string: `-` where the cooperator reported none, `**` marking a two-week count where the PDF does). Sites are DATCP's "County Town" names.
- `codling-moth-site-years.csv`: one row a site and year: whether the orchard used mating disruption (which suppresses trap catches), the weeks read, the first week with a catch and the first with 5 or more moths (DATCP's biofix threshold), each as the week's last day with its count, and the site's approximate location (rounded to 0.01°; DATCP's 2026 orchard map layer, or the town's centre where a site isn't on it). Cooperators' names are left out.

## Sources

Read from the PDFs by column position on 2026-11-18, and checked against counts quoted in DATCP's bulletin text (2023 August 31 Rochester 20 and Oneida 67; 2024 May 23 Rochester 34; 2025 June 12 Montello 22: all agree).

- 2020: the weekly Wisconsin Pest Bulletin's "Apple insect & black light trap counts", May 7 to August 27, `https://datcp.wi.gov/Documents2/MMDD20PestBulletin.pdf` (for example [052820](https://datcp.wi.gov/Documents2/052820PestBulletin.pdf)).
- 2021: [2021 Season Summary](https://datcp.wi.gov/PublishingImages/Pages/Programs_Services/AppleOrchardPests/2021%20Season%20Summary.pdf).
- 2022: [ApplePestSummary2022.pdf](https://datcp.wi.gov/Documents2/ApplePestSummary2022.pdf).
- 2023–2025: [2023](https://datcp.wi.gov/Documents2/2023AppleInsectCounts.pdf), [2024](https://datcp.wi.gov/Documents2/2024AppleInsectCounts.pdf), [2025](https://datcp.wi.gov/Documents2/2025AppleInsectCounts.pdf) AppleInsectCounts (page 1, "Codling Moth Trap Counts Year-End Summary").

## Caveats

- A count covers the week ending on its date, so a first catch is known only to within the 7 days before it.
- Traps are read weekly in commercial orchards, many sprayed, so the first moth is caught later than in research orchards checked every day or two.
- A site-year whose first week read already had a catch only bounds first catch from above.
- 2021 footnotes: Mineral Point May 6–19 and Hill Point May 26–June 8 are two-week counts, Oneida July 1–21 a three-week one. 2024: "First CM catch May 5 at Rochester." 2025: Campbellsport's `30**` is a two-week count placed at July 17 by position (uncertain).
- A cell beside a two-week count may be one column off; none of the checked counts was.
- No 2026 table was online on 2026-11-18 (DATCP's 2026 map keeps only the latest week).
