// Reconciliação dos deltas por `seq` (AC-005-03; prepara a AC-004-10): a ordem de chegada
// não importa e um delta repetido não duplica texto (o primeiro ganha).
// Os tectos protegem o browser de um transporte avariado ou hostil (revisão de segurança, E5.0).

/** Mais deltas do que isto num turno é avaria: o resto é ignorado. */
export const MAX_SEQ = 65_536

export type Parts = ReadonlyMap<number, string>

export function addDelta(parts: Parts, seq: number, text: string): Map<number, string> {
  const next = new Map(parts)
  if (Number.isInteger(seq) && seq >= 1 && seq <= MAX_SEQ && !next.has(seq) && typeof text === 'string') {
    next.set(seq, text)
  }
  return next
}

export function assemble(parts: Parts): string {
  return [...parts.entries()]
    .sort(([a], [b]) => a - b)
    .map(([, text]) => text)
    .join('')
}

/** A resposta está completa se tem exactamente os seqs 1..delta_count (sem buracos nem a mais). */
export function isComplete(parts: Parts, deltaCount: number): boolean {
  if (!Number.isInteger(deltaCount) || deltaCount < 0 || deltaCount > MAX_SEQ) return false
  if (parts.size !== deltaCount) return false
  for (const seq of parts.keys()) if (seq > deltaCount) return false
  return true
}

/** Seqs em falta, dado o `delta_count` do `turn.completed` (limitado a MAX_SEQ). */
export function missingSeqs(parts: Parts, deltaCount: number): number[] {
  const limit = Number.isInteger(deltaCount) ? Math.min(deltaCount, MAX_SEQ) : 0
  const missing: number[] = []
  for (let seq = 1; seq <= limit; seq += 1) if (!parts.has(seq)) missing.push(seq)
  return missing
}
