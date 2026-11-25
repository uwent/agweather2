import { fireEvent, render, screen } from '@testing-library/svelte'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { addSite, memoryBackend, useSitesBackend } from '@/lib/sites.svelte'
import { page, router } from '@/test/page.svelte'
import type { HomeProps } from '@/types'

import Home from './Home.svelte'

vi.mock('@inertiajs/svelte', async () => {
  const fake = await import('@/test/page.svelte')
  const { default: Link } = await import('@/test/FakeLink.svelte')
  return { ...fake, Link }
})

const props: HomeProps = {
  api_docs_url: '/api/v2/docs',
  maps: [
    {
      layer: 'air_temperature_min',
      title: 'Low temperature',
      alt: 'Map of the daily low air temperature across the region on the latest day.',
      image_url: '/api/v2/maps/air_temperature_min.png?width=640',
      map_url: '/map?layer=air_temperature_min',
    },
  ],
  in_season: [
    {
      crop: 'potato',
      name: 'Potato',
      models: [
        {
          id: 'potato-volunteer',
          name: 'Potato volunteer survival',
          group: 'agronomic',
          url: '/models/potato-volunteer',
        },
      ],
    },
  ],
}

beforeEach(() => {
  useSitesBackend(memoryBackend())
  page.props.status = null
})

describe('the home page', () => {
  it('shows the month’s maps as lazy images linking to the map, and the models in season', () => {
    render(Home, props)
    const image = screen.getByRole('img', { name: props.maps[0].alt })
    expect(image).toHaveAttribute('loading', 'lazy')
    expect(image).toHaveAttribute('src', '/api/v2/maps/air_temperature_min.png?width=640')
    expect(screen.getByRole('link', { name: /Low temperature/ })).toHaveAttribute(
      'href',
      '/map?layer=air_temperature_min',
    )
    expect(screen.getByRole('link', { name: 'Potato volunteer survival' })).toHaveAttribute(
      'href',
      '/models/potato-volunteer',
    )
    expect(screen.queryByRole('heading', { name: 'Your sites' })).toBeNull()
  })

  it('lists saved sites as links, without requests', () => {
    addSite({ lat: 43.07, lng: -89.4, name: 'Home farm' })
    addSite({ lat: 44, lng: -89 })
    render(Home, props)
    expect(screen.getByRole('link', { name: 'Home farm' })).toHaveAttribute('href', '/sites/43.07,-89.4')
    expect(screen.getByRole('link', { name: '44.00° N, 89.00° W' })).toHaveAttribute('href', '/sites/44,-89')
  })

  it('says how far the data go', () => {
    page.props.status = {
      observed_through: '2026-11-25T20:00:00Z',
      daily_through: '2026-11-24',
      forecast_cycle: '2026-11-25T18:00:00Z',
      forecast_through: '2026-12-07T06:00:00Z',
      forecast_fallback: null,
      behind: [],
      stale_sources: [],
    }
    render(Home, props)
    expect(screen.getByText('Observed through 2 p.m. CST, Nov 25 · forecast to Dec 6.')).toBeVisible()
  })

  it('goes to the site page for typed coordinates', async () => {
    const visit = vi.spyOn(router, 'visit')
    render(Home, props)
    await fireEvent.input(screen.getByLabelText('See the weather and crop risk for a place'), {
      target: { value: '43.07, -89.40' },
    })
    await fireEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(visit).toHaveBeenCalledWith('/sites/43.07,-89.4')
  })
})
