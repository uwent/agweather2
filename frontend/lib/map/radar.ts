// WISP 3: app/frontend/lib/map/radar.ts (adapted: tileAt and tilePixels moved to tiles.ts, which decodes
// without color management, as the data tiles do, and closes the bitmap)
import type { LngLat } from '@/lib/geo'

import { tileAt, tilePixels } from './tiles'

// Radar reflectivity under a point, read from the same Iowa Environmental Mesonet tile the map
// draws: IEM renders its NEXRAD composite (N0Q) with a 256-color palette in which index 1 is −32 dBZ
// and each index after it 0.5 dBZ more (index 0 is no data), so a pixel's color gives its dBZ. The
// palette is IEM's, from the georeferenced composite (data/gis/images/4326/USCOMP/n0q_0.png).

const IEM_TILES = 'https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913'
/** The zoom the value is read at: pixels of about 300 m, finer than the radar's 1 km */
const ZOOM = 9

// prettier-ignore
const N0Q_PALETTE =
  '00000085718f85728f86738d87758b87768b887789897987897a878a7b858b7d848b7e848c7f828d81808d82808e837e' +
  '8f847c8f857c90877b918879918979928b77938d759691539894579b975b9d9a60a09d64a3a068a5a36da8a671aaa976' +
  'adac7ab0af7eb2b283b7b88cbabb90bdbe94bfc199c2c49dc4c7a2c7caa6cacdaaccd0afd2d4b4cfd2b4c9ccb4c6c9b4' +
  'c3c7b4c0c4b4bdc1b4b9beb4b6bbb4b3b9b4b0b6b4adb3b4aab0b4a4abb4a0a8b49da5b49aa2b497a0b4949db4919ab4' +
  '949bb59098b48c95b38892b2808cb07c89af7886ae7483ac7080ab6c7daa6779a96376a85f73a75b70a6576da44f67a2' +
  '4b64a14761a0435e9f415b9e4361a24568a6486faa4a76ae4d7db24f84b6518bbb5699c3599fc75ba6cb5eadcf60b4d4' +
  '62bbd865c2dc67c9e06ad0e46fd6e868d6d759d6b352d6a24bd69043d67e3cd66d35d65b11d51811d11710cd1710c816' +
  '10c4160fbc150fb7140eb3140eaf130eab130da6120da2120d9e110c99110c95100c91100b880f0b840e0a800e0a7c0d' +
  '0a770d09730c096f0c096b0b08660b08620a095e09327308467d085b88076f9207849d0698a806adb205c1bd05d6c704' +
  'ead204ffe200ffd800ffd300ffce00ffc900ffc400ffc000ffbb00ffb600ffb100ffac00ffa700ffa200ff9900ff9400' +
  'ff8f00ff8a00ff8500ff8000ff0000f80000f10000ea0000e30000d50000cd0000c60000bf0000b80000b10000aa0000' +
  'a300009b00009400008d00007f0000780000710000fffffffff5ffffeaffffdfffffd4ffffc9ffffbeffffb3ffff9dff' +
  'ff92ffff75fffc6bfdf960faf656f7f34bf4f040f1ed36efea2bece720e9e10be3b200ffac00fca400f79b00f49300ef' +
  '8800ea8300e87900e27200dd6900db05ecf005ebf005eaf005dde005dce005dbe005cdd005ccd004bdc004bcc004bbc0' +
  '04aeb004adb0049ea0049da0049ca0038e90038d90038c90037e80037d80036f70036e70036d70025f60025e60024f50' +
  '024e50024d50023f40023e40023d40013030012f30012020011f20011e203a67b53a66b53a65b53a64b53a63b53a62b5'

const DBZ_BY_COLOR = new Map<string, number>()
for (let i = 1; i < 256; i++) DBZ_BY_COLOR.set(N0Q_PALETTE.slice(i * 6, i * 6 + 6), -32 + (i - 1) * 0.5)

/** The reflectivity a tile pixel shows, or null for none (transparent, or not a palette color) */
export function reflectivityForColor(r: number, g: number, b: number, alpha: number): number | null {
  if (alpha === 0) return null
  const hex = [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')
  return DBZ_BY_COLOR.get(hex) ?? null
}

// The last few tiles read, so moving the pointer around one area doesn't fetch it again
const tiles = new Map<string, Promise<ImageData>>()
const KEPT = 12

/** The reflectivity at a point (dBZ), or null where the radar shows nothing */
export async function reflectivityAt(at: LngLat, signal?: AbortSignal): Promise<number | null> {
  const { z, x, y, px, py } = tileAt(at, ZOOM)
  // IEM refreshes the composite every 5 minutes; tiles from the same 5 minutes are the same
  const url = `${IEM_TILES}/${z}/${x}/${y}.png?t=${Math.floor(Date.now() / 300_000)}`
  if (!tiles.has(url)) {
    const loading = tilePixels(url)
    loading.catch(() => tiles.delete(url))
    tiles.set(url, loading)
    if (tiles.size > KEPT) tiles.delete(tiles.keys().next().value!)
  }
  const pixels = await tiles.get(url)!
  signal?.throwIfAborted()
  const i = (py * pixels.width + px) * 4
  return reflectivityForColor(pixels.data[i], pixels.data[i + 1], pixels.data[i + 2], pixels.data[i + 3])
}
