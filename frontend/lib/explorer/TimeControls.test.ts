import { fireEvent, render, screen } from '@testing-library/svelte'
import { describe, expect, it, vi } from 'vitest'

import layers from '@/test/fixtures/layers.json'
import { defaults } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import TimeControls from './TimeControls.svelte'
import { addDays } from '@/lib/dates'
import { type ExplorerView, VIEW_FIELDS } from './view'

const LAYERS = layers.data as LayerInfo[]
const layer = (id: string) => LAYERS.find((l) => l.id === id)!
const view = (changes: Partial<ExplorerView> = {}): ExplorerView => ({ ...defaults(VIEW_FIELDS), ...changes })

function controls(id: string, shown: Partial<ExplorerView>) {
  const onchange = vi.fn()
  render(TimeControls, { view: view({ layer: id, ...shown }), layer: layer(id), today: '2026-11-25', onchange })
  return onchange
}

describe('TimeControls', () => {
  it('steps a day back and forward, and labels a forecast day', async () => {
    const daily = layer('air_temperature_min')
    const last = daily.range.last!.slice(0, 10)
    const onchange = controls(daily.id, { date: last })
    await fireEvent.click(screen.getByRole('button', { name: 'Back 7 days' }))
    expect(onchange).toHaveBeenLastCalledWith({ date: addDays(last, -7) })
    await fireEvent.click(screen.getByRole('button', { name: 'Forward 1 day' }))
    expect(onchange).toHaveBeenLastCalledWith({ date: addDays(last, 1) })
    expect(screen.queryByText('Forecast')).not.toBeInTheDocument()
  })

  it('shows the forecast label past the last observed day', () => {
    const daily = layer('air_temperature_min')
    controls(daily.id, { date: addDays(daily.range.last!.slice(0, 10), 1) })
    expect(screen.getByText('Forecast')).toBeInTheDocument()
  })

  it('offers a range with a statistic, and moves a range by its length', async () => {
    const daily = layer('air_temperature_min')
    const onchange = controls(daily.id, { span: 'range', date: '2026-07-14', start: '2026-07-08' })
    expect(screen.getByLabelText('From')).toHaveValue('2026-07-08')
    expect(screen.getByLabelText('Through')).toHaveValue('2026-07-14')
    expect(screen.getByRole('combobox', { name: 'Combine by' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Forward 1 day' }))
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-07-15', start: '2026-07-09' })
    await fireEvent.click(screen.getByRole('button', { name: '30 days' }))
    expect(onchange).toHaveBeenLastCalledWith({ start: '2026-06-15' })
  })

  it('picks the span', async () => {
    const onchange = controls('air_temperature_min', {})
    await fireEvent.click(screen.getByRole('radio', { name: 'Range' }))
    expect(onchange).toHaveBeenCalledWith({ span: 'range' })
  })

  it('steps an hourly layer by the hour, its clock in CST', async () => {
    const hourly = layer('air_temperature_hourly')
    const onchange = controls(hourly.id, { span: 'hour', hour: '2026-07-08T18' })
    // 18:00 UTC is noon CST
    expect(screen.getByRole('combobox', { name: 'Hour' })).toHaveValue('12')
    await fireEvent.click(screen.getByRole('button', { name: 'Back 6 hours' }))
    expect(onchange).toHaveBeenLastCalledWith({ hour: '2026-07-08T12' })
  })
})
