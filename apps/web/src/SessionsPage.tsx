import { useEffect, useState } from 'react'
import { type ApiSession, ApiError, listSessions, registerPasskey, revokeSession } from './api'

type Props = {
  onLoggedOut: () => void
}

export function SessionsPage({ onLoggedOut }: Props) {
  const [sessions, setSessions] = useState<ApiSession[]>([])
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function refresh() {
    try {
      setSessions(await listSessions())
    } catch {
      onLoggedOut()
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleRevoke(id: string) {
    setError(null)
    try {
      await revokeSession(id)
      await refresh()
    } catch {
      setError('Não foi possível revogar a sessão.')
    }
  }

  async function handleRegisterPasskey() {
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      await registerPasskey(`Passkey de ${new Date().toLocaleDateString('pt-PT')}`)
      setNotice('Passkey registada. Já podes entrar com ela.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Falha inesperada.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="sessions-page">
      <header className="sessions-header">
        <h1>As tuas sessões</h1>
      </header>

      <button type="button" className="btn-secondary" onClick={handleRegisterPasskey} disabled={busy}>
        Registar passkey
      </button>

      {notice && (
        <p role="status" aria-live="polite" className="auth-notice">
          {notice}
        </p>
      )}

      {error && (
        <p role="alert" aria-live="assertive" className="auth-error">
          {error}
        </p>
      )}

      <ul className="sessions-list">
        {sessions.map((session) => (
          <li key={session.id} className="session-item">
            <div>
              <strong>{session.current ? 'Esta sessão' : session.ip_address ?? 'IP desconhecido'}</strong>
              <div className="session-meta">{session.user_agent}</div>
              <div className="session-meta">
                Última autenticação: {session.last_authenticated_at ?? '—'}
              </div>
            </div>
            {!session.current && (
              <button type="button" className="btn-danger" onClick={() => handleRevoke(session.id)}>
                Revogar
              </button>
            )}
          </li>
        ))}
      </ul>
    </main>
  )
}
