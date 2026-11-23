import { useState } from 'react'
import { ApiError, loginWithPasskey, loginWithRecoveryCode, loginWithTotp } from './api'

type Props = {
  onLoggedIn: () => void
}

export function LoginPage({ onLoggedIn }: Props) {
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [useRecoveryCode, setUseRecoveryCode] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleTotpSubmit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (useRecoveryCode) {
        await loginWithRecoveryCode(email, code)
      } else {
        await loginWithTotp(email, code)
      }
      onLoggedIn()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Falha inesperada.')
    } finally {
      setBusy(false)
    }
  }

  async function handlePasskeyClick() {
    setBusy(true)
    setError(null)
    try {
      await loginWithPasskey()
      onLoggedIn()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Falha inesperada.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <h1>KAI</h1>
      <p className="auth-subtitle">Entra com a tua passkey, ou com um código TOTP.</p>

      <button type="button" className="btn-primary" onClick={handlePasskeyClick} disabled={busy}>
        Entrar com passkey
      </button>

      <div className="divider">ou</div>

      <form onSubmit={handleTotpSubmit} className="auth-form">
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />

        <label htmlFor="code">{useRecoveryCode ? 'Código de recuperação' : 'Código TOTP'}</label>
        <input
          id="code"
          type="text"
          inputMode={useRecoveryCode ? 'text' : 'numeric'}
          autoComplete="one-time-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          required
        />

        <button type="button" className="btn-link" onClick={() => setUseRecoveryCode((value) => !value)}>
          {useRecoveryCode ? 'Usar código TOTP' : 'Usar código de recuperação'}
        </button>

        <button type="submit" className="btn-secondary" disabled={busy}>
          Entrar
        </button>
      </form>

      {error && (
        <p role="alert" aria-live="assertive" className="auth-error">
          {error}
        </p>
      )}
    </main>
  )
}
