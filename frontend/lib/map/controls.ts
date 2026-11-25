// WISP 3: app/frontend/lib/map/controls.ts (copied)
import type { IControl } from 'maplibre-gl'

/** A MapLibre control with one button, styled like the built-in ones (e.g. "fit all systems") */
export class ButtonControl implements IControl {
  private container?: HTMLDivElement

  constructor(
    private readonly label: string,
    private readonly icon: string,
    private readonly onclick: () => void,
  ) {}

  onAdd() {
    this.container = document.createElement('div')
    this.container.className = 'maplibregl-ctrl maplibregl-ctrl-group'
    const button = document.createElement('button')
    button.type = 'button'
    button.title = this.label
    button.setAttribute('aria-label', this.label)
    button.innerHTML = this.icon
    button.style.display = 'flex'
    button.style.alignItems = 'center'
    button.style.justifyContent = 'center'
    button.addEventListener('click', this.onclick)
    this.container.append(button)
    return this.container
  }

  onRemove() {
    this.container?.remove()
  }
}

/** A system framed by corners: fit every system in view */
export const FIT_ICON =
  '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
  '<path d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4"/><circle cx="12" cy="12" r="3.5"/></svg>'
