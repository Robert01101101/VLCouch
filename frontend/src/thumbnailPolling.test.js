import { describe, expect, it } from 'vitest'
import { browseMissingThumbnails, showMissingThumbnails } from './thumbnailPolling'

describe('thumbnailPolling', () => {
  it('detects missing browse posters', () => {
    expect(
      browseMissingThumbnails({
        hero: null,
        rows: [{ items: [{ id: 1, poster_url: null }] }],
      })
    ).toBe(true)
    expect(
      browseMissingThumbnails({
        hero: { poster_url: '/posters/a.jpg' },
        rows: [{ items: [{ id: 1, poster_url: '/posters/b.jpg' }] }],
      })
    ).toBe(false)
  })

  it('detects missing hero image', () => {
    expect(
      browseMissingThumbnails({
        hero: { poster_url: null, thumbnail_url: null },
        rows: [],
      })
    ).toBe(true)
  })

  it('detects missing show and episode thumbnails', () => {
    expect(
      showMissingThumbnails({
        poster_url: null,
        seasons: [{ episodes: [{ id: 1, thumbnail_url: '/posters/ep.jpg' }] }],
      })
    ).toBe(true)
    expect(
      showMissingThumbnails({
        poster_url: '/posters/show.jpg',
        seasons: [{ episodes: [{ id: 1, thumbnail_url: null }] }],
      })
    ).toBe(true)
    expect(
      showMissingThumbnails({
        poster_url: '/posters/show.jpg',
        seasons: [{ episodes: [{ id: 1, thumbnail_url: '/posters/ep.jpg' }] }],
      })
    ).toBe(false)
  })
})
