// Ported from WISP 3 (adapted): app/frontend/lib/searchHighlight.test.ts
import { describe, expect, it } from 'vitest'

import { matchRanges } from './searchHighlight'

describe('matchRanges', () => {
  it('covers each match in the marked text only, in any case', () => {
    const root = document.createElement('div')
    root.innerHTML =
      '<h4>Site: <span data-search-text>Field station</span></h4>' +
      '<p data-search-text>Field corn <b>(field)</b></p>' +
      '<p>Scout this field by Monday</p>'
    const ranges = matchRanges(root, 'field')
    expect(ranges.map((range) => range.toString())).toEqual(['Field', 'Field', 'field'])
    expect(ranges.map((range) => range.startContainer.parentElement!.tagName)).toEqual(['SPAN', 'P', 'B'])
  })

  it('marks nothing without a query', () => {
    const root = document.createElement('div')
    root.innerHTML = '<span data-search-text>North</span>'
    expect(matchRanges(root, '')).toEqual([])
  })
})

describe('matchRanges with text whose lower case is longer', () => {
  it('places each range in the text as it is', () => {
    const root = document.createElement('div')
    root.innerHTML = '<span data-search-text>İstanbul farm</span>'
    expect(matchRanges(root, 'farm').map((range) => range.toString())).toEqual(['farm'])
  })
})
