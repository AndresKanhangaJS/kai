import type { ConversationTransport, FailReason, SafeError, TurnEvent, TurnHandle } from './transport'

// Transporte simulado (SPEC-005): respostas fixas, entregues ao longo do tempo, sem rede.
// Troca e repete alguns deltas de propósito, para a UI provar a reconciliação por `seq`.
// Sai quando o transporte real (E5.1) entrar.

export type Scenario = 'normal' | 'timeout' | 'budget_exceeded' | 'provider_unavailable'

export const SCENARIOS: ReadonlyArray<{ value: Scenario; label: string }> = [
  { value: 'normal', label: 'Resposta normal' },
  { value: 'timeout', label: 'Tempo esgotado a meio' },
  { value: 'budget_exceeded', label: 'Orçamento excedido' },
  { value: 'provider_unavailable', label: 'Fornecedor indisponível' },
]

const RESPONSES = [
  'Olá! Sou o KAI, ainda em modo de protótipo. Esta resposta é simulada no teu browser: não passou pelo servidor nem por nenhum modelo. Serve para afinarmos o ecrã de conversa antes de ligar o motor real.',
  'Quando o motor real estiver ligado, vais ver os tokens a chegar exactamente assim, um bocado de cada vez. Se algo correr mal, o estado muda para Erro e mostra o motivo e o identificador do trace.',
  'Podes experimentar os cenários de falha no selector do aviso: tempo esgotado, orçamento excedido ou fornecedor indisponível. O botão Cancelar pára a resposta a meio.',
]

const FAILURES: Record<Exclude<Scenario, 'normal'>, { reason: FailReason; error: SafeError }> = {
  timeout: {
    reason: 'timeout',
    error: { code: 'turn_timeout', message: 'O turno excedeu o tempo limite.', retryable: true },
  },
  budget_exceeded: {
    reason: 'budget_exceeded',
    error: {
      code: 'budget_exceeded',
      message: 'O custo máximo estimado excede o orçamento do turno.',
      retryable: false,
    },
  },
  provider_unavailable: {
    reason: 'provider_unavailable',
    error: {
      code: 'provider_unavailable',
      message: 'O fornecedor do modelo não respondeu depois de várias tentativas.',
      retryable: true,
    },
  },
}

const CANCELLED: SafeError = { code: 'cancelled', message: 'Cancelado pelo owner.', retryable: false }

/** Palavras por delta, em ciclo: 1 a 3, como um stream real. */
const CHUNK_SIZES = [2, 1, 3, 2, 1]

export function chunk(text: string): string[] {
  const words = text.split(' ')
  const chunks: string[] = []
  let i = 0
  let n = 0
  while (i < words.length) {
    const size = CHUNK_SIZES[n % CHUNK_SIZES.length]
    const piece = words.slice(i, i + size).join(' ')
    chunks.push(i === 0 ? piece : ` ${piece}`)
    i += size
    n += 1
  }
  return chunks
}

/** Ordem de entrega dos seqs: troca o 4.º com o 5.º e repete o 2.º depois do 3.º. */
export function deliveryOrder(count: number): number[] {
  const order = Array.from({ length: count }, (_, i) => i + 1)
  if (count >= 5) [order[3], order[4]] = [order[4], order[3]]
  if (count >= 3) order.splice(3, 0, 2)
  return order
}

function traceId(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

export class SimulatedTransport implements ConversationTransport {
  scenario: Scenario
  private turn = 0
  private readonly delayMs: number

  constructor(options: { scenario?: Scenario; delayMs?: number } = {}) {
    this.scenario = options.scenario ?? 'normal'
    this.delayMs = options.delayMs ?? 60
  }

  /** Muda o cenário dos turnos seguintes (o selector do aviso, P-024). */
  setScenario(scenario: Scenario): void {
    this.scenario = scenario
  }

  start(_text: string, onEvent: (event: TurnEvent) => void): TurnHandle {
    const scenario = this.scenario
    const chunks = chunk(RESPONSES[this.turn % RESPONSES.length])
    this.turn += 1
    const trace = traceId()

    const steps: TurnEvent[] = []
    const failure = scenario === 'normal' ? null : FAILURES[scenario]
    if (failure === null) {
      for (const seq of deliveryOrder(chunks.length)) steps.push({ kind: 'delta', seq, text: chunks[seq - 1] })
      steps.push({ kind: 'completed', delta_count: chunks.length, finish: 'end_turn' })
    } else {
      // O timeout acontece a meio da resposta; os outros, antes do primeiro delta.
      const partial = scenario === 'timeout' ? Math.ceil(chunks.length / 2) : 0
      for (let seq = 1; seq <= partial; seq += 1) steps.push({ kind: 'delta', seq, text: chunks[seq - 1] })
      steps.push({ kind: 'failed', ...failure, trace_id: trace })
    }

    let finished = false
    let timer: ReturnType<typeof setTimeout> | undefined
    // A primeira resposta demora mais (o "pensar"); depois, um ritmo irregular de stream.
    const delayFor = (i: number) =>
      i === 0 ? this.delayMs * (failure && scenario !== 'timeout' ? 12 : 6) : this.delayMs * (i % 2 ? 0.75 : 1.25)

    const next = (i: number) => {
      timer = setTimeout(() => {
        const event = steps[i]
        if (event.kind !== 'delta') finished = true
        onEvent(event)
        if (!finished) next(i + 1)
      }, delayFor(i))
    }
    next(0)

    return {
      cancel: () => {
        if (finished) return
        finished = true
        clearTimeout(timer)
        onEvent({ kind: 'failed', reason: 'cancelled', error: CANCELLED, trace_id: trace })
      },
    }
  }
}
