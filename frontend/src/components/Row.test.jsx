import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Row from './Row'

describe('Row', () => {
  const items = [
    { id: 1, title: 'The Matrix', year: 1999, item_type: 'movie' },
    { id: 2, title: 'Inception', year: 2010, item_type: 'movie' },
  ]

  it('renders row title and cards', () => {
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} />
      </MemoryRouter>
    )
    expect(screen.getByTestId('browse-row-movies-1990s')).toBeInTheDocument()
    expect(screen.getByTestId('browse-row-scroll-movies-1990s')).toBeInTheDocument()
    expect(screen.getByText('1990s Movies')).toBeInTheDocument()
    expect(screen.getByTestId('poster-card-movie-1')).toBeInTheDocument()
    expect(screen.getByTestId('poster-card-movie-2')).toBeInTheDocument()
  })

  it('returns null when items empty', () => {
    const { container } = render(
      <MemoryRouter>
        <Row title="Empty" rowId="empty" items={[]} />
      </MemoryRouter>
    )
    expect(container.firstChild).toBeNull()
  })

  it('suppresses card click after drag scroll', () => {
    const onPlay = vi.fn()
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} onPlay={onPlay} />
      </MemoryRouter>
    )

    const scroll = screen.getByTestId('browse-row-scroll-movies-1990s')
    Object.defineProperty(scroll, 'scrollLeft', { writable: true, value: 0 })

    act(() => {
      fireEvent.mouseDown(scroll, { button: 0, clientX: 100 })
      document.dispatchEvent(
        new MouseEvent('mousemove', { bubbles: true, cancelable: true, clientX: 120 })
      )
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }))
    })

    fireEvent.click(screen.getByTestId('poster-card-movie-1'))
    expect(onPlay).not.toHaveBeenCalled()
  })

  it('has drag scroll handlers and applies momentum on release', () => {
    const rafCallbacks = []
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      rafCallbacks.push(cb)
      return rafCallbacks.length
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})

    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} />
      </MemoryRouter>
    )

    const scroll = screen.getByTestId('browse-row-scroll-movies-1990s')
    Object.defineProperty(scroll, 'scrollLeft', { writable: true, value: 0 })

    act(() => {
      fireEvent.mouseDown(scroll, { button: 0, clientX: 100 })
      document.dispatchEvent(
        new MouseEvent('mousemove', { bubbles: true, cancelable: true, clientX: 130 })
      )
      document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }))
    })

    expect(rafCallbacks.length).toBeGreaterThan(0)

    vi.restoreAllMocks()
  })
})
