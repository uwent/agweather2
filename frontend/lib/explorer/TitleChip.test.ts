import { render, screen } from '@testing-library/svelte'
import { describe, expect, it } from 'vitest'

import TitleChip from './TitleChip.svelte'

describe('TitleChip', () => {
  it('shows what the map is, marking a forecast day, and nothing of how far the data reaches', () => {
    render(TitleChip, { title: 'Air temperature, daily minimum', subtitle: 'Nov 27, 2026', forecast: true })
    const chip = screen.getByTestId('title-chip')
    expect(chip).toHaveTextContent('Air temperature, daily minimum')
    expect(chip).toHaveTextContent('Nov 27, 2026, Forecast')
    expect(chip).not.toHaveTextContent('Observed')
  })

  it('leaves an observed day unmarked', () => {
    render(TitleChip, { title: 'Air temperature, daily minimum', subtitle: 'Nov 20, 2026' })
    expect(screen.queryByText('Forecast')).not.toBeInTheDocument()
  })
})
