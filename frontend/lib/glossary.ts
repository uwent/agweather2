// Ported from WISP 3 (adapted): app/frontend/lib/glossary.ts
// Terms AgWeather uses, explained where they appear (Term.svelte, GlossaryText.svelte) and, later, on
// the glossary page. Definitions are for growers and consultants: plain words, a sentence or three,
// no more precise than the models are (CLAUDE.md, Writing for the public).

export type GlossaryEntry = {
  id: string
  term: string
  /**
   * Wordings that mark this term in text, matched as whole words. One in capitals (an
   * abbreviation) matches only in capitals; the rest match in any case.
   */
  matches: string[]
  definition: string
}

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
]

const byId = new Map(GLOSSARY.map((entry) => [entry.id, entry]))

export function glossaryEntry(id: string): GlossaryEntry {
  const entry = byId.get(id)
  if (!entry) throw new Error(`No glossary entry "${id}"`)
  return entry
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
