// Light/dark theme. The system setting applies unless the user picked the other one with the
// toggle, which sets data-theme on <html> and remembers it in this browser (an inline script in
// the layout applies it before the page paints). Picking the system's own theme clears the override.

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'agweather-theme'
const CHANGE_EVENT = 'agweather:themechange'
const systemQuery = () => matchMedia('(prefers-color-scheme: dark)')

export const systemTheme = (): Theme => (systemQuery().matches ? 'dark' : 'light')

export function currentTheme(): Theme {
  const chosen = document.documentElement.dataset.theme
  return chosen === 'light' || chosen === 'dark' ? chosen : systemTheme()
}

export function setTheme(theme: Theme) {
  const root = document.documentElement
  const override = theme !== systemTheme()
  if (override) root.dataset.theme = theme
  else delete root.dataset.theme
  try {
    if (override) localStorage.setItem(STORAGE_KEY, theme)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage blocked (private mode): the choice lasts for this page only
  }
  dispatchEvent(new Event(CHANGE_EVENT))
}

/** Calls back when the theme changes, by the toggle or the system setting; returns an unsubscribe */
export function onThemeChange(callback: () => void): () => void {
  const query = systemQuery()
  query.addEventListener('change', callback)
  addEventListener(CHANGE_EVENT, callback)
  return () => {
    query.removeEventListener('change', callback)
    removeEventListener(CHANGE_EVENT, callback)
  }
}
