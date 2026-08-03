import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LibraryStructureGuide from './LibraryStructureGuide'

describe('LibraryStructureGuide', () => {
  it('renders collapsed by default', () => {
    render(<LibraryStructureGuide />)
    expect(screen.getByTestId('settings-library-structure-section')).toHaveTextContent(
      'Expected file structure'
    )
    expect(screen.getByTestId('settings-library-structure-learn-more')).toBeInTheDocument()
    expect(screen.queryByTestId('settings-library-structure-content')).not.toBeVisible()
  })

  it('expands to show folder examples', () => {
    render(<LibraryStructureGuide />)
    fireEvent.click(screen.getByText('Learn more'))
    const content = screen.getByTestId('settings-library-structure-content')
    expect(content).toBeVisible()
    expect(content).toHaveTextContent('Mystery Manor')
    expect(content).toHaveTextContent('[Mystery]')
    expect(content).toHaveTextContent('Harbor Lights (2018).mkv')
  })
})
