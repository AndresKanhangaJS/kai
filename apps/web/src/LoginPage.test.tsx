import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api'
import { LoginPage } from './LoginPage'

// SPEC-002 AC-02b/c/g na UI: o formulário escolhe o método certo e mostra
// as falhas de forma acessível (role="alert"), sem entrar.

const api = vi.hoisted(() => ({
  loginWithTotp: vi.fn(),
  loginWithRecoveryCode: vi.fn(),
  loginWithPasskey: vi.fn(),
}))

vi.mock('./api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api')>()),
  ...api,
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function fillAndSubmit(code: string) {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'owner@example.test' } })
  fireEvent.change(screen.getByLabelText(/Código/), { target: { value: code } })
  fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('LoginPage', () => {
  it('AC-02b: entra com o código TOTP', async () => {
    api.loginWithTotp.mockResolvedValue(undefined)
    const onLoggedIn = vi.fn()
    render(<LoginPage onLoggedIn={onLoggedIn} />)

    fillAndSubmit('123456')

    await vi.waitFor(() => expect(onLoggedIn).toHaveBeenCalledOnce())
    expect(api.loginWithTotp).toHaveBeenCalledWith('owner@example.test', '123456')
    expect(api.loginWithRecoveryCode).not.toHaveBeenCalled()
  })

  it('AC-02g: alterna para o código de recuperação e usa o método certo', async () => {
    api.loginWithRecoveryCode.mockResolvedValue(undefined)
    const onLoggedIn = vi.fn()
    render(<LoginPage onLoggedIn={onLoggedIn} />)

    fireEvent.click(screen.getByRole('button', { name: 'Usar código de recuperação' }))
    expect(screen.getByLabelText('Código de recuperação')).toBeTruthy()
    fillAndSubmit('Xn6BL-TESTE')

    await vi.waitFor(() => expect(onLoggedIn).toHaveBeenCalledOnce())
    expect(api.loginWithRecoveryCode).toHaveBeenCalledWith('owner@example.test', 'Xn6BL-TESTE')
    expect(api.loginWithTotp).not.toHaveBeenCalled()
  })

  it('AC-02c: um código inválido mostra o erro num alerta e não entra', async () => {
    api.loginWithTotp.mockRejectedValue(new ApiError('Credenciais inválidas.', 422))
    const onLoggedIn = vi.fn()
    render(<LoginPage onLoggedIn={onLoggedIn} />)

    fillAndSubmit('000000')

    expect((await screen.findByRole('alert')).textContent).toBe('Credenciais inválidas.')
    expect(onLoggedIn).not.toHaveBeenCalled()
  })

  it('um erro inesperado nunca mostra detalhes técnicos', async () => {
    api.loginWithPasskey.mockRejectedValue(new TypeError('Failed to fetch: stack…'))
    render(<LoginPage onLoggedIn={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: 'Entrar com passkey' }))

    expect((await screen.findByRole('alert')).textContent).toBe('Falha inesperada.')
  })
})
