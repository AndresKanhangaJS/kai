import { useEffect, useRef, useState } from 'react'
import { reasonLabel } from './reasons'
import { addDelta, assemble, isComplete, MAX_SEQ } from './reconcile'
import type { ConversationTransport, FailReason, SafeError, TurnHandle } from './transport'

// Estado da conversa no browser (SPEC-005): só em memória, desaparece ao recarregar.
// Os eventos vêm de um transporte que, no E5.1, traz output real do LLM: nada aqui confia
// nos tipos em runtime (revisão de segurança do E5.0).

/** O mesmo tecto do `content` no turn.requested.v1. */
export const MAX_CHARS = 32_000
/** Tecto da resposta mostrada (o AI Engine recusa respostas acima de 100 000 caracteres). */
export const MAX_REPLY_CHARS = 100_000

export const BUSY_MESSAGE = 'Espera pelo fim da resposta em curso, ou cancela-a.'

export type Status = 'idle' | 'processing' | 'error'

export type Message = {
  id: number
  role: 'user' | 'assistant'
  text: string
  state: 'streaming' | 'done' | 'interrupted' | 'failed'
  /** Terminou sem todos os deltas que o `delta_count` anunciava (AC-005-03). */
  incomplete?: boolean
  reason?: FailReason
  error?: SafeError
  traceId?: string
}

export function validateDraft(text: string): string | null {
  if (!text.trim()) return 'Escreve uma mensagem antes de enviar.'
  if (text.length > MAX_CHARS) return `A mensagem tem ${text.length} caracteres; o máximo é ${MAX_CHARS}.`
  return null
}

function safeError(error: unknown): SafeError {
  const e = (typeof error === 'object' && error !== null ? error : {}) as Record<string, unknown>
  return {
    code: typeof e.code === 'string' ? e.code.slice(0, 64) : 'unknown',
    message: typeof e.message === 'string' ? e.message.slice(0, 500) : '',
    retryable: e.retryable === true,
  }
}

export function useConversation(transport: ConversationTransport) {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<Status>('idle')
  const [failure, setFailure] = useState<FailReason | null>(null)
  // Região aria-live: só o fim do turno, nunca cada token (AC-005-08).
  const [announcement, setAnnouncement] = useState('')
  // O turno em curso (um token por turno): eventos de outro turno nunca o afectam.
  const current = useRef<{ turn: symbol; handle: TurnHandle | null } | null>(null)
  const nextId = useRef(1)
  const disposed = useRef(false)

  useEffect(() => {
    disposed.current = false
    return () => {
      disposed.current = true
      current.current?.handle?.cancel()
    }
  }, [])

  /** Devolve o erro a mostrar, ou null se o turno começou. */
  function send(text: string): string | null {
    const invalid = validateDraft(text)
    if (invalid) return invalid
    if (current.current) return BUSY_MESSAGE

    const userId = nextId.current++
    const replyId = nextId.current++
    const turn = Symbol('turn')
    current.current = { turn, handle: null }
    setMessages((all) => [
      ...all,
      { id: userId, role: 'user', text, state: 'done' },
      { id: replyId, role: 'assistant', text: '', state: 'streaming' },
    ])
    setStatus('processing')
    setFailure(null)
    setAnnouncement('')

    let parts = new Map<number, string>()
    let length = 0
    let ended = false
    const update = (patch: Partial<Message>) =>
      setMessages((all) => all.map((m) => (m.id === replyId ? { ...m, ...patch } : m)))

    const handle = transport.start(text, (event) => {
      // Depois do primeiro evento terminal, tudo o que chegar (atrasado ou repetido) é ignorado.
      if (disposed.current || ended || current.current?.turn !== turn) return
      if (event.kind === 'delta') {
        if (parts.size >= MAX_SEQ || typeof event.text !== 'string') return
        if (length + event.text.length > MAX_REPLY_CHARS) return
        const before = parts.size
        parts = addDelta(parts, event.seq, event.text)
        if (parts.size === before) return
        length += event.text.length
        update({ text: assemble(parts) })
        return
      }
      ended = true
      current.current = null
      if (event.kind === 'completed') {
        const incomplete = !isComplete(parts, event.delta_count)
        update({ text: assemble(parts), state: 'done', incomplete })
        setStatus('idle')
        setAnnouncement(incomplete ? 'Resposta completa, mas com partes em falta.' : 'Resposta completa.')
        return
      }
      const error = safeError(event.error)
      const label = reasonLabel(event.reason)
      update({
        text: assemble(parts),
        state: parts.size > 0 ? 'interrupted' : 'failed',
        reason: event.reason,
        error,
        traceId: typeof event.trace_id === 'string' ? event.trace_id.slice(0, 64) : undefined,
      })
      setStatus('error')
      setFailure(event.reason)
      setAnnouncement(`Erro: ${label}. ${error.message}`)
    })
    // Um transporte que termina já dentro do `start` (síncrono) não deixa um handle órfão.
    if (current.current?.turn === turn) current.current.handle = handle
    return null
  }

  function cancel() {
    current.current?.handle?.cancel()
  }

  return { messages, status, failure, announcement, send, cancel }
}
