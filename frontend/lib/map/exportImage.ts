// late-blight-db: src/lib/map/export-image.ts (adapted: a data map's legend (a color bar with ticks, or a swatch per
// level, and "No data"), the map's date and data credit, the reader's saved sites as labels, and the layout's
// arithmetic split out of the drawing so it can be tested without a canvas)

/**
 * "Save image": the map, the reader's saved sites in view, the legend, the title and the credits composed on one
 * canvas, as a PNG. Everything is redrawn with the Canvas 2D API from data (the WebGL frame captured by DataMap for
 * the map, the legend from its spec) rather than rasterizing the page, so the image matches the screen without a
 * screenshot library.
 */
import { leaderEnd, type LabelLayout, type Rect } from './labels'

export type ImageColors = {
  background: string
  foreground: string
  muted: string
  border: string
  card: string
}

/** A data map's legend as the image draws it, in the reader's units */
export type ImageLegend = {
  /** The layer's name, with its unit */
  title: string
  /** A continuous bar's colors low to high, with its ticks placed along it (0–1) */
  bar: { colors: string[]; ticks: { at: number; label: string }[] } | null
  /** A swatch per level, named */
  levels: { color: string; label: string }[]
  /** The swatch for "None" (a first or last day not found), when the map can show it */
  none: string | null
}

export type ImageSpec = {
  /** The map frame, captured at `scale` × its CSS size */
  map: CanvasImageSource
  cssWidth: number
  cssHeight: number
  scale: number
  labels: LabelLayout[]
  legend: ImageLegend
  title: string
  /** The date and settings, as the title chip shows them */
  subtitle: string
  /** How far the data reaches ("Observed through Nov 24, 2026 · forecast to Dec 6, 2026"), or '' */
  through: string
  /** Credits on the left (the service) and the right (the data's source, the basemap's, the site) */
  credit: string
  sources: string[]
  colors: ImageColors
  font: string
}

export const LEGEND_WIDTH = 240
export const LEGEND_MARGIN = 8
const PAD = 10
const ROW = 18
const SWATCH = 12
const FOOTER_LINE = 16

/** Text widths in CSS pixels, at a font size; a canvas's in the page, a stand-in in tests */
export type Measure = (text: string, size: number) => number

/** The title band's height: the title, the subtitle and, when there is one, the data's reach */
export const titleHeight = (through: string) => (through ? 82 : 64)

/** Where the legend's parts go, relative to its top left, and its size */
export function legendLayout(legend: ImageLegend, measure: Measure) {
  const width = LEGEND_WIDTH
  let y = PAD + 6 // the title's middle
  const titleY = y
  y += 12
  let bar: { y: number; ticksY: number } | null = null
  const swatches: { x: number; y: number; color: string; label: string; hatched?: boolean }[] = []
  // Swatches flow left to right and wrap, as on screen
  let x = PAD
  const flow = (color: string, label: string, hatched = false) => {
    const w = SWATCH + 4 + measure(label, 11) + 12
    if (x > PAD && x + w > width - PAD) {
      x = PAD
      y += ROW
    }
    swatches.push({ x, y, color, label, hatched })
    x += w
  }
  if (legend.bar) {
    bar = { y: y + 2, ticksY: y + 2 + SWATCH + 8 }
    y += SWATCH + 26
  } else {
    y += 4
    for (const level of legend.levels) flow(level.color, level.label)
    x = PAD
    y += ROW
  }
  if (legend.none) flow(legend.none, 'None')
  flow('', 'No data', true)
  const height = y + ROW / 2 + PAD - 4
  return { width, height, titleY, bar, swatches }
}

/** The legend's box on the map, at its lower left as on screen (labels are placed to avoid it) */
export function legendBox(legend: ImageLegend, cssHeight: number, measure: Measure): Rect {
  const { width, height } = legendLayout(legend, measure)
  return { x: LEGEND_MARGIN, y: cssHeight - LEGEND_MARGIN - height, w: width, h: height }
}

/** The footer's lines: the credit and the sources on one line where they fit, else the sources below it, wrapped
 * (never cut: the basemap's credit must show whole) */
export function footerLines(credit: string, sources: string[], width: number, measure: Measure) {
  const right = sources.filter(Boolean).join('  ·  ')
  const oneLine = measure(credit, 12) + 24 + measure(right, 11) + 32 <= width
  const lines = oneLine ? [] : wrapText(right, width - 32, 11, measure)
  return { right, oneLine, lines, height: (1 + lines.length) * FOOTER_LINE + 14 }
}

/** Text broken at spaces into lines of at most a width (a word longer than the width gets a line of its own) */
export function wrapText(text: string, width: number, size: number, measure: Measure): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(' ')) {
    const next = line ? `${line} ${word}` : word
    if (line && measure(next, size) > width) {
      lines.push(line)
      line = word
    } else line = next
  }
  if (line) lines.push(line)
  return lines
}

/** Text cut to a width, with an ellipsis */
export function fitText(text: string, width: number, size: number, measure: Measure): string {
  if (measure(text, size) <= width) return text
  let cut = text
  while (cut.length > 1 && measure(`${cut}…`, size) > width) cut = cut.slice(0, -1)
  return `${cut.trimEnd()}…`
}

/** The PNG's name: the layer and the map's date ("agweather-air_temperature_max-2026-11-24.png") */
export function imageFileName(layer: string, date: string): string {
  const safe = (text: string) => text.replace(/\.\./g, '_to_').replace(/[^A-Za-z0-9_-]+/g, '-')
  return `agweather-${safe(layer)}-${safe(date)}.png`
}

export function composeImage(spec: ImageSpec, canvas = document.createElement('canvas')): HTMLCanvasElement {
  const { cssWidth: w, cssHeight: h, scale, colors, font } = spec
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas 2D is unavailable')
  const measure: Measure = (text, size) => {
    ctx.font = `400 ${size}px ${font}`
    return ctx.measureText(text).width
  }
  const top = titleHeight(spec.through)
  const footer = footerLines(spec.credit, spec.sources, w, measure)
  const height = top + h + footer.height

  canvas.width = Math.round(w * scale)
  canvas.height = Math.round(height * scale)
  ctx.scale(scale, scale)

  ctx.fillStyle = colors.background
  ctx.fillRect(0, 0, w, height)

  // The title band
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = colors.foreground
  ctx.font = `600 20px ${font}`
  ctx.fillText(
    fitText(spec.title, w - 32, 20, (t) => ctx.measureText(t).width),
    16,
    30,
  )
  ctx.font = `400 14px ${font}`
  ctx.fillText(fitText(spec.subtitle, w - 32, 14, measure), 16, 51)
  if (spec.through) {
    ctx.fillStyle = colors.muted
    ctx.font = `400 12px ${font}`
    ctx.fillText(fitText(spec.through, w - 32, 12, measure), 16, 70)
  }

  // The map
  ctx.drawImage(spec.map, 0, top, w, h)
  ctx.save()
  ctx.translate(0, top)
  ctx.beginPath()
  ctx.rect(0, 0, w, h)
  ctx.clip()
  drawLabels(ctx, spec)
  drawLegend(ctx, spec, measure)
  ctx.restore()
  ctx.strokeStyle = colors.border
  ctx.lineWidth = 1
  ctx.strokeRect(0.5, top + 0.5, w - 1, h - 1)

  // The footer: the service on the left, the sources on the right (or below, on a narrow map)
  const footerY = top + h
  ctx.fillStyle = colors.foreground
  ctx.font = `600 12px ${font}`
  ctx.textBaseline = 'middle'
  ctx.fillText(spec.credit, 16, footerY + 7 + FOOTER_LINE / 2)
  ctx.fillStyle = colors.muted
  ctx.font = `400 11px ${font}`
  if (footer.oneLine) {
    ctx.textAlign = 'right'
    ctx.fillText(footer.right, w - 16, footerY + 7 + FOOTER_LINE / 2)
    ctx.textAlign = 'left'
  } else {
    footer.lines.forEach((line, i) => ctx.fillText(line, 16, footerY + 7 + FOOTER_LINE * (i + 1.5)))
  }
  return canvas
}

function drawLabels(ctx: CanvasRenderingContext2D, spec: ImageSpec) {
  const { colors, font } = spec
  for (const { anchor, box } of spec.labels) {
    const end = leaderEnd(anchor, box)
    if (end) {
      ctx.strokeStyle = colors.foreground
      ctx.globalAlpha = 0.7
      ctx.lineWidth = 1.25
      ctx.beginPath()
      ctx.moveTo(anchor.x, anchor.y)
      ctx.lineTo(end.x, end.y)
      ctx.stroke()
      ctx.globalAlpha = 1
    }
    ctx.beginPath()
    ctx.arc(anchor.x, anchor.y, 3.5, 0, Math.PI * 2)
    ctx.fillStyle = colors.foreground
    ctx.fill()
    ctx.lineWidth = 1.5
    ctx.strokeStyle = colors.background
    ctx.stroke()
  }
  // Boxes after every line, so no leader crosses another site's label
  for (const { text, box } of spec.labels) {
    ctx.beginPath()
    ctx.roundRect(box.x, box.y, box.w, box.h, 6)
    ctx.fillStyle = colors.card
    ctx.fill()
    ctx.lineWidth = 1
    ctx.strokeStyle = colors.border
    ctx.stroke()
    ctx.fillStyle = colors.foreground
    ctx.font = `500 12px ${font}`
    ctx.textBaseline = 'middle'
    ctx.textAlign = 'center'
    ctx.fillText(text, box.x + box.w / 2, box.y + box.h / 2 + 0.5)
    ctx.textAlign = 'left'
  }
}

function drawLegend(ctx: CanvasRenderingContext2D, spec: ImageSpec, measure: Measure) {
  const { colors, font, legend } = spec
  const layout = legendLayout(legend, measure)
  const x = LEGEND_MARGIN
  const y = spec.cssHeight - LEGEND_MARGIN - layout.height

  ctx.beginPath()
  ctx.roundRect(x, y, layout.width, layout.height, 6)
  ctx.fillStyle = colors.card
  ctx.globalAlpha = 0.94
  ctx.fill()
  ctx.globalAlpha = 1
  ctx.strokeStyle = colors.border
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.textBaseline = 'middle'
  ctx.fillStyle = colors.foreground
  ctx.font = `600 12px ${font}`
  ctx.fillText(
    fitText(legend.title, layout.width - 2 * PAD, 12, (t) => ctx.measureText(t).width),
    x + PAD,
    y + layout.titleY,
  )

  if (legend.bar && layout.bar) {
    const barWidth = layout.width - 2 * PAD
    const gradient = ctx.createLinearGradient(x + PAD, 0, x + PAD + barWidth, 0)
    const stops = legend.bar.colors
    stops.forEach((color, i) => gradient.addColorStop(stops.length === 1 ? 0 : i / (stops.length - 1), color))
    ctx.fillStyle = gradient
    ctx.fillRect(x + PAD, y + layout.bar.y, barWidth, SWATCH)
    ctx.strokeStyle = colors.border
    ctx.strokeRect(x + PAD + 0.5, y + layout.bar.y + 0.5, barWidth - 1, SWATCH - 1)
    ctx.fillStyle = colors.foreground
    ctx.font = `400 11px ${font}`
    for (const tick of legend.bar.ticks) {
      ctx.textAlign = tick.at < 0.05 ? 'left' : tick.at > 0.95 ? 'right' : 'center'
      ctx.fillText(tick.label, x + PAD + tick.at * barWidth, y + layout.bar.ticksY)
    }
    ctx.textAlign = 'left'
  }

  ctx.font = `400 11px ${font}`
  for (const swatch of layout.swatches) {
    const sx = x + swatch.x
    const sy = y + swatch.y - SWATCH / 2
    if (swatch.hatched) {
      // Missing cells are drawn clear, so the swatch is hatching over nothing, as on screen
      ctx.save()
      ctx.beginPath()
      ctx.rect(sx, sy, SWATCH, SWATCH)
      ctx.clip()
      ctx.strokeStyle = colors.muted
      ctx.lineWidth = 1
      for (let d = -SWATCH; d < SWATCH * 2; d += 3) {
        ctx.beginPath()
        ctx.moveTo(sx + d, sy + SWATCH)
        ctx.lineTo(sx + d + SWATCH, sy)
        ctx.stroke()
      }
      ctx.restore()
    } else {
      ctx.fillStyle = swatch.color
      ctx.fillRect(sx, sy, SWATCH, SWATCH)
    }
    ctx.strokeStyle = colors.border
    ctx.strokeRect(sx + 0.5, sy + 0.5, SWATCH - 1, SWATCH - 1)
    ctx.fillStyle = colors.foreground
    ctx.fillText(swatch.label, sx + SWATCH + 4, y + swatch.y)
  }
}

/** Basemap credits from MapLibre's attribution control, as plain text */
export function attributionText(html: string[]): string {
  const text = html
    .map((h) =>
      h
        .replace(/<[^>]*>/g, ' ')
        .replace(/&copy;/g, '©')
        .replace(/&amp;/g, '&')
        .replace(/\s+/g, ' ')
        .trim(),
    )
    .filter(Boolean)
  return [...new Set(text)].join(' ')
}

/** A color token (an oklch() value) as rgb, which a canvas gradient takes everywhere */
export function resolveColor(token: string, element: Element = document.documentElement): string {
  const value = getComputedStyle(element).getPropertyValue(token).trim()
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx || !value) return value || '#888888'
  ctx.fillStyle = value
  ctx.fillRect(0, 0, 1, 1)
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
  return `rgb(${r}, ${g}, ${b})`
}

export function downloadCanvas(canvas: HTMLCanvasElement, fileName: string): Promise<void> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) return reject(new Error('Your browser could not make the image.'))
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.append(a)
      a.click()
      a.remove()
      // Give the download a moment to start before revoking
      setTimeout(() => URL.revokeObjectURL(url), 10_000)
      resolve()
    }, 'image/png')
  })
}
