import { fireEvent, render, screen, within } from '@testing-library/svelte'
import { beforeEach, describe, expect, it } from 'vitest'

import {
  addGroup,
  addSite,
  effectivePrefs,
  groups,
  memoryBackend,
  prefsAt,
  setInGroup,
  setPrefs,
  useSitesBackend,
} from '@/lib/sites.svelte'
import type { ModelSettings } from '@/types'

import GroupsPanel from './GroupsPanel.svelte'
import PrefsPanel from './PrefsPanel.svelte'
import SiteGroups from './SiteGroups.svelte'

const models = [
  { id: 'late-blight-dsv', name: 'Late blight', crops: ['potato'] },
  { id: 'tar-spot', name: 'Tar spot', crops: ['corn'] },
  { id: 'white-mold', name: 'White mold', crops: ['soybean', 'potato'] },
]
const crops = [
  { id: 'corn', name: 'Corn' },
  { id: 'potato', name: 'Potato' },
  { id: 'soybean', name: 'Soybean' },
]
const settings: ModelSettings[] = [
  {
    id: 'late-blight-dsv',
    name: 'Late blight',
    group: 'disease',
    biofix: null,
    planting: null,
    options: [
      {
        name: 'protection_days',
        label: 'Days a spray protects',
        choices: [
          { value: '5', label: '5 days' },
          { value: '7', label: '7 days' },
        ],
        default: '7',
        date: false,
      },
    ],
  },
]

let madison: string
let hancock: string
let farm: string
let spuds: string

beforeEach(() => {
  useSitesBackend(memoryBackend())
  madison = (addSite({ lat: 43.07, lng: -89.4, name: 'Madison' }) as { value: { key: string } }).value.key
  hancock = (addSite({ lat: 44.1336, lng: -89.5168, name: 'Hancock' }) as { value: { key: string } }).value.key
  farm = (addGroup('North farm') as { value: { id: string } }).value.id
  spuds = (addGroup('Potatoes') as { value: { id: string } }).value.id
  setInGroup(farm, madison, true)
  setInGroup(farm, hancock, true)
  setInGroup(spuds, hancock, true)
})

describe('PrefsPanel', () => {
  it('tells a site which groups it follows and where each value comes from', async () => {
    setPrefs({ kind: 'group', id: farm }, { crops: ['corn'] })
    setPrefs({ kind: 'group', id: spuds }, { crops: ['potato'], planting: 'early' })
    render(PrefsPanel, { level: { kind: 'site', key: hancock }, models, crops, settings })
    expect(
      screen.getByText(
        'This site follows its groups: North farm and Potatoes. Change a choice here to override them for this site only.',
      ),
    ).toBeTruthy()
    expect(screen.getByText('From the groups North farm and Potatoes: Corn and Potato.')).toBeTruthy()
    expect(screen.getByText('From the group Potatoes: early for each site.')).toBeTruthy()
    // The union of the groups' crops is checked, and only their models listed
    const cropBoxes = within(screen.getByRole('group', { name: 'Crops' }))
    expect((cropBoxes.getByRole('checkbox', { name: 'Corn' }) as HTMLInputElement).checked).toBe(true)
    expect((cropBoxes.getByRole('checkbox', { name: 'Soybean' }) as HTMLInputElement).checked).toBe(false)
    const modelBoxes = within(screen.getByRole('group', { name: 'Models to show' }))
    expect(modelBoxes.getAllByRole('checkbox').map((b) => b.parentElement!.textContent!.trim())).toEqual([
      'Late blight',
      'Tar spot',
      'White mold',
    ])

    // Overriding at the site: its own list, then a reset per field
    await fireEvent.click(cropBoxes.getByRole('checkbox', { name: 'Corn' }))
    expect(prefsAt({ kind: 'site', key: hancock }).crops).toEqual(['potato'])
    expect(screen.getByText('Set for this site: Potato.')).toBeTruthy()
    await fireEvent.click(screen.getByRole('button', { name: 'Reset crops for this site' }))
    expect(prefsAt({ kind: 'site', key: hancock }).crops).toBeUndefined()
    expect(effectivePrefs(hancock).crops).toEqual(['corn', 'potato'])
  })

  it('hides a model for a group, which both its sites follow, and resets to my defaults', async () => {
    render(PrefsPanel, { level: { kind: 'group', id: farm }, models, crops, settings })
    const modelBoxes = within(screen.getByRole('group', { name: 'Models to show' }))
    await fireEvent.click(modelBoxes.getByRole('checkbox', { name: 'Tar spot' }))
    expect(effectivePrefs(madison).hiddenModels).toEqual(['tar-spot'])
    expect(effectivePrefs(hancock).hiddenModels).toEqual(['tar-spot'])
    expect(screen.getByText('Set for this group: Tar spot hidden.')).toBeTruthy()

    const reset = screen.getByRole('button', { name: 'Reset to my defaults' })
    await fireEvent.click(reset)
    expect(effectivePrefs(madison).hiddenModels).toEqual([])
    expect((reset as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('Back to your defaults.')).toBeTruthy()
  })

  it('sets a model’s option at all sites, shown with its source at a site', async () => {
    const view = render(PrefsPanel, { level: { kind: 'all' }, models, crops, settings })
    await fireEvent.change(screen.getByLabelText('Change a model’s settings'), { target: { value: 'late-blight-dsv' } })
    await fireEvent.change(screen.getByLabelText('Days a spray protects'), { target: { value: '5' } })
    expect(effectivePrefs(madison).options['late-blight-dsv']).toEqual({ protection_days: '5' })
    expect(screen.getByText('Late blight, days a spray protects: 5 days')).toBeTruthy()
    view.unmount()

    render(PrefsPanel, { level: { kind: 'site', key: madison }, models, crops, settings })
    expect(screen.getByText('(from your choices for all sites)')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Reset Late blight, days a spray protects' })).toBeNull()
  })
})

describe('GroupsPanel', () => {
  it('reorders groups, links each to the map and asks before deleting', async () => {
    setPrefs({ kind: 'group', id: farm }, { layer: 'tar-spot' })
    render(GroupsPanel, { models, crops, settings })
    const list = screen.getByRole('list', { name: 'Your groups' })
    const names = () =>
      within(list)
        .getAllByRole('listitem')
        .map((li) => li.dataset.testid)
    expect(names()).toEqual(['group-North farm', 'group-Potatoes'])

    await fireEvent.click(screen.getByRole('button', { name: 'Move Potatoes up' }))
    expect(groups.map((g) => g.name)).toEqual(['Potatoes', 'North farm'])
    expect(names()).toEqual(['group-Potatoes', 'group-North farm'])

    const link = within(screen.getByTestId('group-North farm')).getByRole('link', { name: 'Show on the map' })
    const url = new URL(link.getAttribute('href')!, 'https://example.org')
    expect(url.searchParams.get('layer')).toBe('tar-spot')
    expect(url.searchParams.get('group')).toBe('North%20farm;43.07,-89.4,Madison;44.1336,-89.5168,Hancock')

    await fireEvent.click(screen.getByRole('button', { name: 'Delete Potatoes' }))
    expect(groups).toHaveLength(2)
    await fireEvent.click(screen.getByRole('button', { name: 'Delete Potatoes now' }))
    expect(groups.map((g) => g.name)).toEqual(['North farm'])
  })

  it('opens a group’s preferences', async () => {
    render(GroupsPanel, { models, crops, settings })
    await fireEvent.click(screen.getByRole('button', { name: 'Preferences for Potatoes' }))
    expect(screen.getByRole('heading', { name: 'Preferences for Potatoes' })).toBeTruthy()
    expect(screen.getByText(/^Sites in Potatoes follow these choices/)).toBeTruthy()
  })
})

describe('SiteGroups', () => {
  it('puts a site in groups and makes a new one with it', async () => {
    render(SiteGroups, { siteKey: madison, label: 'Madison' })
    await fireEvent.click(screen.getByRole('checkbox', { name: 'Potatoes' }))
    expect(groups.find((g) => g.id === spuds)!.siteKeys).toContain(madison)
    await fireEvent.input(screen.getByLabelText('New group for Madison'), { target: { value: 'Clients' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Add a new group with Madison in it' }))
    expect(groups.find((g) => g.name === 'Clients')!.siteKeys).toEqual([madison])
    expect(screen.getByText('Madison added to Clients.')).toBeTruthy()
  })
})
