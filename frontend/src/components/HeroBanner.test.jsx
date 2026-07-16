import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HeroBanner from './HeroBanner'
import * as api from '../api'

vi.mock('../api')

describe('HeroBanner', () => {
  const onPlayed = vi.fn()

  const episodeHero = {
    item_type: 'episode',
    episode_id: 42,
    show_id: 3,
    show_title: 'Breaking Bad',
    season: 2,
    episode: 5,
    episode_title: 'Fly',
    overview: 'A fly interrupts Walt\'s work.',
    poster_url: '/api/thumbnails/42.jpg',
  }

  const movieHero = {
    item_type: 'movie',
    id: 7,
    title: 'The Matrix',
    year: 1999,
    overview: 'A hacker discovers reality is a simulation.',
    thumbnail_url: '/api/thumbnails/movie-7.jpg',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.playItem.mockResolvedValue({})
  })

  it('renders nothing when hero is absent', () => {
    const { container } = render(<HeroBanner hero={null} onPlayed={onPlayed} />)
    expect(container).toBeEmptyDOMElement()
    expect(screen.queryByTestId('hero-banner')).not.toBeInTheDocument()
  })

  it('renders episode hero content and play button', () => {
    render(<HeroBanner hero={episodeHero} onPlayed={onPlayed} />)
    expect(screen.getByTestId('hero-banner')).toBeInTheDocument()
    expect(screen.getByText('Continue Watching')).toBeInTheDocument()
    expect(screen.getByText('Breaking Bad')).toBeInTheDocument()
    expect(screen.getByText('S02E05 — Fly')).toBeInTheDocument()
    expect(screen.getByText('A fly interrupts Walt\'s work.')).toBeInTheDocument()
    expect(screen.getByTestId('hero-play')).toBeInTheDocument()
    expect(screen.getByTestId('hero-play')).toHaveTextContent('Play')
  })

  it('renders movie hero content and play button', () => {
    render(<HeroBanner hero={movieHero} onPlayed={onPlayed} />)
    expect(screen.getByTestId('hero-banner')).toBeInTheDocument()
    expect(screen.getByText('Watch Again')).toBeInTheDocument()
    expect(screen.getByText('The Matrix')).toBeInTheDocument()
    expect(screen.getByText('1999')).toBeInTheDocument()
    expect(screen.getByTestId('hero-play')).toBeInTheDocument()
  })

  it('calls playItem and onPlayed when play clicked', async () => {
    render(<HeroBanner hero={episodeHero} onPlayed={onPlayed} />)
    fireEvent.click(screen.getByTestId('hero-play'))
    await waitFor(() => {
      expect(api.playItem).toHaveBeenCalledWith('episode', 42)
    })
    await waitFor(() => {
      expect(onPlayed).toHaveBeenCalled()
    })
  })
})
