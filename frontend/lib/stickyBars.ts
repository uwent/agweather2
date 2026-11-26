// Ported from WISP 3: app/frontend/lib/stickyBars.ts
// Bars pinned to the top of the window (the impersonation bar, a field page's time travel bar)
// publish their heights as CSS variables, so other sticky elements (`top-sticky` in
// application.css, e.g. the weather charts' range bar) stop below them instead of sliding under.

export type StickyBar = '--app-bar-h' | '--page-bar-h'

/** An attachment that keeps `name` on the document root equal to the element's height while it's mounted */
export function stickyHeight(name: StickyBar) {
  return (element: HTMLElement) => {
    const root = document.documentElement
    const set = () => root.style.setProperty(name, `${element.offsetHeight}px`)
    set()
    const observer = new ResizeObserver(set)
    observer.observe(element)
    return () => {
      observer.disconnect()
      root.style.removeProperty(name)
    }
  }
}
