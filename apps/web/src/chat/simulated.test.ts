import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { addDelta, assemble, missingSeqs } from './reconcile'
import { SimulatedTransport, type Scenario } from './simulated'
import type { TurnEvent } from './transport'

// O transporte simulado imita os eventos v1 (SPEC-005 §6): deltas com seq, completed com
// delta_count, failed com reason, erro seguro e trace_id.

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

function collect(scenario: Scenario, ms = 60_000) {
  const transport = new SimulatedTransport({ scenario })
  const events: TurnEvent[] = []
  const handle = transport.start('Olá KAI', (event) => events.push(event))
  vi.advanceTimersByTime(ms)
  return { events, handle }
}

function text(events: TurnEvent[]): string {
  let parts = new Map<number, string>()
  for (const e of events) if (e.kind === 'delta') parts = addDelta(parts, e.seq, e.text)
  return assemble(parts)
}

describe('SimulatedTransport', () => {
  it('normal: deltas (alguns trocados ou repetidos) e um completed com o delta_count certo', () => {
    const { events } = collect('normal')
    const deltas = events.filter((e) => e.kind === 'delta')
    const last = events.at(-1)
    expect(last?.kind).toBe('completed')
    if (last?.kind !== 'completed') return
    const seqs = deltas.map((d) => (d.kind === 'delta' ? d.seq : 0))
    // Exercita a reconciliação: há pelo menos uma troca e um repetido.
    expect(seqs.some((s, i) => i > 0 && s < seqs[i - 1])).toBe(true)
    expect(new Set(seqs).size).toBeLessThan(seqs.length)
    let parts = new Map<number, string>()
    for (const d of deltas) if (d.kind === 'delta') parts = addDelta(parts, d.seq, d.text)
    expect(missingSeqs(parts, last.delta_count)).toEqual([])
    expect(text(events).length).toBeGreaterThan(20)
  })

  it('os deltas chegam ao longo do tempo, não todos de uma vez', () => {
    const transport = new SimulatedTransport({ scenario: 'normal' })
    const events: TurnEvent[] = []
    transport.start('x', (e) => events.push(e))
    expect(events).toEqual([])
    // O primeiro delta demora mais (o "pensar", ~360 ms); depois chegam aos poucos.
    vi.advanceTimersByTime(500)
    const early = events.length
    expect(early).toBeGreaterThan(0)
    vi.advanceTimersByTime(60_000)
    expect(events.length).toBeGreaterThan(early)
  })

  it.each([
    ['timeout', 'timeout', true, true],
    ['budget_exceeded', 'budget_exceeded', false, false],
    ['provider_unavailable', 'provider_unavailable', true, false],
  ] as const)('%s: termina em failed com motivo, erro seguro e trace_id', (scenario, reason, retryable, partial) => {
    const { events } = collect(scenario)
    const last = events.at(-1)
    expect(last?.kind).toBe('failed')
    if (last?.kind !== 'failed') return
    expect(last.reason).toBe(reason)
    expect(last.error.retryable).toBe(retryable)
    expect(last.error.code).toMatch(/^[a-z][a-z0-9_]*$/)
    expect(last.error.message.length).toBeGreaterThan(0)
    expect(last.trace_id).toMatch(/^[0-9a-f]{32}$/)
    expect(events.some((e) => e.kind === 'delta')).toBe(partial)
    expect(events.filter((e) => e.kind !== 'delta')).toHaveLength(1)
  })

  it('AC-005-04: cancelar pára já, emite cancelled e mais nada', () => {
    const transport = new SimulatedTransport({ scenario: 'normal' })
    const events: TurnEvent[] = []
    const handle = transport.start('x', (e) => events.push(e))
    vi.advanceTimersByTime(300)
    handle.cancel()
    const last = events.at(-1)
    expect(last?.kind === 'failed' && last.reason).toBe('cancelled')
    const count = events.length
    vi.advanceTimersByTime(60_000)
    handle.cancel()
    expect(events).toHaveLength(count)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('cancelar depois do fim não faz nada', () => {
    const { events, handle } = collect('normal')
    const count = events.length
    handle.cancel()
    expect(events).toHaveLength(count)
  })

  it('o cenário muda para o turno seguinte', () => {
    const transport = new SimulatedTransport({ scenario: 'normal' })
    transport.setScenario('budget_exceeded')
    const events: TurnEvent[] = []
    transport.start('x', (e) => events.push(e))
    vi.advanceTimersByTime(60_000)
    expect(events.at(-1)?.kind).toBe('failed')
  })
})
