import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Row from './Row'

function dispatchPointer(target, type, init = {}) {
  target.dispatchEvent(
    new PointerEvent(type, { bubbles: true, cancelable: true, ...init })
  )
}

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

  it('allows card click without drag', () => {
    const onPlay = vi.fn()
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} onPlay={onPlay} />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByTestId('poster-card-movie-1'))
    expect(onPlay).toHaveBeenCalledWith(items[0])
  })

  it('allows card click after drag scroll', () => {
    const onPlay = vi.fn()
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} onPlay={onPlay} />
      </MemoryRouter>
    )

    const scroll = screen.getByTestId('browse-row-scroll-movies-1990s')
    Object.defineProperty(scroll, 'scrollLeft', { writable: true, value: 0 })

    act(() => {
      fireEvent.pointerDown(scroll, { button: 0, clientX: 100, pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 130, pointerId: 1 })
      dispatchPointer(window, 'pointerup', { pointerId: 1 })
    })

    const card = screen.getByTestId('poster-card-movie-2')
    act(() => {
      fireEvent.pointerDown(card, { button: 0, pointerId: 2 })
      dispatchPointer(window, 'pointerup', { pointerId: 2 })
    })
    fireEvent.click(card)
    expect(onPlay).toHaveBeenCalledWith(items[1])
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
      fireEvent.pointerDown(scroll, { button: 0, clientX: 100, pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 120, pointerId: 1 })
      dispatchPointer(window, 'pointerup', { pointerId: 1 })
    })

    fireEvent.click(screen.getByTestId('poster-card-movie-1'))
    expect(onPlay).not.toHaveBeenCalled()
  })

  it('allows show link click without drag', () => {
    const showItems = [{ id: 9, title: 'Breaking Bad', item_type: 'show' }]
    render(
      <MemoryRouter>
        <Row
          title="TV Shows"
          rowId="tv-shows"
          items={showItems}
          getLink={(item) => `/shows/${item.id}`}
        />
      </MemoryRouter>
    )

    expect(screen.getByTestId('poster-card-show-9')).toHaveAttribute('href', '/shows/9')
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
      fireEvent.pointerDown(scroll, { button: 0, clientX: 100, pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 130, pointerId: 1 })
      dispatchPointer(window, 'pointerup', { pointerId: 1 })
    })

    expect(rafCallbacks.length).toBeGreaterThan(0)

    vi.restoreAllMocks()
  })

  it('ends drag on pointercancel', () => {
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} />
      </MemoryRouter>
    )

    const scroll = screen.getByTestId('browse-row-scroll-movies-1990s')
    Object.defineProperty(scroll, 'scrollLeft', { writable: true, value: 0 })

    act(() => {
      fireEvent.pointerDown(scroll, { button: 0, clientX: 100, pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 130, pointerId: 1 })
    })
    expect(scroll.scrollLeft).toBe(-30)

    act(() => {
      dispatchPointer(window, 'pointercancel', { pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 200, pointerId: 1 })
    })

    expect(scroll.scrollLeft).toBe(-30)
  })

  it('ends drag on window blur', () => {
    render(
      <MemoryRouter>
        <Row title="1990s Movies" rowId="movies-1990s" items={items} />
      </MemoryRouter>
    )

    const scroll = screen.getByTestId('browse-row-scroll-movies-1990s')
    Object.defineProperty(scroll, 'scrollLeft', { writable: true, value: 0 })

    act(() => {
      fireEvent.pointerDown(scroll, { button: 0, clientX: 100, pointerId: 1 })
      dispatchPointer(window, 'pointermove', { clientX: 130, pointerId: 1 })
      window.dispatchEvent(new Event('blur'))
    })
    expect(scroll.scrollLeft).toBe(-30)

    act(() => {
      dispatchPointer(window, 'pointermove', { clientX: 200, pointerId: 1 })
    })

    expect(scroll.scrollLeft).toBe(-30)
  })
})
