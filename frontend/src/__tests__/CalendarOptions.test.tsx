import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CalendarOptions from '../components/CalendarOptions'

const DEFAULT_OPTIONS = {
  hilo: true, alerts: true, slack: false, tidepooling: false,
  flood: false, perigean: true, radius: false,
}

describe('CalendarOptions', () => {
  it('slack water disabled when station is non-harmonic', () => {
    render(
      <CalendarOptions
        options={DEFAULT_OPTIONS}
        onChange={vi.fn()}
        isHarmonic={false}
        hasFloodData={false}
        radiusActive={false}
      />
    )
    const label = screen.getByText('Slack water').closest('label')!
    const input = label.querySelector('input')!
    expect(input).toBeDisabled()
  })

  it('flood risk disabled when station has no flood data', () => {
    render(
      <CalendarOptions
        options={DEFAULT_OPTIONS}
        onChange={vi.fn()}
        isHarmonic={true}
        hasFloodData={false}
        radiusActive={true}
      />
    )
    const label = screen.getByText('Flood risk').closest('label')!
    expect(label.querySelector('input')).toBeDisabled()
  })

  it('radius alerts disabled when radius at minimum', () => {
    render(
      <CalendarOptions
        options={DEFAULT_OPTIONS}
        onChange={vi.fn()}
        isHarmonic={true}
        hasFloodData={true}
        radiusActive={false}
      />
    )
    const label = screen.getByText('Radius alerts').closest('label')!
    expect(label.querySelector('input')).toBeDisabled()
  })

  it('high & low tides checkbox cannot be unchecked', () => {
    render(
      <CalendarOptions
        options={DEFAULT_OPTIONS}
        onChange={vi.fn()}
        isHarmonic={true}
        hasFloodData={true}
        radiusActive={true}
      />
    )
    const label = screen.getByText('High & low tides').closest('label')!
    const input = label.querySelector('input')!
    expect(input).toBeChecked()
    expect(input).toBeDisabled()
  })

  it('enabled option calls onChange when clicked', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <CalendarOptions
        options={DEFAULT_OPTIONS}
        onChange={onChange}
        isHarmonic={true}
        hasFloodData={true}
        radiusActive={true}
      />
    )
    const label = screen.getByText('Slack water').closest('label')!
    await user.click(label.querySelector('input')!)
    expect(onChange).toHaveBeenCalledOnce()
  })
})
