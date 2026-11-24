import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import axe from 'axe-core'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ChatPage } from './ChatPage'
import { SimulatedTransport, type Scenario } from './simulated'
import type { ConversationTransport, TurnEvent } from './transport'

// SPEC-005: o ecrã de conversa com respostas simuladas.

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

function setup(transport: ConversationTransport = new SimulatedTransport({ scenario: 'normal' })) {
  render(<ChatPage transport={transport} />)
  return transport
}

function type(text: string) {
  fireEvent.change(screen.getByLabelText('Mensagem'), { target: { value: text } })
}

function send(text: string) {
  type(text)
  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
}

function advance(ms = 60_000) {
  act(() => {
    vi.advanceTimersByTime(ms)
  })
}

function badge() {
  return screen.getByTestId('status-badge')
}

function log() {
  return screen.getByRole('list', { name: 'Mensagens' })
}

/** Transporte de teste: entrega os eventos dados, um por tick. */
class Scripted implements ConversationTransport {
  private readonly events: TurnEvent[]

  constructor(events: TurnEvent[]) {
    this.events = events
  }

  start(_text: string, onEvent: (event: TurnEvent) => void) {
    const timers = this.events.map((event, i) => setTimeout(() => onEvent(event), (i + 1) * 10))
    return { cancel: () => timers.forEach(clearTimeout) }
  }
}

describe('ChatPage', () => {
  it('AC-005-01: mostra o aviso de respostas simuladas e o estado em espera, com texto', () => {
    setup()
    expect(screen.getByRole('note').textContent).toContain('Respostas simuladas')
    expect(badge().dataset.state).toBe('idle')
    expect(badge().textContent).toBe('Em espera')
    expect(badge().querySelector('svg')).not.toBeNull()
  })

  it('AC-005-01 / P-024: o selector de cenário está dentro do aviso', () => {
    setup()
    const note = screen.getByRole('note')
    expect(within(note).getByLabelText('Cenário simulado')).toBeTruthy()
  })

  it('AC-005-02: envia, mostra a mensagem logo, processa e mostra a resposta incremental', () => {
    setup()
    send('Olá KAI')
    expect(within(log()).getByText('Olá KAI')).toBeTruthy()
    expect(badge().dataset.state).toBe('processing')
    expect((screen.getByLabelText('Mensagem') as HTMLTextAreaElement).value).toBe('')

    advance(400)
    const reply = screen.getByTestId('assistant-message')
    // Só o texto da resposta (sem o rótulo "KAI" nem o "A preparar…"): tem de crescer aos poucos.
    const partial = reply.querySelector('.msg-text')?.textContent ?? ''
    expect(partial.length).toBeGreaterThan(0)
    expect(reply.dataset.state).toBe('streaming')

    advance()
    expect(reply.dataset.state).toBe('done')
    const final = reply.querySelector('.msg-text')?.textContent ?? ''
    expect(final.length).toBeGreaterThan(partial.length)
    expect(final.startsWith(partial)).toBe(true)
    expect(badge().dataset.state).toBe('idle')
  })

  it('AC-005-02: Enter envia e Shift+Enter não', () => {
    setup()
    const box = screen.getByLabelText('Mensagem')
    type('linha 1')
    fireEvent.keyDown(box, { key: 'Enter', shiftKey: true })
    expect(within(log()).queryByText('linha 1')).toBeNull()
    fireEvent.keyDown(box, { key: 'Enter' })
    expect(within(log()).getByText('linha 1')).toBeTruthy()
  })

  it('AC-005-03: deltas trocados e repetidos dão o texto completo, sem duplicados', () => {
    setup(
      new Scripted([
        { kind: 'delta', seq: 2, text: ' mundo' },
        { kind: 'delta', seq: 1, text: 'Olá' },
        { kind: 'delta', seq: 1, text: 'Olá' },
        { kind: 'delta', seq: 3, text: '!' },
        { kind: 'completed', delta_count: 3, finish: 'end_turn' },
      ]),
    )
    send('oi')
    advance()
    expect(screen.getByTestId('assistant-message').querySelector('.msg-text')?.textContent).toBe('Olá mundo!')
  })

  it('AC-005-03 (negativo): uma resposta com buracos fica marcada como incompleta', () => {
    setup(
      new Scripted([
        { kind: 'delta', seq: 1, text: 'Olá' },
        { kind: 'delta', seq: 3, text: '!' },
        { kind: 'completed', delta_count: 3, finish: 'end_turn' },
      ]),
    )
    send('oi')
    advance()
    expect(screen.getByTestId('assistant-message').textContent).toContain('resposta incompleta')
    expect(screen.getByTestId('announcer').textContent).toContain('partes em falta')
  })

  it('negativo: um delta_count absurdo não congela o browser e marca a resposta incompleta', () => {
    setup(
      new Scripted([
        { kind: 'delta', seq: 1, text: 'Olá' },
        { kind: 'delta', seq: 1e12, text: 'X' },
        { kind: 'completed', delta_count: 1e12, finish: 'end_turn' },
      ]),
    )
    send('oi')
    advance()
    const reply = screen.getByTestId('assistant-message')
    expect(reply.querySelector('.msg-text')?.textContent).toBe('Olá')
    expect(reply.textContent).toContain('resposta incompleta')
  })

  it('negativo: eventos depois do fim do turno são ignorados (atrasados ou repetidos)', () => {
    setup(
      new Scripted([
        { kind: 'delta', seq: 1, text: 'Olá' },
        { kind: 'completed', delta_count: 1, finish: 'end_turn' },
        { kind: 'delta', seq: 2, text: ' a mais' },
        { kind: 'failed', reason: 'timeout', error: { code: 'x', message: 'tarde', retryable: true }, trace_id: 'a'.repeat(32) },
      ]),
    )
    send('oi')
    advance()
    const reply = screen.getByTestId('assistant-message')
    expect(reply.dataset.state).toBe('done')
    expect(reply.querySelector('.msg-text')?.textContent).toBe('Olá')
    expect(badge().dataset.state).toBe('idle')
  })

  it('negativo: um failed atrasado do turno anterior não afecta o turno seguinte', () => {
    let late: ((event: TurnEvent) => void) | null = null
    const turns: Array<(event: TurnEvent) => void> = []
    const transport: ConversationTransport = {
      start: (_text, onEvent) => {
        turns.push(onEvent)
        return { cancel: () => {} }
      },
    }
    setup(transport)
    send('A')
    act(() => turns[0]({ kind: 'completed', delta_count: 0, finish: 'end_turn' }))
    late = turns[0]
    send('B')
    act(() => late?.({ kind: 'failed', reason: 'timeout', error: { code: 'x', message: 'tarde', retryable: true }, trace_id: 'a'.repeat(32) }))
    expect(badge().dataset.state).toBe('processing')
    const [first, second] = screen.getAllByTestId('assistant-message')
    expect(first.dataset.state).toBe('done')
    expect(second.dataset.state).toBe('streaming')
    act(() => turns[1]({ kind: 'delta', seq: 1, text: 'B ok' }))
    expect(second.querySelector('.msg-text')?.textContent).toBe('B ok')
  })

  it('negativo: um transporte que termina dentro do start não bloqueia o envio seguinte', () => {
    const transport: ConversationTransport = {
      start: (_text, onEvent) => {
        onEvent({ kind: 'failed', reason: 'provider_unavailable', error: { code: 'offline', message: 'sem ligação', retryable: true }, trace_id: 'b'.repeat(32) })
        return { cancel: () => {} }
      },
    }
    const start = vi.spyOn(transport, 'start')
    setup(transport)
    send('primeira')
    send('segunda')
    expect(start).toHaveBeenCalledTimes(2)
    expect(within(log()).getByText('segunda')).toBeTruthy()
  })

  it.each(['__proto__', 'toString', 'motivo_novo_v2'])(
    'negativo: um motivo desconhecido ou hostil (%s) não derruba o ecrã',
    (reason) => {
      setup(
        new Scripted([
          { kind: 'failed', reason, error: { code: 'x', message: 'm', retryable: false }, trace_id: 'c'.repeat(32) } as unknown as TurnEvent,
        ]),
      )
      send('oi')
      advance()
      expect(badge().textContent).toBe('Erro · Motivo desconhecido')
      expect(screen.getByTestId('turn-error').textContent).toContain('Motivo desconhecido')
    },
  )

  it('negativo: um erro sem campos ou com tipos errados é mostrado com segurança', () => {
    setup(
      new Scripted([
        { kind: 'failed', reason: 'timeout', error: { message: { html: '<b>x</b>' } }, trace_id: 42 } as unknown as TurnEvent,
      ]),
    )
    send('oi')
    advance()
    expect(badge().textContent).toBe('Erro · Tempo esgotado')
    expect(screen.getByTestId('turn-error').querySelector('code')).toBeNull()
  })

  it('não se pode enviar outra mensagem enquanto há uma resposta em curso', () => {
    setup()
    send('primeira')
    expect((screen.getByRole('button', { name: 'Enviar' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('AC-005-04: Cancelar pára a resposta, marca-a interrompida e mostra Erro com o motivo', () => {
    setup()
    send('conta uma história')
    advance(400)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    const reply = screen.getByTestId('assistant-message')
    expect(reply.dataset.state).toBe('interrupted')
    expect(reply.textContent).toContain('interrompida')
    expect(badge().dataset.state).toBe('error')
    expect(badge().textContent).toContain('Cancelado')
    const frozen = reply.textContent
    advance()
    expect(reply.textContent).toBe(frozen)
    expect(screen.queryByRole('button', { name: 'Cancelar' })).toBeNull()
  })

  it.each([
    ['timeout', 'Tempo esgotado'],
    ['budget_exceeded', 'Orçamento do turno excedido'],
    ['provider_unavailable', 'Fornecedor indisponível'],
  ] as const)('AC-005-05: o cenário %s mostra o motivo, a mensagem e o trace_id', (scenario: Scenario, label) => {
    setup(new SimulatedTransport({ scenario }))
    send('olá')
    advance()
    expect(badge().dataset.state).toBe('error')
    expect(badge().textContent).toContain(label)
    const failure = screen.getByTestId('turn-error')
    expect(failure.textContent).toContain(label)
    expect(failure.querySelector('code')?.textContent).toMatch(/^[0-9a-f]{32}$/)
    // Depois de um erro, pode-se enviar outra mensagem.
    expect((screen.getByRole('button', { name: 'Enviar' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('AC-005-05: o selector muda o cenário do turno seguinte', () => {
    setup()
    fireEvent.change(screen.getByLabelText('Cenário simulado'), { target: { value: 'budget_exceeded' } })
    send('olá')
    advance()
    expect(badge().textContent).toContain('Orçamento do turno excedido')
  })

  it('AC-005-06 (negativo): a resposta é sempre texto literal, nunca HTML, imagens ou links', () => {
    const hostile = '<img src=x onerror="alert(1)"><script>alert(2)</script> [link](https://evil.test) ![i](https://evil.test/a.png) **negrito** <a href="https://evil.test">a</a>'
    setup(
      new Scripted([
        { kind: 'delta', seq: 1, text: hostile },
        { kind: 'completed', delta_count: 1, finish: 'end_turn' },
      ]),
    )
    send(hostile)
    advance()
    for (const message of within(log()).getAllByRole('listitem')) {
      expect(message.querySelector('img, script, a, iframe, strong')).toBeNull()
    }
    expect(screen.getByTestId('assistant-message').querySelector('.msg-text')?.textContent).toBe(hostile)
  })

  it.each([
    ['', 'Escreve uma mensagem antes de enviar.'],
    ['   \n  ', 'Escreve uma mensagem antes de enviar.'],
    ['x'.repeat(32_001), 'A mensagem tem 32001 caracteres; o máximo é 32000.'],
  ])('AC-005-07 (negativo): recusa uma mensagem inválida sem a enviar', (text, error) => {
    const transport = setup()
    const start = vi.spyOn(transport, 'start')
    send(text)
    expect(start).not.toHaveBeenCalled()
    expect(screen.getByRole('alert').textContent).toBe(error)
    expect(within(log()).queryAllByRole('listitem')).toHaveLength(0)
    expect(screen.getByLabelText('Mensagem').getAttribute('aria-invalid')).toBe('true')
  })

  it('AC-005-07: 32 000 caracteres é aceite', () => {
    const transport = setup()
    const start = vi.spyOn(transport, 'start')
    send('x'.repeat(32_000))
    expect(start).toHaveBeenCalledOnce()
  })

  it('AC-005-08: anuncia o fim da resposta uma vez, não cada token, e devolve o foco', () => {
    setup()
    const live = screen.getByTestId('announcer')
    expect(live.getAttribute('aria-live')).toBe('polite')
    send('olá')
    advance(400)
    expect(live.textContent).toBe('')
    advance()
    expect(live.textContent).toBe('Resposta completa.')
    expect(document.activeElement).toBe(screen.getByLabelText('Mensagem'))
  })

  it('AC-005-08: o histórico com scroll é alcançável pelo teclado', () => {
    setup()
    const region = screen.getByRole('region', { name: 'Histórico da conversa' })
    expect(region.getAttribute('tabindex')).toBe('0')
  })

  it('AC-005-08: anuncia o erro com o motivo', () => {
    setup(new SimulatedTransport({ scenario: 'timeout' }))
    send('olá')
    advance()
    expect(screen.getByTestId('announcer').textContent).toContain('Tempo esgotado')
  })

  it('AC-005-08: sem violações axe em espera, a meio e depois de um erro', async () => {
    setup()
    send('olá')
    advance(400)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    vi.useRealTimers()
    // O jsdom não calcula cores: o contraste verifica-se no E2E, num browser real.
    const result = await axe.run(document.body, { rules: { 'color-contrast': { enabled: false } } })
    expect(result.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([])
  })
})
