// Ported from WISP 3 (adapted): app/frontend/lib/searchHighlight.ts
import type { Attachment } from 'svelte/attachments'

// Marks what a search box matched with the CSS Custom Highlight API: the text of each element
// marked data-search-text (names, crops) in the page's <main>, so a match in a note isn't
// marked. Styled by ::highlight(search) in application.css.
// Browsers without the API (and jsdom) mark nothing.

/** The query as matched: trimmed and lower case; '' matches everything (WISP 3's lib/search.ts) */
export const searchText = (query: string) => query.trim().toLowerCase()

export const HIGHLIGHT = 'search'

/** Ranges over each place text occurs in the marked elements under root */
export function matchRanges(root: ParentNode, text: string): Range[] {
  if (!text) return []
  const ranges: Range[] = []
  // Matched in the text as it is (lowercasing can change a string's length: "İ" is two characters)
  const pattern = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
  for (const element of root.querySelectorAll('[data-search-text]')) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      for (const match of (node.nodeValue ?? '').matchAll(pattern)) {
        if (!match[0]) continue
        const range = document.createRange()
        range.setStart(node, match.index)
        range.setEnd(node, match.index + match[0].length)
        ranges.push(range)
      }
    }
  }
  return ranges
}

/**
 * {@attach searchHighlight(() => query)} on the search box (SearchFilter): marks the matches in
 * its page, again as the query or the page changes, and clears them when it's removed
 */
export function searchHighlight(query: () => string): Attachment<HTMLElement> {
  return (box) => {
    if (typeof CSS === 'undefined' || !('highlights' in CSS)) return
    const root = box.closest('main') ?? document.body
    const text = searchText(query())
    const mark = () => {
      const ranges = matchRanges(root, text)
      if (ranges.length) CSS.highlights.set(HIGHLIGHT, new Highlight(...ranges))
      else CSS.highlights.delete(HIGHLIGHT)
    }
    mark()
    if (!text) return
    // The list redraws as filters change or the weather lands: marked again once a frame at most
    let frame = 0
    const observer = new MutationObserver(() => {
      if (!frame) frame = requestAnimationFrame(() => ((frame = 0), mark()))
    })
    observer.observe(root, { subtree: true, childList: true, characterData: true })
    return () => {
      observer.disconnect()
      cancelAnimationFrame(frame)
      CSS.highlights.delete(HIGHLIGHT)
    }
  }
}
