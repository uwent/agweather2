// STUB: replaced by the sites store agent's file at merge

/** A site's key: its coordinates to 4 decimals (~11 m), as its URL segment (F1) */
export function siteKey(lat: number, lng: number): string {
  const short = (value: number) => String(Number(value.toFixed(4)))
  return `${short(lat)},${short(lng)}`
}

/** The site page's path for a key */
export function siteUrl(key: string): string {
  return `/sites/${key}`
}
