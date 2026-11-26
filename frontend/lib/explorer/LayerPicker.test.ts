import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import crops from '@/test/fixtures/crops.json'
import layers from '@/test/fixtures/layers.json'
import models from '@/test/fixtures/models.json'
import presets from '@/test/fixtures/presets.json'
import { defaults } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import type { CropSummary, DegreeDayPreset, ModelSummary } from './catalog'
import LayerPicker from './LayerPicker.svelte'
import { type ExplorerView, VIEW_FIELDS } from './view'

const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })

function picker(shown: Partial<ExplorerView>) {
  const onchange = vi.fn()
  render(LayerPicker, {
    view: view(shown),
    layers: layers.data as LayerInfo[],
    models: models.data as ModelSummary[],
    crops: crops.data as CropSummary[],
    presets: presets.data as DegreeDayPreset[],
    onchange,
  })
  return onchange
}

describe('LayerPicker', () => {
  it('opens on the shown layer’s tab and picks a weather layer from its select', async () => {
    const onchange = picker({ layer: 'air_temperature_min' })
    expect(screen.getByRole('radio', { name: 'Weather' })).toBeChecked()
    const select = screen.getByRole('combobox', { name: 'Weather' })
    expect(select).toHaveValue('air_temperature_min')
    await fireEvent.change(select, { target: { value: 'air_temperature_max' } })
    expect(onchange).toHaveBeenCalledWith({ layer: 'air_temperature_max', output: null })
  })

  it('finds a map by the words of its name', async () => {
    const onchange = picker({ layer: 'air_temperature_min' })
    await fireEvent.input(screen.getByRole('searchbox', { name: 'Find a map' }), { target: { value: 'tar spot' } })
    const results = screen.getByRole('list')
    await fireEvent.click(within(results).getAllByRole('button')[0])
    expect(onchange).toHaveBeenCalledWith(expect.objectContaining({ layer: 'tar-spot' }))
  })

  it('lists a crop’s models, the map’s crop first in a shared link, and those without a map dimmed', async () => {
    const onchange = picker({ layer: 'late-blight-dsv' })
    expect(screen.getByRole('radio', { name: 'Crops and pests' })).toBeChecked()
    expect(screen.getByRole('combobox', { name: 'Crop' })).toHaveValue('potato')
    expect(screen.getByRole('radio', { name: /Late blight/ })).toBeChecked()
    await fireEvent.change(screen.getByRole('combobox', { name: 'Crop' }), { target: { value: 'corn' } })
    expect(onchange).toHaveBeenCalledWith({ crop: 'corn' })
  })

  it('switches to the degree-day builder', async () => {
    picker({ layer: 'air_temperature_min' })
    await fireEvent.click(screen.getByRole('radio', { name: 'Degree days' }))
    expect(screen.getByRole('radio', { name: 'Degree days' })).toBeChecked()
    expect(screen.queryByRole('combobox', { name: 'Weather' })).not.toBeInTheDocument()
  })

  it('lists the freeze maps in a Climate group of the daily weather', async () => {
    const onchange = picker({ layer: 'freeze_chance' })
    expect(screen.getByRole('radio', { name: 'Weather' })).toBeChecked()
    const select = screen.getByRole('combobox', { name: 'Weather' })
    expect(select).toHaveValue('freeze_chance')
    const climate = select.querySelector('optgroup[label="Climate"]')!
    expect([...climate.querySelectorAll('option')].map((o) => o.textContent)).toEqual([
      'Chance of a freeze',
      'Freeze dates and season length',
    ])
    await fireEvent.change(select, { target: { value: 'freeze_dates' } })
    expect(onchange).toHaveBeenCalledWith({ layer: 'freeze_dates', output: null })
  })
})
