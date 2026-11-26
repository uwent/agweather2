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
    expect(screen.queryByTestId('forecast-badge')).not.toBeInTheDocument()
  })

  it('shows the forecast label past the last observed day', () => {
    const daily = layer('air_temperature_min')
    controls(daily.id, { date: addDays(daily.range.last!.slice(0, 10), 1) })
    expect(screen.getByTestId('forecast-badge')).toHaveTextContent('Forecast')
    expect(screen.getByRole('slider', { name: 'Day on the timeline' })).toHaveAttribute(
      'aria-valuetext',
      'Nov 25, 2026, forecast',
    )
  })

  it('says what the layer reaches, and marks the forecast’s boundary on the slider', () => {
    controls('air_temperature_min', { date: '2026-11-20' })
    expect(screen.getByTestId('date-reach')).toHaveTextContent(
      'You can map any day from Jan 1, 2016 to Dec 6, 2026. Days through Nov 24, 2026 are observed; later days are a forecast.',
    )
    expect(screen.getByTestId('forecast-boundary')).toHaveTextContent('Observed through Nov 24')
    expect(screen.getByTestId('forecast-boundary')).toHaveTextContent('Forecast')
    expect(screen.getByTestId('forecast-segment')).toBeInTheDocument()
  })

  it('moves the day by the slider’s keys, held to the forecast’s last day', async () => {
    const onchange = controls('air_temperature_min', { date: '2026-11-20' })
    const slider = screen.getByRole('slider', { name: 'Day on the timeline' })
    expect(slider).toHaveAttribute('aria-valuetext', 'Nov 20, 2026')
    await fireEvent.keyDown(slider, { key: 'ArrowRight' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-11-21' })
    await fireEvent.keyDown(slider, { key: 'PageDown' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-11-13' })
    await fireEvent.keyDown(slider, { key: 'End' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-12-06' })
    // The recent weeks' first day
    await fireEvent.keyDown(slider, { key: 'Home' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-10-14' })
  })

  it('shows the recent weeks first, and a whole year when one is chosen', async () => {
    const onchange = controls('air_temperature_min', { date: '2026-11-20' })
    const timeline = screen.getByRole('combobox', { name: 'Timeline' })
    expect(timeline).toHaveValue('recent')
    expect(screen.getByText('Oct 14')).toBeInTheDocument()
    await fireEvent.change(timeline, { target: { value: '2026' } })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-11-20' })
    expect(timeline).toHaveValue('2026')
    expect(screen.getByText('Jan')).toBeInTheDocument()
    await fireEvent.keyDown(screen.getByRole('slider', { name: 'Day on the timeline' }), { key: 'Home' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-01-01' })
  })

  it('chooses a year, keeping the day of the year; a past year has no forecast', async () => {
    const onchange = controls('air_temperature_min', { date: '2026-07-08' })
    await fireEvent.change(screen.getByRole('combobox', { name: 'Timeline' }), { target: { value: '2020' } })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2020-07-08' })
  })

  it('has no forecast on a past year’s slider', () => {
    controls('air_temperature_min', { date: '2020-07-08' })
    expect(screen.queryByTestId('forecast-boundary')).not.toBeInTheDocument()
    expect(screen.queryByTestId('forecast-segment')).not.toBeInTheDocument()
  })

  it('shows a range as a band and slides its end, keeping its length', async () => {
    const onchange = controls('air_temperature_min', { span: 'range', date: '2026-07-14', start: '2026-07-08' })
    expect(screen.getByTestId('date-band')).toBeInTheDocument()
    await fireEvent.keyDown(screen.getByRole('slider', { name: 'Last day on the timeline' }), { key: 'ArrowLeft' })
    expect(onchange).toHaveBeenLastCalledWith({ date: '2026-07-13', start: '2026-07-07' })
  })

  it('shows the season to date as a band from January 1', () => {
    controls('degree_days', { span: 'season', date: '2026-07-14' })
    expect(screen.getByTestId('date-band')).toBeInTheDocument()
    expect(screen.getByRole('slider', { name: 'Last day on the timeline' })).toHaveAttribute(
      'aria-valuetext',
      'Jul 14, 2026',
    )
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
    const slider = screen.getByRole('slider', { name: 'Hour on the timeline' })
    expect(slider).toHaveAttribute('aria-valuetext', 'noon CST, Jul 8, 2026')
    await fireEvent.keyDown(slider, { key: 'PageUp' })
    expect(onchange).toHaveBeenLastCalledWith({ hour: '2026-07-09T00' })
  })

  it('shows an hourly layer’s newest hours with the forecast after them', () => {
    controls('air_temperature_hourly', { span: 'hour' })
    expect(screen.getByTestId('forecast-boundary')).toHaveTextContent('Observed through Nov 25, 2 p.m. CST')
  })
})
