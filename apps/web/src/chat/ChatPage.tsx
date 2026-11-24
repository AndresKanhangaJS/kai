import { type FormEvent, type KeyboardEvent, useEffect, useLayoutEffect, useRef, useState } from 'react'
import './chat.css'
import { reasonLabel } from './reasons'
import { SCENARIOS, type Scenario, SimulatedTransport } from './simulated'
import { StatusBadge } from './StatusBadge'
import type { ConversationTransport } from './transport'
import { type Message, useConversation } from './useConversation'

// Protótipo do chat no Command Center (SPEC-005). As mensagens são sempre texto literal:
// nunca HTML nem markdown renderizado a partir da resposta (AC-005-06, security.md).

function AssistantMessage({ message }: { message: Message }) {
  return (
    <li className="msg msg-assistant" data-testid="assistant-message" data-state={message.state}>
      <span className="msg-author">KAI</span>
      {message.text && (
        <p className="msg-text">
          {message.text}
          {message.state === 'streaming' && <span className="caret" aria-hidden="true" />}
        </p>
      )}
      {message.state === 'streaming' && !message.text && (
        <p className="msg-thinking">A preparar a resposta…</p>
      )}
      {message.state === 'interrupted' && <span className="msg-note">(resposta interrompida)</span>}
      {message.incomplete && <span className="msg-note">(resposta incompleta: faltam partes)</span>}
      {message.reason && message.error && (
        <div className="msg-error" data-testid="turn-error">
          <span className="msg-error-label">{reasonLabel(message.reason)}</span>
          <span>{message.error.message}</span>
          {message.traceId && (
            <span className="msg-trace">
              trace_id <code>{message.traceId}</code>
            </span>
          )}
        </div>
      )}
    </li>
  )
}

export function ChatPage({ transport }: { transport?: ConversationTransport }) {
  const [fallback] = useState(() => new SimulatedTransport())
  const active = transport ?? fallback
  const simulated = active instanceof SimulatedTransport ? active : null
  const [scenario, setScenario] = useState<Scenario>(simulated?.scenario ?? 'normal')
  const { messages, status, failure, announcement, send, cancel } = useConversation(active)
  const [draft, setDraft] = useState('')
  const [draftError, setDraftError] = useState<string | null>(null)
  const composer = useRef<HTMLTextAreaElement>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const atBottom = useRef(true)
  const wasProcessing = useRef(false)
  const processing = status === 'processing'

  // No fim de cada turno, o foco volta ao compositor (AC-005-08).
  useEffect(() => {
    if (wasProcessing.current && !processing) composer.current?.focus()
    wasProcessing.current = processing
  }, [processing])

  // Scroll automático só se o owner já estava no fundo.
  useLayoutEffect(() => {
    const el = logRef.current
    if (el && atBottom.current) el.scrollTop = el.scrollHeight
  }, [messages])

  function submit() {
    const problem = send(draft)
    if (problem) {
      // Ocupado ou inválido: o rascunho fica para o owner não o perder.
      setDraftError(problem)
      return
    }
    setDraft('')
    setDraftError(null)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!processing) submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (!processing) submit()
    }
  }

  return (
    <main className="chat-page" aria-labelledby="chat-title">
      {/* O aviso existe só com o transporte simulado: nunca com o KAI real (revisão do E5.0). */}
      {simulated && (
        <div className="sim-banner" role="note">
          <p>
            <strong>Respostas simuladas.</strong> Protótipo: nada é enviado ao KAI nem guardado.
          </p>
          <label className="sim-scenario">
            Cenário simulado
            <select
              value={scenario}
              onChange={(event) => {
                const value = event.target.value as Scenario
                simulated.setScenario(value)
                setScenario(value)
              }}
            >
              {SCENARIOS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <header className="chat-header">
        <h1 id="chat-title">Conversa</h1>
        <StatusBadge status={status} reason={failure} />
      </header>

      <div
        className="chat-log"
        ref={logRef}
        // Área com scroll alcançável pelo teclado (axe scrollable-region-focusable, AC-005-08).
        role="region"
        aria-label="Histórico da conversa"
        tabIndex={0}
        onScroll={(event) => {
          const el = event.currentTarget
          atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
        }}
      >
        {messages.length === 0 && <p className="chat-empty">Escreve uma mensagem para começar.</p>}
        <ol aria-label="Mensagens">
          {messages.map((message) =>
            message.role === 'user' ? (
              <li key={message.id} className="msg msg-user">
                <span className="visually-hidden">Tu: </span>
                <p className="msg-text">{message.text}</p>
              </li>
            ) : (
              <AssistantMessage key={message.id} message={message} />
            ),
          )}
        </ol>
      </div>

      <form className="composer" onSubmit={handleSubmit} noValidate>
        <label htmlFor="composer-input" className="visually-hidden">
          Mensagem
        </label>
        <textarea
          id="composer-input"
          ref={composer}
          rows={2}
          value={draft}
          placeholder="Escreve ao KAI… (Enter envia, Shift+Enter muda de linha)"
          aria-invalid={draftError ? 'true' : undefined}
          aria-describedby={draftError ? 'composer-error' : undefined}
          onChange={(event) => {
            setDraft(event.target.value)
            if (draftError) setDraftError(null)
          }}
          onKeyDown={handleKeyDown}
        />
        <div className="composer-actions">
          {processing && (
            <button type="button" className="btn-secondary" onClick={cancel}>
              Cancelar
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={processing}>
            Enviar
          </button>
        </div>
        {draftError && (
          <p id="composer-error" role="alert" className="auth-error">
            {draftError}
          </p>
        )}
      </form>

      <div className="visually-hidden" aria-live="polite" role="status" data-testid="announcer">
        {announcement}
      </div>
    </main>
  )
}
