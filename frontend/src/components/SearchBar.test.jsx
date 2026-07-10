import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SearchBar from './SearchBar'
import * as api from '../api'

vi.mock('../api')

describe('SearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <SearchBar />
      </MemoryRouter>
    )
    expect(screen.getByTestId('library-search')).toBeInTheDocument()
  })

  it('shows search results after typing', async () => {
    api.searchLibrary.mockResolvedValue({
      results: [
        { id: 1, title: 'Breaking Bad', item_type: 'show', episode_count: 2 },
      ],
    })

    render(
      <MemoryRouter>
        <SearchBar />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByTestId('library-search'), {
      target: { value: 'breaking' },
    })

    await waitFor(() => {
      expect(api.searchLibrary).toHaveBeenCalledWith('breaking')
    })
    expect(await screen.findByTestId('search-result-show-1')).toBeInTheDocument()
  })
})
