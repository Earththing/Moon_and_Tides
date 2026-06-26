import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LocationSearch from '../components/LocationSearch'
import * as api from '../api'

const MOCK_RESULT = [{ lat: 37.7749, lon: -122.4194, display_name: 'San Francisco, CA, USA' }]

describe('LocationSearch', () => {
  beforeEach(() => {
    vi.spyOn(api, 'geocode').mockResolvedValue(MOCK_RESULT)
  })
  afterEach(() => vi.restoreAllMocks())

  it('geocode not called until 300ms after last keystroke', async () => {
    const user = userEvent.setup({ delay: null })
    render(<LocationSearch onSelect={vi.fn()} />)
    const input = screen.getByPlaceholderText(/search/i)
    await user.type(input, 'San')
    expect(api.geocode).not.toHaveBeenCalled()
    await waitFor(() => expect(api.geocode).toHaveBeenCalledWith('San'), { timeout: 500 })
  })

  it('selecting candidate calls onSelect with lat/lon', async () => {
    const user = userEvent.setup({ delay: null })
    const onSelect = vi.fn()
    render(<LocationSearch onSelect={onSelect} />)
    const input = screen.getByPlaceholderText(/search/i)
    await user.type(input, 'San Francisco')
    await waitFor(() => screen.getByText(/San Francisco/), { timeout: 500 })
    await user.click(screen.getByText(/San Francisco/))
    expect(onSelect).toHaveBeenCalledWith(MOCK_RESULT[0])
  })
})
