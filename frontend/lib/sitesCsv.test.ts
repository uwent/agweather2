import { describe, expect, it } from 'vitest'

import { cleanName, parseCsvRows, parseSitesCsv, sitesToCsv, uniqueName } from './sitesCsv'

describe('parseCsvRows', () => {
  it('reads quoted cells with commas, quotes and line breaks, any line ending, and a byte order mark', () => {
    const text = '﻿name,lat\r\n"Smith, North",43\n"Say ""hi""",44\r"two\nlines",45'
    expect(parseCsvRows(text)).toEqual([
      ['name', 'lat'],
      ['Smith, North', '43'],
      ['Say "hi"', '44'],
      ['two\nlines', '45'],
    ])
  })
})

describe('parseSitesCsv', () => {
  it('reads our own export back', () => {
    const csv = sitesToCsv([
      { name: 'Home farm', lat: 43.07, lng: -89.4, groups: ['North', 'Clients'] },
      { name: '=Sum, field', lat: 44.5, lng: -89.5, groups: [] },
    ])
    expect(csv.split('\r\n')[0]).toBe('name,lat,lng,groups')
    const parsed = parseSitesCsv(csv)
    expect(parsed.error).toBeNull()
    expect(parsed.sites).toEqual([
      { name: 'Home farm', lat: 43.07, lng: -89.4, groups: ['North', 'Clients'], row: 2 },
      // A spreadsheet formula is written with a quote in front, so it reads back as text
      { name: "'=Sum, field", lat: 44.5, lng: -89.5, groups: [], row: 3 },
    ])
  })

  it('reads the Crop Risk Tool’s files: its export and the column names its upload took', () => {
    const exported = 'id,name,lat,lng\n1,Arlington,43.297,-89.38\n'
    expect(parseSitesCsv(exported).sites.map((s) => s.name)).toEqual(['Arlington'])
    const example = '﻿Location,State,Latitude,Longitude\nKankakee,IL,41.12,-87.83\nEau Claire,WI,44.82,-91.5\n'
    expect(parseSitesCsv(example).sites).toEqual([
      { name: 'Kankakee', lat: 41.12, lng: -87.83, groups: [], row: 2 },
      { name: 'Eau Claire', lat: 44.82, lng: -91.5, groups: [], row: 3 },
    ])
    const stations = 'ID,Name,Latitude,Long\nALTN,Arlington,43.297,-89.38\n'
    expect(parseSitesCsv(stations).sites[0]).toMatchObject({ name: 'Arlington', lng: -89.38 })
  })

  it('lists each row it leaves out, numbered as a spreadsheet numbers it, in a sentence', () => {
    const text = 'name,lat,lng\nGood,43,-89\n\nBad lat,abc,-89\nNo lng,43,\nOff the map,95,-89\n'
    const parsed = parseSitesCsv(text)
    expect(parsed.sites.map((s) => [s.name, s.row])).toEqual([['Good', 2]])
    expect(parsed.skipped).toEqual([
      { row: 4, message: "Row 4 was skipped: its latitude 'abc' isn’t a number in decimal degrees." },
      { row: 5, message: 'Row 5 was skipped: its latitude or longitude is blank.' },
      {
        row: 6,
        message:
          'Row 6 was skipped: 95, -89 isn’t a place on Earth. Latitude runs from -90 to 90 and longitude from -180 to 180.',
      },
    ])
  })

  it('refuses a file without coordinates or without rows', () => {
    expect(parseSitesCsv('').error).toBe('The file is empty.')
    expect(parseSitesCsv('name,town\nA,B\n').error).toMatch(/couldn’t find latitude and longitude columns/)
  })

  it('cleans names: tags removed, spaces collapsed, long ones cut', () => {
    expect(cleanName('  <b>North</b>   field ')).toBe('North field')
    expect(cleanName('x'.repeat(80))).toHaveLength(60)
    const taken = new Set(['north'])
    expect(uniqueName('North', taken)).toBe('North (2)')
    expect(uniqueName('North', taken)).toBe('North (3)')
    expect(uniqueName('', taken)).toBe('')
  })

  it('reads a decimal comma in a quoted cell, and rounds to the key’s precision', () => {
    expect(parseSitesCsv('name,lat,lng\nA,"43,071234","-89,4"\n').sites[0]).toMatchObject({ lat: 43.0712, lng: -89.4 })
  })
})
