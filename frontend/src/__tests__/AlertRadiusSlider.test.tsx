import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import AlertRadiusSlider from '../components/AlertRadiusSlider'

describe('AlertRadiusSlider', () => {
  it('station count label updates when value changes', async () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <AlertRadiusSlider value={50} stationCount={3} onChange={onChange} />
    )
    expect(screen.getByText(/3 station/)).toBeTruthy()

    rerender(<AlertRadiusSlider value={100} stationCount={7} onChange={onChange} />)
    expect(screen.getByText(/7 station/)).toBeTruthy()
    expect(screen.getByText(/100 mi/)).toBeTruthy()
  })
})
