// Settings remembered in this browser (a collapsed row, a chosen order), or for this tab's session
// (setup's last choices). Storage can be blocked (a private window, a browser setting) or hold
// anything, so reading and writing never throw: a setting that can't be read is undefined, and one
// that can't be saved lasts for this page only.

type Area = 'local' | 'session'
const storage = (area: Area): Storage => (area === 'session' ? sessionStorage : localStorage)

/** What's saved under key (JSON), or undefined if nothing is or storage is blocked. Text saved
 * before settings were JSON ("name", "off") comes back as that string. */
export function readStored(key: string, area: Area = 'local'): unknown {
  let text: string | null
  try {
    text = storage(area).getItem(key)
  } catch {
    return undefined
  }
  if (text === null) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

/** Saves value under key as JSON; false if storage is blocked */
export function writeStored(key: string, value: unknown, area: Area = 'local'): boolean {
  try {
    storage(area).setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

/** Removes what's saved under key; nothing happens if storage is blocked */
export function removeStored(key: string, area: Area = 'local'): void {
  try {
    storage(area).removeItem(key)
  } catch {
    // Blocked: there's nothing to remove
  }
}
