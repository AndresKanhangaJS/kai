import { reasonLabel } from './reasons'
import type { FailReason } from './transport'
import type { Status } from './useConversation'

// Badge de estado do núcleo (FR-007 no MVP, FR-068): sempre texto e ícone, nunca só cor.

function Icon({ status }: { status: Status }) {
  if (status === 'processing') {
    return (
      <svg className="badge-icon dots" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <circle cx="5" cy="12" r="2.5" />
        <circle cx="12" cy="12" r="2.5" />
        <circle cx="19" cy="12" r="2.5" />
      </svg>
    )
  }
  if (status === 'error') {
    return (
      <svg className="badge-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M12 3 2 21h20L12 3Z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
        <path d="M12 10v5M12 18v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    )
  }
  return (
    <svg className="badge-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

export function StatusBadge({ status, reason }: { status: Status; reason: FailReason | null }) {
  const label =
    status === 'processing'
      ? 'A processar'
      : status === 'error'
        ? `Erro · ${reasonLabel(reason)}`
        : 'Em espera'
  return (
    <span className="status-badge" data-state={status} data-testid="status-badge">
      <Icon status={status} />
      {label}
    </span>
  )
}
