// Ported from WISP 3 (adapted): app/frontend/lib/glossary.ts
// Terms AgWeather uses, explained where they appear (Term.svelte, GlossaryText.svelte) and, later, on
// the glossary page. Definitions are for growers and consultants: plain words, a sentence or three,
// no more precise than the models are (CLAUDE.md, Writing for the public).

import { normalsHref } from '@/lib/methods'
import { routes } from '@/lib/routes'

export type GlossaryEntry = {
  id: string
  term: string
  /**
   * Wordings that mark this term in text, matched as whole words. One in capitals (an
   * abbreviation) matches only in capitals; the rest match in any case.
   */
  matches: string[]
  definition: string
  /** Where to read more, shown after the definition on the glossary page */
  more?: { href: string; label: string }
}

const HOW_NORMALS = { href: normalsHref(), label: 'How we make normals' }

export const GLOSSARY: GlossaryEntry[] = [
  {
    id: 'growing_degree_days',
    term: 'Growing degree days (GDD)',
    matches: ['growing degree days', 'growing degree day', 'degree days', 'degree day', 'GDD'],
    definition:
      'A measure of the heat a crop or insect has had to grow and develop. Each day adds the amount its average temperature was above a base threshold (and, for some models, held below an upper threshold); a cool day adds little or nothing. Added up from a start date, degree days predict when a crop or pest reaches a stage better than the calendar does.',
  },
  {
    id: 'base_threshold',
    term: 'Base threshold',
    matches: ['base threshold', 'base temperature', 'lower threshold'],
    definition:
      "The temperature below which a crop or insect doesn't develop. Degree days count only the heat above it, so models of different organisms use different bases, such as 50 °F for corn and 48 °F for alfalfa weevil.",
  },
  {
    id: 'upper_threshold',
    term: 'Upper threshold',
    matches: ['upper threshold', 'upper cutoff', 'upper temperature'],
    definition:
      "The temperature above which development no longer speeds up. Degree days count a hotter day as if it stopped at this temperature, so a heat wave doesn't add more than the crop or insect can use.",
  },
  {
    id: 'biofix',
    term: 'Biofix',
    matches: ['biofix'],
    definition:
      'The date a model starts counting from: an event seen in the field, such as the first moths caught in a trap or crop emergence, or a fixed date such as January 1 when none is set. Setting your own biofix fits the model to your field.',
  },
  {
    id: 'emergence',
    term: 'Emergence',
    matches: ['emergence', 'crop emergence'],
    definition:
      "When a crop's first shoots break through the soil surface. Disease models for potatoes and other crops often start counting at emergence, because the plants can't be infected before then.",
  },
  {
    id: 'dsv',
    term: 'Disease severity value (DSV)',
    matches: ['disease severity values', 'disease severity value', 'DSV', 'DSVs'],
    definition:
      "A daily score from 0 to 4 of how favorable the weather was for a disease, from the hours the leaves stayed wet and the temperature during them. Values add up through the season, and a total past the model's threshold means it is time to protect the crop.",
  },
  {
    id: 'p_days',
    term: 'Physiological days (P-days)',
    matches: ['physiological days', 'P-days', 'P-day'],
    definition:
      "A heat total like degree days, weighted for the potato plant: each day's temperatures are scored by how well they suit potato growth. Early blight models use 300 P-days from emergence as the time to begin protecting the crop.",
  },
  // Climate (Phase 7 track 6.1): normals, their spread and freezes
  {
    id: 'normal',
    term: 'Normal',
    matches: ['climate normals', 'climate normal', 'normals'],
    definition:
      "The usual weather for a place and time of year: the average over a run of recent years, the last 30 by default, or the last 10 or 5. We compute a place's normals from its own past years, so a normal total to a date is each year's own total, averaged.",
    more: HOW_NORMALS,
  },
  {
    id: 'percentile',
    term: 'Percentile',
    matches: ['percentiles', 'percentile'],
    definition:
      'Where a value ranks among past years. The 50th percentile is the middle year; the 90th is a value only 1 year in 10 went above. The range from the 10th to the 90th percentile holds 8 years in 10, so a value outside it is unusual.',
    more: HOW_NORMALS,
  },
  {
    id: 'departure',
    term: 'Departure from normal',
    matches: ['departures from normal', 'departure from normal', 'departures', 'departure'],
    definition:
      "How far a value is from its normal: this year's value less the normal. Above normal is positive and below normal negative.",
    more: HOW_NORMALS,
  },
  {
    id: 'frost',
    term: 'Frost',
    matches: ['frosts', 'frost'],
    definition:
      'A night when the air falls to 32 °F (0 °C) or colder, 2 m (6.5 ft) above the ground. Tender crops can be damaged. Low spots and plants near the ground can frost on nights a little warmer than this.',
  },
  {
    id: 'hard_freeze',
    term: 'Hard freeze',
    matches: ['hard freezes', 'hard freeze'],
    definition:
      'A night when the air falls to 28 °F (−2.2 °C) or colder. It kills or badly damages most warm-season crops and ends the growing season for many annual plants.',
  },
  {
    id: 'killing_freeze',
    term: 'Killing freeze',
    matches: ['killing freezes', 'killing freeze'],
    definition:
      "A night when the air falls to 24 °F (−4.4 °C) or colder, cold enough to kill the top growth of hardier crops such as alfalfa. Crops differ, and a tool for one crop may use that crop's own killing temperature.",
  },
  {
    id: 'frost_free_season',
    term: 'Frost-free season',
    matches: ['frost-free seasons', 'frost-free season', 'season without a frost'],
    definition:
      "The days between the last frost of spring and the first frost of fall, when crops can grow without one. It's counted in each year, so its typical length isn't simply the time between the typical dates.",
    more: HOW_NORMALS,
  },
  // --- Reference terms (Phase 7 step 7.4, the glossary page): models' scales, weather and the grid ---
  {
    id: 'risk_level',
    term: 'Risk level',
    matches: ['risk level', 'risk levels'],
    definition:
      "A model's result in words, such as Low, Moderate or High, set by the thresholds in the research behind the model. The same level has the same color on every map and chart. A high risk means the weather has favored the pest or disease, not that it is present in your field.",
  },
  {
    id: 'div',
    term: 'Daily infection value (DIV)',
    matches: ['daily infection values', 'daily infection value', 'DIV', 'DIVs'],
    definition:
      'A daily score from 0 to 7 of how favorable the weather was for Cercospora leaf spot of sugar beet, from the hours of high humidity and their temperature. The model averages the scores over the last 2 and 7 days to judge the risk.',
  },
  {
    id: 'degree_day_method',
    term: 'Degree-day method',
    matches: ['degree-day method', 'single sine', 'modified average', 'simple average'],
    definition:
      "How a day's degree days are worked out from its low and high temperatures. The simple average takes the day's average less the base; the modified average first raises the low to the base and lowers the high to the upper threshold; the single sine fits a curve through the low and high, and is the most common method for insects. Use the method a model was developed with.",
  },
  {
    id: 'et0',
    term: 'Reference evapotranspiration (ET0)',
    matches: ['reference evapotranspiration', 'evapotranspiration', 'ET0'],
    definition:
      'The water a well-watered, actively growing grass would lose in a day through evaporation from the soil and transpiration from its leaves, worked out from temperature, humidity, wind and sunshine. A crop uses more or less than this depending on its kind and growth stage.',
  },
  {
    id: 'chill_hours',
    term: 'Chill hours',
    matches: ['chill hours', 'chill hour'],
    definition:
      'The hours between 32 °F and 45 °F in fall and winter. Fruit trees need enough cold to end their winter rest before they bloom normally, and chill hours are the simplest measure of it.',
  },
  {
    id: 'utah_chill_units',
    term: 'Utah chill units',
    matches: ['Utah chill units', 'Utah chill unit', 'chill units'],
    definition:
      'A measure of winter chill for fruit trees that weights each hour by its temperature: cool hours count fully, near-freezing and mild hours count less, and warm hours count against the total.',
  },
  {
    id: 'chill_portions',
    term: 'Chill portions',
    matches: ['chill portions', 'chill portion', 'dynamic model'],
    definition:
      "A measure of winter chill for fruit trees from the Dynamic model. Cold builds up in steps that warm hours can still undo, until each step is locked in as a portion. It handles mild winters better than chill hours, so it's the usual choice where winters swing between cold and warm.",
  },
  {
    id: 'thi',
    term: 'Temperature humidity index (THI)',
    matches: ['temperature humidity index', 'temperature-humidity index', 'THI'],
    definition:
      "A measure of heat stress in livestock from air temperature and humidity. Dairy cows' milk yield begins to fall at a THI of about 68, and stress is commonly counted from 72.",
  },
  {
    id: 'cattle_comfort_index',
    term: 'Cattle comfort index',
    matches: ['cattle comfort index', 'comprehensive climate index'],
    definition:
      "An apparent temperature for cattle: the air temperature adjusted for humidity, wind and sunshine, so it shows heat stress on a sunny, still day and cold stress on a windy one. It's given in degrees, like the air temperature.",
  },
  {
    id: 'planting_tiers',
    term: 'Early, typical and late planting',
    matches: ['typical planting date', 'typical planting', 'planting tier', 'planting tiers'],
    definition:
      "Planting dates we estimate for each location when you haven't given your own: a typical date for the area, and an early and a late one on either side. They come from published planting dates and the area's usual last spring freeze. Set your own planting date for results that fit your field.",
  },
  {
    id: 'leaf_wetness',
    term: 'Hours estimated wet',
    matches: ['hours estimated wet', 'leaf wetness'],
    definition:
      "The hours with relative humidity at or above 90% or with rain, which stand in for the hours a crop's leaves stay wet. Many diseases infect only while leaves are wet, so wet hours drive their models. We estimate them from the weather, since leaf wetness isn't measured across the grid.",
  },
  {
    id: 'observed',
    term: 'Observed weather',
    matches: ['observed weather'],
    definition:
      "Weather for hours and days that have passed, from NOAA's analyses, which combine weather station readings, radar and a short forecast on a 2.5 km grid. The newest hours come from a quicker preliminary analysis and are replaced a few hours later.",
  },
  {
    id: 'forecast',
    term: 'Forecast',
    matches: ['weather forecast'],
    definition:
      "Weather for the coming days, from NOAA's National Blend of Models, corrected against our observed weather. Models run on the forecast to show where a risk is heading, and charts and tables mark forecast days so you can tell them from observed ones.",
  },
  {
    id: 'estimated',
    term: 'Estimated day',
    matches: ['estimated days', 'estimated day'],
    definition:
      'A day whose weather was missing and has been filled in from the days on either side, so a model or running total can carry on across a short gap. Results say how many of their days were estimated. Precipitation is never estimated: a missing day counts as no rain and is reported as missing.',
  },
  {
    id: 'grid_cell',
    term: 'Grid cell',
    matches: ['grid cell', 'grid cells'],
    definition:
      'One square of the grid AgWeather keeps its weather on, about 2.5 km (1.6 miles) on a side. A location takes the values of the cell it is in, so a value describes the cell as a whole rather than one field.',
  },
  {
    id: 'grid_day',
    term: 'Day (midnight to midnight CST)',
    matches: ['grid day', 'Central Standard Time'],
    definition:
      'Each day on AgWeather runs from midnight to midnight Central Standard Time (CST) all year, so in summer it runs from 1 a.m. to 1 a.m. Central Daylight Time. Every cell on a map covers the same hours. For a location, the API can give days on its own clock instead.',
  },
  {
    id: 'model_status',
    term: 'Beta and stable models',
    matches: ['beta model', 'stable model'],
    definition:
      "A model's status. A beta model is new to AgWeather or still being checked, and its results may change as we test it; a stable model has been checked and is in regular use. Any change to a model's results is listed in the changelog on its page.",
  },
  {
    id: 'training_area',
    term: 'Training area',
    matches: ['training area'],
    definition:
      'The area whose fields or weather stations a model was fitted to. Outside it, the model is working beyond what its research tested, so treat its results with more caution there.',
  },
  // --- End of the reference terms ---
]

const byId = new Map(GLOSSARY.map((entry) => [entry.id, entry]))

export function glossaryEntry(id: string): GlossaryEntry {
  const entry = byId.get(id)
  if (!entry) throw new Error(`No glossary entry "${id}"`)
  return entry
}

/** The entry's place on the glossary page (/glossary#id) */
export function glossaryHref(id: string): string {
  return `${routes.glossary()}#${id}`
}

/** The glossary A–Z, grouped by each term's first letter */
export function glossaryByLetter(entries: GlossaryEntry[] = GLOSSARY): { letter: string; entries: GlossaryEntry[] }[] {
  const sorted = [...entries].sort((a, b) => a.term.localeCompare(b.term, 'en', { sensitivity: 'base' }))
  const groups: { letter: string; entries: GlossaryEntry[] }[] = []
  for (const entry of sorted) {
    const letter = entry.term[0].toUpperCase()
    if (groups.at(-1)?.letter !== letter) groups.push({ letter, entries: [] })
    groups.at(-1)!.entries.push(entry)
  }
  return groups
}

/** The entries whose term, wordings or definition contain every word of `query`, in any case */
export function filterGlossary(query: string, entries: GlossaryEntry[] = GLOSSARY): GlossaryEntry[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return entries
  return entries.filter((entry) => {
    const text = [entry.term, ...entry.matches, entry.definition].join(' ').toLowerCase()
    return words.every((word) => text.includes(word))
  })
}

export type Segment = { text: string; entry?: GlossaryEntry }

// Every wording, longest first so "growing degree days" wins over "degree days"
const wordings = GLOSSARY.flatMap((entry) => entry.matches.map((match) => ({ match, entry }))).sort(
  (a, b) => b.match.length - a.match.length,
)
const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const pattern = new RegExp(`\\b(?:${wordings.map(({ match }) => escape(match)).join('|')})\\b`, 'gi')
const abbreviation = (match: string) => match === match.toUpperCase()

/**
 * Splits text into plain runs and glossary terms, marking only each term's first appearance.
 * Pass the same `seen` set for every paragraph in a block, so a term is marked once per block.
 */
export function markTerms(text: string, seen: Set<string> = new Set()): Segment[] {
  const segments: Segment[] = []
  let last = 0
  for (const found of text.matchAll(pattern)) {
    const wording = wordings.find(({ match }) =>
      abbreviation(match) ? match === found[0] : match.toLowerCase() === found[0].toLowerCase(),
    )
    if (!wording || seen.has(wording.entry.id)) continue
    seen.add(wording.entry.id)
    if (found.index > last) segments.push({ text: text.slice(last, found.index) })
    segments.push({ text: found[0], entry: wording.entry })
    last = found.index + found[0].length
  }
  if (last < text.length) segments.push({ text: text.slice(last) })
  return segments
}
