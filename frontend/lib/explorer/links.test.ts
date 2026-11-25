import { describe, expect, it } from 'vitest'

import { modelPath, sitePath, siteModelPath } from './links'

describe('links', () => {
  it('gives a site’s page by its key, with a name', () => {
    expect(sitePath(43.07312, -89.40001)).toBe('/sites/43.0731,-89.4')
    expect(sitePath(43.07, -89.4, 'Arlington, WI')).toBe('/sites/43.07,-89.4?name=Arlington%2C+WI')
  })

  it('gives a model’s page and a model at a site', () => {
    expect(modelPath('late-blight-dsv')).toBe('/models/late-blight-dsv')
    expect(siteModelPath(43.07, -89.4, 'tar-spot')).toBe('/sites/43.07,-89.4/models/tar-spot')
    expect(siteModelPath(43.07, -89.4, 'tar-spot', 'Hancock')).toBe('/sites/43.07,-89.4/models/tar-spot?name=Hancock')
  })
})
