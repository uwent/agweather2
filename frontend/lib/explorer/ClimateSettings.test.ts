import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import { defaults } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import ClimateSettings from './ClimateSettings.svelte'
import { type ExplorerView, VIEW_FIELDS } from './view'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })

function settings(id: string, shown: Partial<ExplorerView> = {}) {
  const onchange = vi.fn()
  render(ClimateSettings, {
    view: view({ layer: id, ...shown }),
    layer: layer(id),
    layers: LAYERS,
    today: '2026-11-25',
    onchange,
  })
  return onchange
}

const choices = (name: string) =>
  screen.getAllByRole('radio').filter((r) => r.getAttribute('name') === name) as HTMLInputElement[]

describe('ClimateSettings', () => {
  it('offers Off, Normal and Departure on a daily layer, with the period once one is on', async () => {
    const onchange = settings('air_temperature_min')
    expect(choices('climate-kind').map((r) => r.value)).toEqual(['off', 'normal', 'departure'])
    expect(screen.getByRole('radio', { name: 'Off' })).toBeChecked()
    expect(screen.queryByText(/Normal from/)).not.toBeInTheDocument()
    await fireEvent.click(screen.getByRole('radio', { name: 'Departure' }))
    expect(onchange).toHaveBeenLastCalledWith({ climate: 'departure' })
  })

  it('shows the period, labelled with its years, and what the map now shows', async () => {
    const onchange = settings('precipitation_total', { climate: 'percentile' })
    expect(choices('climate-kind').map((r) => r.value)).toEqual(['off', 'normal', 'departure', 'percentile'])
    expect(screen.getByRole('radio', { name: 'Percentile' })).toBeChecked()
    // Percentiles are kept over 30 or 10 years
    expect(choices('climate-period').map((r) => r.value)).toEqual(['last30', 'last10'])
    expect(screen.getByRole('radio', { name: '10 years (2016–2025)' })).toBeInTheDocument()
    expect(screen.getByTestId('climate-words')).toHaveTextContent('where this year’s total ranks')
    await fireEvent.click(screen.getByRole('radio', { name: '10 years (2016–2025)' }))
    expect(onchange).toHaveBeenLastCalledWith({ period: 'last10' })
  })

  it('disables the percentile over 5 years', () => {
    settings('precipitation_total', { climate: 'departure', period: 'last5' })
    expect(screen.getByRole('radio', { name: 'Percentile' })).toBeDisabled()
    expect(screen.getByRole('radio', { name: 'Departure' })).toBeChecked()
  })

  it('says which degree-day settings have normals when the chosen one hasn’t', () => {
    settings('degree_days', { dd: 'average_50', span: 'season', climate: 'departure' })
    expect(choices('climate-kind').map((r) => r.value)).toEqual(['off'])
    expect(screen.getByRole('radio', { name: 'Off' })).toBeChecked()
    expect(
      screen.getByText(/Normals are kept for these degree days: single sine from a base of 32/),
    ).toBeInTheDocument()
  })

  it('gives the freeze maps a threshold and a period, and no comparison', async () => {
    const onchange = settings('freeze_chance')
    expect(screen.queryByRole('radio', { name: 'Departure' })).not.toBeInTheDocument()
    expect(choices('climate-threshold').map((r) => r.value)).toEqual(['32', '28', '24'])
    expect(screen.getByRole('radio', { name: 'Frost (32 °F)' })).toBeChecked()
    await fireEvent.click(screen.getByRole('radio', { name: 'Hard freeze (28 °F)' }))
    expect(onchange).toHaveBeenLastCalledWith({ threshold: 28 })
    expect(choices('climate-period').map((r) => r.value)).toEqual(['last30', 'last10', 'last5'])
  })

  it('shows nothing for a map without normals', () => {
    settings('air_temperature_hourly')
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
})
