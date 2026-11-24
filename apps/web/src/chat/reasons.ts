import type { FailReason } from './transport'

// Motivos do turn.failed.v1 em PT-PT, para o estado Error (AC-09).
export const REASON_LABELS: Record<FailReason, string> = {
  provider_unavailable: 'Fornecedor indisponível',
  provider_error: 'Erro do fornecedor',
  timeout: 'Tempo esgotado',
  budget_exceeded: 'Orçamento do turno excedido',
  cancelled: 'Cancelado',
  invalid_request: 'Pedido inválido',
  internal_error: 'Erro interno',
}

/** Etiqueta segura mesmo com um motivo desconhecido ou hostil (`__proto__`): só chaves próprias. */
export function reasonLabel(reason: unknown): string {
  return typeof reason === 'string' && Object.hasOwn(REASON_LABELS, reason)
    ? REASON_LABELS[reason as FailReason]
    : 'Motivo desconhecido'
}
