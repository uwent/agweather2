// Ported from WISP 3 (adapted): app/frontend/lib/glossary.test.ts
import { describe, expect, it } from 'vitest'

import { filterGlossary, GLOSSARY, glossaryByLetter, glossaryEntry, glossaryHref, markTerms } from './glossary'

const marked = (text: string, seen?: Set<string>) =>
  markTerms(text, seen)
    .map((segment) => (segment.entry ? `[${segment.text}:${segment.entry.id}]` : segment.text))
    .join('')

describe('markTerms', () => {
  it('marks each term once, preferring the longest wording', () => {
    expect(marked('Growing degree days add up; degree days from May 1 too.')).toBe(
      '[Growing degree days:growing_degree_days] add up; degree days from May 1 too.',
    )
  })

  it('counts every wording of a term as one term', () => {
    expect(marked('Disease severity values (DSV): a DSV of 3 is high.')).toBe(
      '[Disease severity values:dsv] (DSV): a DSV of 3 is high.',
    )
  })

  it('matches abbreviations only in capitals and only as whole words', () => {
    expect(marked('The gdd column; GDD since biofix.')).toBe(
      'The gdd column; [GDD:growing_degree_days] since [biofix:biofix].',
    )
    expect(marked('GDDX and DSVR are not terms')).toBe('GDDX and DSVR are not terms')
  })

  it('matches phrases in any case', () => {
    expect(marked('Base Threshold, then the upper threshold.')).toBe(
      '[Base Threshold:base_threshold], then the [upper threshold:upper_threshold].',
    )
  })

  it('shares what it has marked across the paragraphs of a block', () => {
    const seen = new Set<string>()
    expect(marked('From emergence.', seen)).toBe('From [emergence:emergence].')
    expect(marked('Since emergence.', seen)).toBe('Since emergence.')
  })

  it('leaves text without terms as one run', () => {
    expect(markTerms('Nothing to see')).toEqual([{ text: 'Nothing to see' }])
    expect(markTerms('')).toEqual([])
  })
})

describe('glossary', () => {
  it('has unique ids and wordings', () => {
    expect(new Set(GLOSSARY.map((entry) => entry.id)).size).toBe(GLOSSARY.length)
    const wordings = GLOSSARY.flatMap((entry) => entry.matches.map((match) => match.toLowerCase()))
    expect(new Set(wordings).size).toBe(wordings.length)
  })

  it('looks entries up by id, and fails loudly on a typo', () => {
    expect(glossaryEntry('p_days').term).toBe('Physiological days (P-days)')
    expect(() => glossaryEntry('pdays')).toThrow('No glossary entry "pdays"')
  })

  it('writes definitions for the public: whole sentences, no exclamation marks', () => {
    for (const entry of GLOSSARY) {
      expect(entry.definition).toMatch(/^[A-Z].*\.$/)
      expect(entry.definition).not.toContain('!')
    }
  })
})

describe('the glossary page’s helpers', () => {
  it('links an entry to its anchor on the glossary page', () => {
    expect(glossaryHref('biofix')).toBe('/glossary#biofix')
  })

  it('groups the terms A–Z by first letter, ignoring case', () => {
    const groups = glossaryByLetter([
      { id: 'b', term: 'beta', matches: [], definition: '' },
      { id: 'a2', term: 'Apple', matches: [], definition: '' },
      { id: 'a1', term: 'apex', matches: [], definition: '' },
    ])
    expect(groups.map((g) => [g.letter, g.entries.map((e) => e.id)])).toEqual([
      ['A', ['a1', 'a2']],
      ['B', ['b']],
    ])
  })

  it('filters by every word, in the term, its wordings or its definition', () => {
    const ids = (query: string) => filterGlossary(query).map((e) => e.id)
    expect(ids('')).toHaveLength(GLOSSARY.length)
    expect(ids('ET0')).toEqual(['et0'])
    expect(ids('dairy MILK')).toEqual(['thi'])
    expect(ids('dairy nothing-like-this')).toEqual([])
  })

  it('has the reference terms the glossary page promises', () => {
    const ids = ['risk_level', 'et0', 'chill_portions', 'thi', 'planting_tiers', 'observed', 'forecast', 'estimated']
    for (const id of [...ids, 'grid_cell', 'grid_day']) expect(glossaryEntry(id).definition).not.toBe('')
  })
})
