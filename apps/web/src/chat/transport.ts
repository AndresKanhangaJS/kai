// Eventos de um turno, na forma dos contratos v1 (SPEC-003/SPEC-004): deltas com `seq`,
// `turn.completed` com `delta_count` e `turn.failed` com motivo e erro seguro.
// O transporte simulado (SPEC-005) e o real (E5.1: API + Reverb) implementam a mesma interface.

export type FailReason =
  | 'provider_unavailable'
  | 'provider_error'
  | 'timeout'
  | 'budget_exceeded'
  | 'cancelled'
  | 'invalid_request'
  | 'internal_error'

/** Erro seguro (common.v1 `safe_error`): sem dados sensíveis nem stack trace. */
export type SafeError = {
  code: string
  message: string
  retryable: boolean
}

export type TurnEvent =
  | { kind: 'delta'; seq: number; text: string }
  | { kind: 'completed'; delta_count: number; finish: 'end_turn' | 'max_output_tokens' }
  | { kind: 'failed'; reason: FailReason; error: SafeError; trace_id: string }

export type TurnHandle = {
  /** Pára o turno. Idempotente; depois do fim não faz nada. */
  cancel(): void
}

export interface ConversationTransport {
  start(text: string, onEvent: (event: TurnEvent) => void): TurnHandle
}
