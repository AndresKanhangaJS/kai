import { describe, expect, it } from 'vitest'
import { addDelta, assemble, isComplete, MAX_SEQ, missingSeqs } from './reconcile'

// AC-005-03: a resposta monta-se por `seq`, sem duplicados nem buracos (prepara a AC-004-10).

describe('reconcile', () => {
  it('monta por ordem de seq mesmo com deltas trocados', () => {
    let parts = addDelta(new Map(), 2, ' mundo')
    parts = addDelta(parts, 1, 'Olá')
    parts = addDelta(parts, 3, '!')
    expect(assemble(parts)).toBe('Olá mundo!')
  })

  it('ignora um delta repetido (o primeiro ganha)', () => {
    let parts = addDelta(new Map(), 1, 'Olá')
    parts = addDelta(parts, 1, 'XXX')
    parts = addDelta(parts, 2, ' mundo')
    expect(assemble(parts)).toBe('Olá mundo')
  })

  it('não altera o mapa original', () => {
    const before = addDelta(new Map(), 1, 'a')
    addDelta(before, 2, 'b')
    expect(assemble(before)).toBe('a')
  })

  it('com o delta_count, diz que seqs faltam', () => {
    let parts = addDelta(new Map(), 1, 'a')
    parts = addDelta(parts, 3, 'c')
    expect(missingSeqs(parts, 4)).toEqual([2, 4])
    expect(missingSeqs(addDelta(parts, 2, 'b'), 3)).toEqual([])
  })

  it('isComplete exige exactamente 1..delta_count', () => {
    let parts = addDelta(new Map(), 1, 'a')
    parts = addDelta(parts, 2, 'b')
    expect(isComplete(parts, 2)).toBe(true)
    expect(isComplete(parts, 3)).toBe(false)
    expect(isComplete(parts, 1)).toBe(false)
    expect(isComplete(parts, Number.NaN)).toBe(false)
    expect(isComplete(parts, 1e12)).toBe(false)
  })

  it('negativo: delta_count e seq absurdos têm tecto (sem congelar o browser)', () => {
    expect(assemble(addDelta(new Map(), MAX_SEQ + 1, 'x'))).toBe('')
    expect(missingSeqs(new Map(), 1e12)).toHaveLength(MAX_SEQ)
    expect(missingSeqs(new Map(), Number.POSITIVE_INFINITY)).toEqual([])
  })

  it('recusa seqs inválidos', () => {
    expect(assemble(addDelta(new Map(), 0, 'x'))).toBe('')
    expect(assemble(addDelta(new Map(), 1.5, 'x'))).toBe('')
  })
})
