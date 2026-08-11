import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { dayKey, dayLabel, timeLabel } from './dates'

describe('dates utils', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-09T12:00:00'))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('labels today as "Сегодня"', () => {
    expect(dayLabel('2026-08-09T08:00:00')).toBe('Сегодня')
  })

  it('labels yesterday as "Вчера"', () => {
    expect(dayLabel('2026-08-08T21:00:00')).toBe('Вчера')
  })

  it('labels older dates with the full date', () => {
    const label = dayLabel('2026-07-01T10:00:00')
    expect(label).toContain('июля')
  })

  it('dayKey groups timestamps from the same calendar day together', () => {
    expect(dayKey('2026-08-09T00:05:00')).toBe(dayKey('2026-08-09T23:55:00'))
    expect(dayKey('2026-08-09T23:55:00')).not.toBe(dayKey('2026-08-10T00:05:00'))
  })

  it('timeLabel formats as HH:MM', () => {
    expect(timeLabel('2026-08-09T09:05:00')).toMatch(/^\d{2}:\d{2}$/)
  })
})
