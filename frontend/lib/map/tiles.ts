// Web map tiles read back in the page: which tile and pixel lie under a point, and a tile's pixels as stored.
// Shared by the API's data tiles (dataTiles.ts), whose bytes pack values, and IEM's radar tiles (radar.ts), whose
// colors index a palette: both need the bytes exactly as the PNG holds them.

import type { LngLat } from '@/lib/geo'

/** The web map tile at a zoom containing a point, and the point's pixel in it */
export function tileAt([lng, lat]: LngLat, zoom: number) {
  const scale = 2 ** zoom * 256
  const x = ((lng + 180) / 360) * scale
  const sin = Math.sin((lat * Math.PI) / 180)
  const y = (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * scale
  return { z: zoom, x: Math.floor(x / 256), y: Math.floor(y / 256), px: Math.floor(x % 256), py: Math.floor(y % 256) }
}

/** A tile's pixels, decoded without color management or premultiplied alpha (the bytes are read, not shown) */
export async function tilePixels(url: string, signal?: AbortSignal): Promise<ImageData> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`Tile ${url}: ${response.status}`)
  const bitmap = await createImageBitmap(await response.blob(), {
    premultiplyAlpha: 'none',
    colorSpaceConversion: 'none',
  })
  const canvas = document.createElement('canvas')
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  const context = canvas.getContext('2d', { willReadFrequently: true })!
  context.drawImage(bitmap, 0, 0)
  bitmap.close()
  return context.getImageData(0, 0, canvas.width, canvas.height)
}
