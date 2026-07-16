import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Home from './Home'
import * as api from '../api'

vi.mock('../api')

describe('Home', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.fetchMediaRoots.mockResolvedValue({ roots: [{ path: 'D:/Movies', type: 'movies' }] })
  })

  it('shows loading state', () => {
    api.fetchBrowse.mockReturnValue(new Promise(() => {}))
    api.fetchMediaRoots.mockReturnValue(new Promise(() => {}))
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(screen.getByTestId('page-loading')).toBeInTheDocument()
  })

  it('shows setup wizard when no media folders are configured', async () => {
    api.fetchBrowse.mockResolvedValue({ hero: null, rows: [] })
    api.fetchMediaRoots.mockResolvedValue({ roots: [] })
    render(
      <MemoryRouter>
        <Home scanning={false} onScan={vi.fn()} />
      </MemoryRouter>
    )
    expect(await screen.findByTestId('setup-wizard')).toBeInTheDocument()
  })

  it('shows error state', async () => {
    api.fetchBrowse.mockRejectedValue(new Error('Network error'))
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    expect(await screen.findByTestId('page-error')).toHaveTextContent('Network error')
  })

  it('renders browse rows after fetch', async () => {
    api.fetchBrowse.mockResolvedValue({
      hero: null,
      rows: [
        {
          id: 'movies-1990s',
          title: '1990s Movies',
          item_type: 'movie',
          items: [{ id: 1, title: 'The Matrix', year: 1999, item_type: 'movie' }],
        },
      ],
    })
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByTestId('browse-row-movies-1990s')).toBeInTheDocument()
    })
    expect(screen.getByTestId('poster-card-movie-1')).toBeInTheDocument()
    expect(screen.queryByTestId('hero-banner')).not.toBeInTheDocument()
  })

  it('prefixes TV category row titles with [TV]', async () => {
    api.fetchBrowse.mockResolvedValue({
      hero: null,
      rows: [
        {
          id: 'shows-drama',
          title: 'Drama',
          item_type: 'show',
          items: [{ id: 1, title: 'Breaking Bad', year: 2008, item_type: 'show' }],
        },
        {
          id: 'recently-watched',
          title: 'Recently Watched',
          item_type: 'mixed',
          items: [{ id: 2, title: 'Breaking Bad', year: 2008, item_type: 'show' }],
        },
      ],
    })
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('[TV] Drama')).toBeInTheDocument()
    })
    expect(screen.getByText('Recently Watched')).toBeInTheDocument()
    expect(screen.queryByText('[TV] Recently Watched')).not.toBeInTheDocument()
  })

  it('renders hero banner when browse includes hero', async () => {
    api.fetchBrowse.mockResolvedValue({
      hero: {
        item_type: 'episode',
        episode_id: 42,
        show_id: 3,
        show_title: 'Breaking Bad',
        season: 2,
        episode: 5,
        episode_title: 'Fly',
        overview: 'A fly interrupts Walt\'s work.',
        poster_url: '/api/thumbnails/42.jpg',
      },
      rows: [],
    })
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByTestId('hero-banner')).toBeInTheDocument()
    })
    expect(screen.getByText('Breaking Bad')).toBeInTheDocument()
    expect(screen.getByText('S02E05 — Fly')).toBeInTheDocument()
    expect(screen.getByText('A fly interrupts Walt\'s work.')).toBeInTheDocument()
    expect(screen.getByTestId('hero-play')).toBeInTheDocument()
  })
})
