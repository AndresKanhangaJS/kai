import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

// SPEC-005 AC-005-09: o protótipo não abre nenhum caminho sem autenticação.

const api = vi.hoisted(() => ({
  loginWithTotp: vi.fn(),
  listSessions: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  ...api,
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

async function login() {
  api.loginWithTotp.mockResolvedValue(undefined)
  api.listSessions.mockResolvedValue([])
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'owner@example.test' } })
  fireEvent.change(screen.getByLabelText(/Código/), { target: { value: '123456' } })
  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
  await screen.findByRole('navigation', { name: 'Principal' })
}

describe('App', () => {
  it('AC-005-09 (negativo): sem sessão mostra o login e nenhum chat', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeTruthy()
    expect(screen.queryByLabelText('Mensagem')).toBeNull()
    expect(screen.queryByText(/Respostas simuladas/)).toBeNull()
  })

  it('AC-005-01: depois do login, a página inicial é a conversa', async () => {
    render(<App />)
    await login()
    expect(screen.getByLabelText('Mensagem')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Conversa' }).getAttribute('aria-current')).toBe('page')
  })

  it('AC-005-01: as sessões continuam acessíveis pela navegação', async () => {
    render(<App />)
    await login()
    fireEvent.click(screen.getByRole('button', { name: 'Sessões' }))
    expect(await screen.findByRole('heading', { name: 'As tuas sessões' })).toBeTruthy()
    expect(screen.queryByLabelText('Mensagem')).toBeNull()
  })

  it('negativo: se terminar sessão falhar, avisa e não finge que saiu', async () => {
    api.logout.mockRejectedValue(new Error('419'))
    render(<App />)
    await login()
    fireEvent.click(screen.getByRole('button', { name: 'Terminar sessão' }))
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível terminar a sessão. Tenta outra vez.')
    expect(screen.getByRole('navigation', { name: 'Principal' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Entrar' })).toBeNull()
  })

  it('terminar sessão volta ao login', async () => {
    api.logout.mockResolvedValue(undefined)
    render(<App />)
    await login()
    fireEvent.click(screen.getByRole('button', { name: 'Terminar sessão' }))
    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeTruthy()
  })
})
