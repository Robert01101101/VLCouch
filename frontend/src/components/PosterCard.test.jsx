import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PosterCard from '../components/PosterCard'

describe('PosterCard', () => {
  const item = { id: 1, title: 'The Matrix', year: 1999 }

  it('renders title', () => {
    render(<PosterCard item={item} testId="poster-card-movie-1" />)
    expect(screen.getByTestId('poster-card-movie-1')).toHaveTextContent('The Matrix')
    expect(screen.getByTestId('poster-card-movie-1')).toHaveTextContent('1999')
  })

  it('calls onPlay when card clicked', async () => {
    const onPlay = vi.fn()
    render(
      <PosterCard
        item={item}
        onPlay={onPlay}
        testId="poster-card-movie-1"
      />
    )
    await fireEvent.click(screen.getByTestId('poster-card-movie-1'))
    expect(onPlay).toHaveBeenCalledWith(item)
  })

  it('renders progress bar when watched_count and total_episodes set', () => {
    const showItem = {
      id: 2,
      title: 'Breaking Bad',
      watched_count: 3,
      total_episodes: 10,
      item_type: 'show',
    }
    render(<PosterCard item={showItem} testId="poster-card-show-2" />)
    const progress = screen.getByTestId('poster-card-show-2-progress')
    expect(progress).toBeInTheDocument()
    expect(progress.firstChild).toHaveStyle({ width: '30%' })
  })
})
